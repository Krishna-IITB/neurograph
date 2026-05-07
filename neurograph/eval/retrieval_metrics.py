"""Retrieval-side metrics: Hit Rate and MRR.

Hit Rate = (# queries where correct chunk appears in top-k) / total queries
MRR     = mean(1 / rank_of_first_correct_chunk) over all queries
"""


def hit_rate(retrieved: list[list[str]], gold: list[str]) -> float:
    raise NotImplementedError("Eval: implement hit rate")


def mrr(retrieved: list[list[str]], gold: list[str]) -> float:
    raise NotImplementedError("Eval: implement MRR")
