"""CLI: `python -m scripts.run_eval [--modes vector hybrid] [--cache]`

Runs the full eval suite against data/eval/qa_pairs.json and saves results
under eval_results/<timestamp>.json + .md.

Examples:
    # Full eval — all 3 modes
    python -m scripts.run_eval

    # Skip graph (faster, fewer LLM calls)
    python -m scripts.run_eval --modes vector hybrid

    # Allow cache hits (rough latency upper-bound)
    python -m scripts.run_eval --cache
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from neurograph.eval.runner import MODES, run_all


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the NeuroGraph eval suite (Phase 4).",
    )
    parser.add_argument(
        "--modes", nargs="+", choices=MODES, default=MODES,
        help="Subset of retrieval modes to evaluate. Default: all 3.",
    )
    parser.add_argument(
        "--qa-file", type=Path, default=Path("data/eval/qa_pairs.json"),
        help="Path to the gold QA JSON.",
    )
    parser.add_argument(
        "--cache", action="store_true",
        help="Allow semantic-cache hits during eval (default: off, for honest measurements).",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't persist results under eval_results/.",
    )

    args = parser.parse_args()

    if not args.qa_file.exists():
        logger.error(f"QA file not found: {args.qa_file}")
        sys.exit(1)

    run_all(
        qa_file=args.qa_file,
        modes=args.modes,
        save=not args.no_save,
        use_cache=args.cache,
    )


if __name__ == "__main__":
    main()
