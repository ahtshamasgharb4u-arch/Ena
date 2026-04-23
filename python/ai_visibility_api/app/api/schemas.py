from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileCreateIn(BaseModel):
    name: str
    domain: str
    industry: str
    description: str
    competitors: list[str] = Field(default_factory=list)


class PaginationOut(BaseModel):
    page: int
    per_page: int
    total: int

