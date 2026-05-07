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
