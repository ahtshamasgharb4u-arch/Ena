import os

from anthropic import Anthropic
from openai import OpenAI

from .base import LlmClient, LlmResponse, LlmUsage


class OpenAiClient(LlmClient):
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, *, system: str, user: str) -> LlmResponse:
        r = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        txt = (r.choices[0].message.content or "").strip()
        usage = LlmUsage(total_tokens=getattr(r.usage, "total_tokens", None))
        return LlmResponse(text=txt, usage=usage)


class AnthropicClient(LlmClient):
    def __init__(self, api_key: str, model: str):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def complete(self, *, system: str, user: str) -> LlmResponse:
        r = self.client.messages.create(
            model=self.model,
            system=system,
            max_tokens=1500,
            temperature=0.3,
            messages=[{"role": "user", "content": user}],
        )
        parts = []
        for c in r.content:
            if getattr(c, "type", None) == "text":
                parts.append(c.text)
        txt = ("\n".join(parts)).strip()
        usage = LlmUsage(total_tokens=getattr(r.usage, "input_tokens", None))
        return LlmResponse(text=txt, usage=usage)


def build_llm_client():
    provider = (os.environ.get("LLM_PROVIDER") or "openai").lower().strip()
    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY")
        return OpenAiClient(api_key=key, model=os.environ.get("OPENAI_MODEL", "gpt-4o"))
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY")
        return AnthropicClient(
            api_key=key,
            model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        )
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")

