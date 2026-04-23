from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func

from ..agents.discovery import QueryDiscoveryAgent
from ..agents.llm_clients import build_llm_client
from ..agents.recommendation import ContentRecommendationAgent
from ..agents.scoring import VisibilityScoringAgent
from ..extensions import db
from ..models import BusinessProfile, ContentRecommendation, DiscoveredQuery, PipelineRun


class PipelineService:
    def __init__(self, *, location_code: int, language_code: str):
        llm = build_llm_client()
        self.discovery = QueryDiscoveryAgent(llm)
        self.scoring = VisibilityScoringAgent(llm, location_code=location_code, language_code=language_code)
        self.reco = ContentRecommendationAgent(llm)

    def run_for_profile(self, profile: BusinessProfile) -> dict:
        run = PipelineRun(profile_uuid=profile.uuid, status="started")
        db.session.add(run)
        db.session.commit()

        tokens_total = 0
        try:
            queries, t1 = self.discovery.run(
                name=profile.name,
                domain=profile.domain,
                industry=profile.industry,
                description=profile.description,
                competitors=profile.competitors or [],
            )
            tokens_total += t1 or 0
            run.queries_discovered = len(queries)
            db.session.commit()

            scored_rows: list[DiscoveredQuery] = []
            for q in queries:
                try:
                    s = self.scoring.score(query_text=q, target_domain=profile.domain)
                    tokens_total += s.get("tokens_used") or 0
                    row = DiscoveredQuery(
                        profile_uuid=profile.uuid,
                        run_uuid=run.uuid,
                        query_text=q,
                        estimated_search_volume=s["estimated_search_volume"],
                        competitive_difficulty=s["competitive_difficulty"],
                        opportunity_score=s["opportunity_score"],
                        domain_visible=s["domain_visible"],
                        visibility_position=s["visibility_position"],
                        visibility_status=s["visibility_status"],
                    )
                    scored_rows.append(row)
                except Exception:
                    # partial failure: skip only this query
                    continue

            for r in scored_rows:
                db.session.add(r)
            db.session.commit()

            run.queries_scored = len(scored_rows)
            db.session.commit()

            top = (
                DiscoveredQuery.query.filter_by(profile_uuid=profile.uuid, run_uuid=run.uuid)
                .order_by(DiscoveredQuery.opportunity_score.desc())
                .limit(3)
                .all()
            )
            top3 = [self._query_dict(q) for q in top]

            # Recommend from the top-scoring not-visible queries
            not_visible = (
                DiscoveredQuery.query.filter_by(profile_uuid=profile.uuid, run_uuid=run.uuid)
                .filter(DiscoveredQuery.domain_visible.is_(False))
                .order_by(DiscoveredQuery.opportunity_score.desc())
                .limit(5)
                .all()
            )
            reco_queries = [q.query_text for q in not_visible]
            recos, t3 = self.reco.run(domain=profile.domain, industry=profile.industry, queries=reco_queries)
            tokens_total += t3 or 0

            reco_rows: list[ContentRecommendation] = []
            for idx, item in enumerate(recos):
                target = not_visible[min(idx, len(not_visible) - 1)] if not_visible else None
                if not target:
                    break
                reco_rows.append(
                    ContentRecommendation(
                        profile_uuid=profile.uuid,
                        query_uuid=target.uuid,
                        content_type=item.content_type,
                        title=item.title,
                        rationale=item.rationale,
                        target_keywords=item.target_keywords,
                        priority=item.priority,
                    )
                )

            for rr in reco_rows:
                db.session.add(rr)
            db.session.commit()

            run.status = "completed"
            run.tokens_used = tokens_total or None
            run.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            return {
                "run_uuid": run.uuid,
                "status": run.status,
                "queries_discovered": run.queries_discovered,
                "queries_scored": run.queries_scored,
                "top_3_opportunity_queries": top3,
                "content_recommendations": [self._reco_dict(r) for r in reco_rows],
                "tokens_used": run.tokens_used,
            }
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.tokens_used = tokens_total or None
            run.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            return {
                "run_uuid": run.uuid,
                "status": "failed",
                "error": str(e),
                "tokens_used": run.tokens_used,
            }

    def recheck_query(self, q: DiscoveredQuery, profile: BusinessProfile) -> dict:
        s = self.scoring.score(query_text=q.query_text, target_domain=profile.domain)
        q.estimated_search_volume = s["estimated_search_volume"]
        q.competitive_difficulty = s["competitive_difficulty"]
        q.opportunity_score = s["opportunity_score"]
        q.domain_visible = s["domain_visible"]
        q.visibility_position = s["visibility_position"]
        q.visibility_status = s["visibility_status"]
        db.session.commit()
        return self._query_dict(q)

    def profile_summary(self, profile_uuid: str) -> dict:
        total = DiscoveredQuery.query.filter_by(profile_uuid=profile_uuid).count()
        avg = (
            db.session.query(func.avg(DiscoveredQuery.opportunity_score))
            .filter(DiscoveredQuery.profile_uuid == profile_uuid)
            .scalar()
        )
        return {"total_queries": total, "avg_opportunity_score": float(avg or 0.0)}

    def _query_dict(self, q: DiscoveredQuery) -> dict:
        return {
            "query_uuid": q.uuid,
            "query_text": q.query_text,
            "estimated_search_volume": q.estimated_search_volume,
            "competitive_difficulty": q.competitive_difficulty,
            "opportunity_score": float(q.opportunity_score),
            "domain_visible": bool(q.domain_visible),
            "visibility_position": q.visibility_position,
            "status": q.visibility_status,
            "discovered_at": q.discovered_at.isoformat(),
        }

    def _reco_dict(self, r: ContentRecommendation) -> dict:
        return {
            "recommendation_uuid": r.uuid,
            "target_query_uuid": r.query_uuid,
            "content_type": r.content_type,
            "title": r.title,
            "rationale": r.rationale,
            "target_keywords": r.target_keywords,
            "priority": r.priority,
            "created_at": r.created_at.isoformat(),
        }

