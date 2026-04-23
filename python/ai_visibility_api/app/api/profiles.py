from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, request

from ..config import Settings
from ..extensions import db
from ..models import BusinessProfile
from ..services.pipeline import PipelineService
from ..utils.errors import error_payload
from .schemas import ProfileCreateIn


bp = Blueprint("profiles", __name__, url_prefix="/api/v1")


def _settings() -> Settings:
    return Settings.from_env()


@bp.post("/profiles")
def create_profile():
    try:
        body = ProfileCreateIn.model_validate(request.get_json(force=True))
    except Exception as e:
        return error_payload("BadRequest", "Invalid JSON body", str(e)), 400

    p = BusinessProfile(
        name=body.name,
        domain=body.domain,
        industry=body.industry,
        description=body.description,
        competitors=body.competitors,
        status="created",
    )
    db.session.add(p)
    db.session.commit()
    return (
        {
            "profile_uuid": p.uuid,
            "name": p.name,
            "domain": p.domain,
            "status": p.status,
            "created_at": p.created_at.isoformat(),
        },
        201,
    )


@bp.get("/profiles/<profile_uuid>")
def get_profile(profile_uuid: str):
    p = BusinessProfile.query.get(profile_uuid)
    if not p:
        return error_payload("NotFound", "Profile not found"), 404

    svc = PipelineService(
        location_code=_settings().dataforseo_location_code,
        language_code=_settings().dataforseo_language_code,
    )
    stats = svc.profile_summary(p.uuid)
    return {
        "profile_uuid": p.uuid,
        "name": p.name,
        "domain": p.domain,
        "industry": p.industry,
        "description": p.description,
        "competitors": p.competitors or [],
        "status": p.status,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
        "stats": stats,
    }


@bp.post("/profiles/<profile_uuid>/run")
def run_pipeline(profile_uuid: str):
    p = BusinessProfile.query.get(profile_uuid)
    if not p:
        return error_payload("NotFound", "Profile not found"), 404

    s = _settings()
    svc = PipelineService(location_code=s.dataforseo_location_code, language_code=s.dataforseo_language_code)
    res = svc.run_for_profile(p)
    if res.get("status") == "failed":
        # DataForSEO missing or LLM provider misconfigured: return 422 for configuration errors
        return (
            {
                "run_uuid": res.get("run_uuid"),
                "status": "failed",
                "error": res.get("error"),
                "tokens_used": res.get("tokens_used"),
            },
            422,
        )
    return {
        "run_uuid": res["run_uuid"],
        "status": res["status"],
        "queries_discovered": res["queries_discovered"],
        "queries_scored": res["queries_scored"],
        "top_3_opportunity_queries": res["top_3_opportunity_queries"],
        "content_recommendations": res["content_recommendations"],
        "tokens_used": res.get("tokens_used"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

