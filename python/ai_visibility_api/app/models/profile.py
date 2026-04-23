from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON

from ..extensions import db
from .base import utcnow, uuid4_str


class BusinessProfile(db.Model):
    __tablename__ = "business_profiles"

    uuid = db.Column(String(36), primary_key=True, default=uuid4_str)
    name = db.Column(String(200), nullable=False)
    domain = db.Column(String(255), nullable=False, index=True)
    industry = db.Column(String(200), nullable=False)
    description = db.Column(Text, nullable=False)
    competitors = db.Column(SQLITE_JSON, nullable=False, default=list)
    status = db.Column(String(50), nullable=False, default="created")

    created_at = db.Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

