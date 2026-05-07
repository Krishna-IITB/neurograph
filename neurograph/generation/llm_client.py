"""Unified LLM client.

Routes to Groq or Ollama based on settings.llm_provider so the rest of
the codebase doesn't care which backend is in use.

Both providers expose the same `complete(prompt, system, temperature)`
signature. Groq is the default (cloud, fast, free tier). Ollama is the
local fallback (no API key needed).
"""

from __future__ import annotations

from functools import lru_cache

from loguru import logger

from neurograph.config import settings


@lru_cache(maxsize=1)
def _groq_client():
    from groq import Groq

    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to .env or switch to LLM_PROVIDER=ollama."
        )
    return Groq(api_key=settings.groq_api_key)


@lru_cache(maxsize=1)
def _ollama_client():
    from ollama import Client

    return Client(host=settings.ollama_host)


def complete(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    """Single-turn completion. Returns the assistant text.

    Args:
        prompt: User message.
        system: Optional system prompt.
        temperature: 0.0 for deterministic eval runs.
        max_tokens: Generation cap.
    """
    provider = settings.llm_provider

    if provider == "groq":
        client = _groq_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    elif provider == "ollama":
        client = _ollama_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = client.chat(
            model=settings.ollama_model,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return resp["message"]["content"]

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


def is_available() -> bool:
    """Return True if the configured provider has the credentials it needs."""
    if settings.llm_provider == "groq":
        return bool(settings.groq_api_key)
    if settings.llm_provider == "ollama":
        # We assume ollama is reachable; first real call will surface errors
        return True
    return False
