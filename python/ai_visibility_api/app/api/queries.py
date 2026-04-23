from __future__ import annotations

from flask import Blueprint, request

from ..config import Settings
from ..extensions import db
from ..models import BusinessProfile, ContentRecommendation, DiscoveredQuery
from ..services.pipeline import PipelineService
from ..utils.errors import error_payload


bp = Blueprint("queries", __name__, url_prefix="/api/v1")


def _settings() -> Settings:
    return Settings.from_env()


@bp.get("/profiles/<profile_uuid>/queries")
def list_queries(profile_uuid: str):
    if not BusinessProfile.query.get(profile_uuid):
        return error_payload("NotFound", "Profile not found"), 404

    min_score = float(request.args.get("min_score", "0") or 0)
    status = request.args.get("status")
    page = max(1, int(request.args.get("page", "1") or 1))
    per_page = min(100, max(1, int(request.args.get("per_page", "20") or 20)))

    q = DiscoveredQuery.query.filter_by(profile_uuid=profile_uuid)
    q = q.filter(DiscoveredQuery.opportunity_score >= min_score)
    if status in {"visible", "not_visible", "unknown"}:
        q = q.filter(DiscoveredQuery.visibility_status == status)

    q = q.order_by(DiscoveredQuery.opportunity_score.desc())
    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "data": [
            {
                "query_uuid": r.uuid,
                "query_text": r.query_text,
                "estimated_search_volume": r.estimated_search_volume,
                "competitive_difficulty": r.competitive_difficulty,
                "opportunity_score": float(r.opportunity_score),
                "domain_visible": bool(r.domain_visible),
                "visibility_position": r.visibility_position,
                "status": r.visibility_status,
                "discovered_at": r.discovered_at.isoformat(),
            }
            for r in rows
        ],
        "pagination": {"page": page, "per_page": per_page, "total": total},
    }


@bp.get("/profiles/<profile_uuid>/recommendations")
def list_recommendations(profile_uuid: str):
    if not BusinessProfile.query.get(profile_uuid):
        return error_payload("NotFound", "Profile not found"), 404

    rows = (
        ContentRecommendation.query.filter_by(profile_uuid=profile_uuid)
        .order_by(ContentRecommendation.created_at.desc())
        .all()
    )
    return {
        "data": [
            {
                "recommendation_uuid": r.uuid,
                "target_query_uuid": r.query_uuid,
                "content_type": r.content_type,
                "title": r.title,
                "rationale": r.rationale,
                "target_keywords": r.target_keywords,
                "priority": r.priority,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@bp.post("/queries/<query_uuid>/recheck")
def recheck(query_uuid: str):
    q = DiscoveredQuery.query.get(query_uuid)
    if not q:
        return error_payload("NotFound", "Query not found"), 404
    p = BusinessProfile.query.get(q.profile_uuid)
    if not p:
        return error_payload("NotFound", "Profile not found"), 404

    s = _settings()
    svc = PipelineService(location_code=s.dataforseo_location_code, language_code=s.dataforseo_language_code)
    try:
        updated = svc.recheck_query(q, p)
        return updated
    except Exception as e:
        db.session.rollback()
        return error_payload("UnprocessableEntity", "Recheck failed", str(e)), 422

