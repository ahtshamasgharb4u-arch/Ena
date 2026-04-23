from __future__ import annotations

from pydantic import BaseModel, Field


class DiscoveredQueriesOut(BaseModel):
    queries: list[str] = Field(min_length=10, max_length=25)


class ScoredQueryOut(BaseModel):
    domain_visible: bool
    visibility_position: int | None = None
    visibility_status: str  # visible|not_visible|unknown


class RecommendationItem(BaseModel):
    content_type: str
    title: str
    rationale: str
    target_keywords: list[str]
    priority: str  # high|medium|low


class RecommendationsOut(BaseModel):
    recommendations: list[RecommendationItem] = Field(min_length=1, max_length=10)

