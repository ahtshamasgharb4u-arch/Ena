from sqlalchemy import String, DateTime, Integer, Float, Boolean, Text

from ..extensions import db
from .base import utcnow, uuid4_str


class DiscoveredQuery(db.Model):
    __tablename__ = "discovered_queries"

    uuid = db.Column(String(36), primary_key=True, default=uuid4_str)
    profile_uuid = db.Column(String(36), db.ForeignKey("business_profiles.uuid"), nullable=False, index=True)
    run_uuid = db.Column(String(36), db.ForeignKey("pipeline_runs.uuid"), nullable=False, index=True)

    query_text = db.Column(Text, nullable=False)
    estimated_search_volume = db.Column(Integer, nullable=False, default=0)
    competitive_difficulty = db.Column(Integer, nullable=False, default=0)  # 0–100
    opportunity_score = db.Column(Float, nullable=False, default=0.0)  # 0–1

    domain_visible = db.Column(Boolean, nullable=False, default=False)
    visibility_position = db.Column(Integer, nullable=True)
    visibility_status = db.Column(String(20), nullable=False, default="unknown")  # visible|not_visible|unknown

    discovered_at = db.Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

