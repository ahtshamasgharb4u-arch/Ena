from __future__ import annotations

from .base import AgentError, LlmClient
from .schemas import DiscoveredQueriesOut
from ..utils.json_tools import parse_and_validate


class QueryDiscoveryAgent:
    SYSTEM = (
        "You are Query Discovery Agent. You generate realistic, commercially relevant questions "
        "people ask AI assistants when evaluating products/services in a competitive space. "
        "Return ONLY valid JSON that matches the schema."
    )

    USER_TMPL = """Business profile:
name: {name}
domain: {domain}
industry: {industry}
description: {description}
competitors: {competitors}

Task:
Generate 10–20 natural-language, commercially relevant questions users might ask an AI assistant.
Use the industry and competitors for realism.

Output JSON schema (strict):
{{
  "queries": ["string", "..."]
}}

Rules:
- Return ONLY JSON (no markdown).
- Each query must be unique.
- Prefer high intent (best/vs/compare/pricing/alternatives) and buying-stage questions.
"""

    def __init__(self, llm: LlmClient):
        self.llm = llm

    def run(self, *, name: str, domain: str, industry: str, description: str, competitors: list[str]):
        user = self.USER_TMPL.format(
            name=name,
            domain=domain,
            industry=industry,
            description=description,
            competitors=", ".join(competitors or []),
        )
        r = self.llm.complete(system=self.SYSTEM, user=user)
        try:
            parsed = parse_and_validate(DiscoveredQueriesOut, r.text)
            return parsed.queries, r.usage.total_tokens
        except Exception as e:
            raise AgentError(f"Discovery agent JSON validation failed: {e}") from e

