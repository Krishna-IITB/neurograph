"""Generation-side metrics: Faithfulness and Answer Relevance.

Both are LLM-as-judge style.

Faithfulness:        does the answer follow from the retrieved context?
Answer Relevance:    does the answer actually address the question?
"""


def faithfulness(answer: str, context: str) -> float:
    raise NotImplementedError("Eval: implement faithfulness")


def answer_relevance(answer: str, question: str) -> float:
    raise NotImplementedError("Eval: implement answer relevance")
