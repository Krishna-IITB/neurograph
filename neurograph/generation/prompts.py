"""Prompt templates for the system."""

ANSWER_PROMPT = """You are a precise QA assistant. Answer the user's question using ONLY the context below. If the context does not contain the answer, say so.

{context}

Question: {question}
Answer:"""

CLEANER_PROMPT = """The following text was extracted from a PDF and may contain OCR errors, broken words, or formatting artifacts. Return a cleaned version with the same meaning. Do not add information.

Text:
{text}

Cleaned:"""

TRIPLET_PROMPT = """Extract all entity-relationship-entity triplets from the text. Return a JSON array of objects with keys: head, relation, tail. Use UPPERCASE_SNAKE_CASE for relations.

Text:
{text}

JSON:"""

ENTITY_EXTRACT_PROMPT = """List the named entities (people, organizations, places, products) in the question below. Return ONLY a JSON array of strings, no commentary.

Question: {question}

JSON:"""


# ============================================================================
# Eval prompts (LLM-as-judge)
# All judges return a single integer 1..5 with no commentary.
# ============================================================================

FAITHFULNESS_JUDGE_PROMPT = """You are a strict evaluator. Given a CONTEXT and an ANSWER, judge how faithful the answer is to the context — i.e., does every claim in the answer follow from the context?

Score on a 1-5 scale:
5 = every claim is directly supported by the context
4 = mostly supported, minor unsupported details
3 = some claims supported, others not
2 = mostly unsupported claims
1 = answer contradicts the context or is fully hallucinated

Return ONLY the integer score (1-5), nothing else.

CONTEXT:
{context}

ANSWER:
{answer}

Score:"""

ANSWER_RELEVANCE_JUDGE_PROMPT = """You are a strict evaluator. Given a QUESTION and an ANSWER, judge how directly the answer addresses the question.

Score on a 1-5 scale:
5 = directly answers the question
4 = answers the question with minor digression
3 = partially answers
2 = mostly off-topic
1 = does not address the question at all

Return ONLY the integer score (1-5), nothing else.

QUESTION:
{question}

ANSWER:
{answer}

Score:"""

CORRECTNESS_JUDGE_PROMPT = """You are a strict evaluator. Given an EXPECTED answer and a GENERATED answer, judge how well the generated answer matches the expected answer in factual content.

Score on a 1-5 scale:
5 = factually equivalent (same facts, different wording is fine)
4 = mostly correct, minor missing details
3 = partially correct
2 = mostly wrong
1 = factually contradicts the expected answer

Return ONLY the integer score (1-5), nothing else.

EXPECTED:
{expected}

GENERATED:
{generated}

Score:"""
