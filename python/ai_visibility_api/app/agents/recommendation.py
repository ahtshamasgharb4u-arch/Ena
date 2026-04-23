from __future__ import annotations

from .base import AgentError, LlmClient
from .schemas import RecommendationsOut
from ..utils.json_tools import parse_and_validate


class ContentRecommendationAgent:
    SYSTEM = (
        "You are Content Recommendation Agent. You create specific, actionable content recommendations "
        "to help a business appear in AI answers for high-opportunity queries. Return ONLY valid JSON "
        "matching the schema."
    )

    USER_TMPL = """Target domain: {domain}
Industry: {industry}
High-opportunity queries where the domain is NOT visible:
{queries}

Generate 3–5 recommendations. Each recommendation must include:
- content_type: blog_post | landing_page | faq | comparison | guide
- title: suggested title
- rationale: why it closes the visibility gap
- target_keywords: list of strings
- priority: high | medium | low

Output JSON schema (strict):
{{
  "recommendations": [
    {{
      "content_type": "blog_post",
      "title": "string",
      "rationale": "string",
      "target_keywords": ["string"],
      "priority": "high"
    }}
  ]
}}

Rules:
- Return ONLY JSON.
- Make recommendations concrete (what to publish, angles, and sections).
"""

    def __init__(self, llm: LlmClient):
        self.llm = llm

    def run(self, *, domain: str, industry: str, queries: list[str]):
        q_lines = "\n".join([f"- {q}" for q in queries])
        user = self.USER_TMPL.format(domain=domain, industry=industry, queries=q_lines)
        r = self.llm.complete(system=self.SYSTEM, user=user)
        try:
            parsed = parse_and_validate(RecommendationsOut, r.text)
            return parsed.recommendations, r.usage.total_tokens
        except Exception as e:
            raise AgentError(f"Recommendation agent JSON validation failed: {e}") from e

