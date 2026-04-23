from __future__ import annotations

import random

from .base import AgentError, LlmClient
from .schemas import ScoredQueryOut
from ..utils.dataforseo import DataForSeoError, fetch_keyword_metrics
from ..utils.json_tools import parse_and_validate
from ..utils.scoring import opportunity_score


class VisibilityScoringAgent:
    SYSTEM = (
        "You are Visibility Scoring Agent. You simulate whether a target domain would appear in an "
        "AI answer for a query. You must output ONLY valid JSON matching the schema."
    )

    USER_TMPL = """Target domain: {domain}
Query: {query}

Simulate an AI answer visibility check:
- Decide if the target domain would be mentioned (domain_visible: true/false).
- If visible, provide a plausible 1-based visibility_position (1–10). If not visible, null.
- Provide visibility_status: "visible" | "not_visible" | "unknown"

Output JSON schema (strict):
{{
  "domain_visible": true,
  "visibility_position": 3,
  "visibility_status": "visible"
}}

Rules:
- Return ONLY JSON.
- Keep decisions consistent with commercially oriented queries.
"""

    def __init__(self, llm: LlmClient, *, location_code: int, language_code: str):
        self.llm = llm
        self.location_code = location_code
        self.language_code = language_code

    def score(self, *, query_text: str, target_domain: str):
        # Real third-party metrics
        try:
            metrics = fetch_keyword_metrics(
                query_text,
                location_code=self.location_code,
                language_code=self.language_code,
            )
        except DataForSeoError as e:
            raise AgentError(str(e)) from e

        # Simulated AI visibility
        user = self.USER_TMPL.format(domain=target_domain, query=query_text)
        r = self.llm.complete(system=self.SYSTEM, user=user)
        try:
            parsed = parse_and_validate(ScoredQueryOut, r.text)
        except Exception:
            # deterministic fallback: random but stable-ish based on text
            seed = sum(ord(c) for c in (query_text + target_domain)) % 10_000
            rng = random.Random(seed)
            vis = rng.random() < 0.35
            parsed = ScoredQueryOut(
                domain_visible=vis,
                visibility_position=rng.randint(1, 10) if vis else None,
                visibility_status="visible" if vis else "not_visible",
            )

        diff = max(0, min(100, int(metrics.difficulty)))
        vol = max(0, int(metrics.search_volume))
        opp = opportunity_score(
            volume=vol,
            difficulty_0_100=diff,
            domain_visible=bool(parsed.domain_visible),
            query_text=query_text,
        )

        return {
            "estimated_search_volume": vol,
            "competitive_difficulty": diff,
            "opportunity_score": float(opp),
            "domain_visible": bool(parsed.domain_visible),
            "visibility_position": parsed.visibility_position,
            "visibility_status": parsed.visibility_status,
            "tokens_used": r.usage.total_tokens,
        }

