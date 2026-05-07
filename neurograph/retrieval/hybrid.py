"""Hybrid retrieval — fuse vector chunks + graph paths into a single context.

Output format (fed to the generation prompt):

    Context from text:
    1. <chunk 1>
    2. <chunk 2>

    Context from graph:
    - <path 1>
    - <path 2>
"""


def retrieve(query: str) -> str:
    """Run both retrievers in parallel and format the combined context."""
    raise NotImplementedError("Phase 2: hybrid retrieval")
