import math
import re


COMMERCIAL_PATTERNS = [
    r"\b(best|top|vs|versus|compare|comparison|pricing|price|cost|alternative|alternatives|review)\b",
    r"\b(tool|software|platform|service)\b",
]


def commercial_intent_score(query_text: str) -> float:
    t = (query_text or "").lower()
    hits = 0
    for pat in COMMERCIAL_PATTERNS:
        if re.search(pat, t):
            hits += 1
    return min(1.0, hits / 2.0)


def volume_factor(volume: int) -> float:
    v = max(0, int(volume or 0))
    return min(1.0, math.log10(1 + v) / 4.0)


def opportunity_score(
    *,
    volume: int,
    difficulty_0_100: int,
    domain_visible: bool,
    query_text: str,
) -> float:
    vol_norm = volume_factor(volume)
    ease = 1.0 - (max(0, min(100, int(difficulty_0_100))) / 100.0)
    gap = 0.25 if domain_visible else 1.0
    intent = commercial_intent_score(query_text)
    s = 0.45 * vol_norm + 0.25 * ease + 0.2 * gap + 0.1 * intent
    return max(0.0, min(1.0, s))

