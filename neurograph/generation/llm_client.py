"""Unified LLM client. Routes to Groq or Ollama based on settings.llm_provider.

Both providers implement the same interface so the rest of the codebase
doesn't care which one is in use.
"""


def complete(prompt: str, *, system: str | None = None, temperature: float = 0.0) -> str:
    """Single-turn completion. Returns the assistant text."""
    raise NotImplementedError("Phase 2: implement LLM client")
