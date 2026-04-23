from sqlalchemy import String, DateTime, Integer, Text

from ..extensions import db
from .base import utcnow, uuid4_str


class PipelineRun(db.Model):
    __tablename__ = "pipeline_runs"

    uuid = db.Column(String(36), primary_key=True, default=uuid4_str)
    profile_uuid = db.Column(String(36), db.ForeignKey("business_profiles.uuid"), nullable=False, index=True)
    status = db.Column(String(50), nullable=False, default="started")  # completed | failed

    queries_discovered = db.Column(Integer, nullable=False, default=0)
    queries_scored = db.Column(Integer, nullable=False, default=0)
    tokens_used = db.Column(Integer, nullable=True)
    error_message = db.Column(Text, nullable=True)

    started_at = db.Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = db.Column(DateTime(timezone=True), nullable=True)

