"""
LLM Provider abstraction for Module 1.

Active provider, explicit model string, and temperature come from env vars.
The browser never calls the LLM; the backend calls it here.
Never pin to "latest" — explicit model strings only.
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        """Return (text, input_tokens, output_tokens)."""
        ...


class AnthropicProvider:
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = msg.content[0].text if msg.content else ""
        return text, msg.usage.input_tokens, msg.usage.output_tokens


class OpenAIProvider:
    """OpenAI-compatible provider."""

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def model_id(self) -> str:
        return self._model

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        return text, usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0


class MockProvider:
    """
    Hardcoded mock provider for local development without an API key.
    Enabled when LLM_MOCK=true in the environment.
    Returns a realistic suggestion so the full UI flow can be tested.
    """

    _MODEL = "mock-echo"

    @property
    def model_id(self) -> str:
        return self._MODEL

    def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> tuple[str, int, int]:
        import json
        # Return one passive-voice suggestion derived from whatever text was sent
        lines = [l.strip() for l in user.splitlines() if l.strip()]
        suggestions = []
        for line in lines[:3]:
            if " was " in line or " were " in line:
                revised = line.replace(" was ", " is ").replace(" were ", " are ")
                if revised != line:
                    suggestions.append({
                        "original": line,
                        "revised": revised,
                        "reason": "passive voice (mock)",
                    })
                    break
        text = json.dumps(suggestions)
        return text, len(user.split()) * 2, len(text.split())


def get_provider(tier: str = "paid") -> LLMProvider:
    """
    Return the configured provider for the given tier.

    Env vars:
      LLM_PROVIDER     = "anthropic" | "openai"   (default: anthropic)
      LLM_MODEL_PAID   = explicit model string for paid tier
      LLM_MODEL_FREE   = explicit model string for free trial
      LLM_MOCK         = "true" to use a hardcoded mock (dev only — no API key needed)
      ANTHROPIC_API_KEY / OPENAI_API_KEY
    """
    if os.getenv("LLM_MOCK", "false").lower() in ("true", "1", "yes"):
        return MockProvider()

    provider_name = os.getenv("LLM_PROVIDER", "anthropic").lower()
    model = (
        os.getenv("LLM_MODEL_FREE", "claude-sonnet-4-6")
        if tier == "free"
        else os.getenv("LLM_MODEL_PAID", "claude-opus-4-8")
    )

    if provider_name == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Add it to backend/.env, or set LLM_MOCK=true to test without a key."
            )
        return AnthropicProvider(api_key=key, model=model)

    if provider_name == "openai":
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OPENAI_API_KEY not set.")
        return OpenAIProvider(api_key=key, model=model)

    raise ValueError(f"Unknown LLM_PROVIDER: {provider_name!r}. Use 'anthropic' or 'openai'.")
