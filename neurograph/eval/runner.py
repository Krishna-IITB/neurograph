"""Eval runner — orchestrates all metrics across all retrieval modes.

For each (question, expected_answer) pair we run retrieval + generation in
each mode (vector, graph, hybrid), compute four metrics, and aggregate.

Output:
  - Pretty console table
  - JSON dump under eval_results/<timestamp>.json
  - Markdown table under eval_results/<timestamp>.md
    (paste straight into the README's eval section)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from neurograph.eval.generation_metrics import (
    answer_relevance,
    correctness,
    faithfulness,
)
from neurograph.eval.retrieval_metrics import (
    average,
    keyword_recall_for_chunks,
    keyword_recall_for_paths,
)
from neurograph.generation.qa import answer as qa_answer
from neurograph.retrieval.hybrid import format_context

MODES: list[str] = ["vector", "graph", "hybrid"]
QA_FILE = Path("data/eval/qa_pairs.json")
RESULTS_DIR = Path("eval_results")


@dataclass
class PerQuestionResult:
    qid: str
    question: str
    mode: str
    answer: str
    recall: float
    faithfulness: float
    relevance: float
    correctness: float
    latency_ms: float


def _load_qa_pairs(path: Path = QA_FILE) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    pairs = [p for p in data["qa_pairs"] if p.get("expected_answer")]
    logger.info(f"Loaded {len(pairs)} QA pairs from {path}")
    return pairs


def _evaluate_one(
    qa: dict,
    mode: str,
    *,
    use_cache: bool = False,
) -> PerQuestionResult:
    """Run retrieval + generation + 4 metrics for a single (question, mode)."""
    question = qa["question"]
    expected = qa["expected_answer"]

    resp = qa_answer(question, mode=mode, use_cache=use_cache)

    # Recall: did retrieval pull the answer?
    if mode == "graph":
        recall = keyword_recall_for_paths(resp.retrieval.paths, expected)
    elif mode == "vector":
        recall = keyword_recall_for_chunks(resp.retrieval.chunks, expected)
    else:  # hybrid: either side counts
        recall = max(
            keyword_recall_for_chunks(resp.retrieval.chunks, expected),
            keyword_recall_for_paths(resp.retrieval.paths, expected),
        )

    context = format_context(resp.retrieval.chunks, resp.retrieval.paths)
    is_error = resp.answer.startswith("(generation error")
    f_score = 0.0 if is_error else faithfulness(resp.answer, context)
    r_score = 0.0 if is_error else answer_relevance(resp.answer, question)
    c_score = 0.0 if is_error else correctness(resp.answer, expected)

    return PerQuestionResult(
        qid=qa["id"],
        question=question,
        mode=mode,
        answer=resp.answer,
        recall=recall,
        faithfulness=f_score,
        relevance=r_score,
        correctness=c_score,
        latency_ms=resp.latency_ms,
    )


def _aggregate(rows: list[PerQuestionResult], mode: str) -> dict:
    mode_rows = [r for r in rows if r.mode == mode]
    return {
        "mode": mode,
        "n": len(mode_rows),
        "recall": average([r.recall for r in mode_rows]),
        "faithfulness": average([r.faithfulness for r in mode_rows]),
        "relevance": average([r.relevance for r in mode_rows]),
        "correctness": average([r.correctness for r in mode_rows]),
        "avg_latency_ms": average([r.latency_ms for r in mode_rows]),
    }


def _format_console_table(per_mode: list[dict]) -> str:
    """Pretty-print a comparison table to the terminal."""
    lines = []
    lines.append("=" * 92)
    lines.append(f"{'Mode':<10} | {'Recall@k':>10} | {'Faithful.':>10} | {'Relevance':>10} | {'Correct.':>10} | {'Latency (ms)':>14}")
    lines.append("-" * 92)
    for s in per_mode:
        lines.append(
            f"{s['mode']:<10} | {s['recall']:>10.3f} | {s['faithfulness']:>10.2f} | "
            f"{s['relevance']:>10.2f} | {s['correctness']:>10.2f} | {s['avg_latency_ms']:>14.0f}"
        )
    lines.append("=" * 92)
    lines.append("Recall: 0..1 (fraction of questions whose expected answer appeared in retrieved context).")
    lines.append("Faithfulness / Relevance / Correctness: 1..5 (LLM-as-judge, higher is better).")
    return "\n".join(lines)


def _format_markdown_table(per_mode: list[dict]) -> str:
    """Markdown table that pastes into the README."""
    # Find the best in each column for bolding
    best_recall = max(s["recall"] for s in per_mode)
    best_faith = max(s["faithfulness"] for s in per_mode)
    best_rel = max(s["relevance"] for s in per_mode)
    best_corr = max(s["correctness"] for s in per_mode)

    def fmt(val: float, best: float, decimals: int = 3) -> str:
        s = f"{val:.{decimals}f}"
        return f"**{s}**" if abs(val - best) < 1e-9 and val > 0 else s

    lines = [
        "| Mode | Recall@k ↑ | Faithfulness ↑ | Answer Relevance ↑ | Correctness ↑ | Avg Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for s in per_mode:
        lines.append(
            f"| {s['mode']} | {fmt(s['recall'], best_recall, 3)} | "
            f"{fmt(s['faithfulness'], best_faith, 2)} | "
            f"{fmt(s['relevance'], best_rel, 2)} | "
            f"{fmt(s['correctness'], best_corr, 2)} | "
            f"{s['avg_latency_ms']:.0f} |"
        )
    return "\n".join(lines)


def run_all(
    *,
    qa_file: Path = QA_FILE,
    modes: list[str] | None = None,
    save: bool = True,
    use_cache: bool = False,
) -> dict:
    """Run the full eval and return aggregated results.

    Args:
        qa_file: Path to the gold QA JSON.
        modes: Subset of ['vector', 'graph', 'hybrid']. Defaults to all 3.
        save: Persist JSON + markdown to eval_results/.
        use_cache: Whether to allow semantic-cache hits during eval. Default False
            (so we measure real generation behavior, not cached responses).
    """
    modes = modes or MODES
    qa_pairs = _load_qa_pairs(qa_file)

    all_rows: list[PerQuestionResult] = []
    total = len(qa_pairs) * len(modes)
    pbar = tqdm(total=total, desc="Evaluating", unit="run")
    for qa in qa_pairs:
        for mode in modes:
            try:
                row = _evaluate_one(qa, mode, use_cache=use_cache)
                all_rows.append(row)
            except Exception as e:
                logger.error(f"Eval failed for {qa['id']}/{mode}: {e}")
            finally:
                pbar.update(1)
            # Tiny breath to be nice to free-tier rate limits
            time.sleep(0.5)
    pbar.close()

    per_mode = [_aggregate(all_rows, m) for m in modes]
    console_table = _format_console_table(per_mode)
    md_table = _format_markdown_table(per_mode)

    print()
    print(console_table)
    print()
    print("Markdown table (paste into README):")
    print(md_table)
    print()

    if save:
        RESULTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path = RESULTS_DIR / f"eval_{ts}.json"
        md_path = RESULTS_DIR / f"eval_{ts}.md"
        with open(json_path, "w") as f:
            json.dump(
                {
                    "timestamp": ts,
                    "n_questions": len(qa_pairs),
                    "modes": modes,
                    "summary": per_mode,
                    "per_question": [asdict(r) for r in all_rows],
                },
                f,
                indent=2,
            )
        md_path.write_text(md_table + "\n")
        logger.info(f"Saved → {json_path}")
        logger.info(f"Saved → {md_path}")

    return {
        "summary": per_mode,
        "rows": [asdict(r) for r in all_rows],
        "n_questions": len(qa_pairs),
    }
