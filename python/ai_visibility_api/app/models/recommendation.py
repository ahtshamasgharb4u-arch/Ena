from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON

from ..extensions import db
from .base import utcnow, uuid4_str


class ContentRecommendation(db.Model):
    __tablename__ = "content_recommendations"

    uuid = db.Column(String(36), primary_key=True, default=uuid4_str)
    profile_uuid = db.Column(String(36), db.ForeignKey("business_profiles.uuid"), nullable=False, index=True)
    query_uuid = db.Column(String(36), db.ForeignKey("discovered_queries.uuid"), nullable=False, index=True)

    content_type = db.Column(String(50), nullable=False)
    title = db.Column(String(255), nullable=False)
    rationale = db.Column(Text, nullable=False)
    target_keywords = db.Column(SQLITE_JSON, nullable=False, default=list)
    priority = db.Column(String(20), nullable=False)  # high|medium|low

    created_at = db.Column(DateTime(timezone=True), nullable=False, default=utcnow)

