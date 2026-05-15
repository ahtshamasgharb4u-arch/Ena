"""Pydantic models for the reminder_service package."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Locale(str, Enum):
    """Supported locales for reminder generation."""

    EN = "en"
    ES = "es"
    AR = "ar"


class Appointment(BaseModel):
    """A dental appointment to generate a reminder for.

    Boundary contract decisions:
    - `appointment_id` is a required string (not auto-generated) so callers
      can use their own ID scheme. We validate it is non-empty.
    - `patient_name` is required. We do not split into first/last because
      the reminder script uses the full name as provided.
    - `phone_number` is a string (not an int) to preserve leading zeros and
      formatting like dashes. We strip non-digit characters internally for
      SSML digit-readback.
    - `appointment_time` is timezone-aware datetime. Naive datetimes are
      rejected to avoid ambiguity across locales.
    - `reason` is optional. If absent, the reminder uses a generic message.
    - `locale` defaults to 'en'. The caller must explicitly set it for
      non-English reminders.
    """

    appointment_id: str = Field(..., min_length=1, description="Unique appointment identifier")
    patient_name: str = Field(..., min_length=1, description="Full name of the patient")
    phone_number: str = Field(..., min_length=1, description="Contact phone number")
    appointment_time: datetime = Field(..., description="Appointment datetime (timezone-aware)")
    reason: Optional[str] = Field(None, description="Reason for the visit (e.g., cleaning, checkup)")
    locale: Locale = Field(default=Locale.EN, description="Locale for the reminder script")
    practice_name: str = Field(default="Teraleads Dental", description="Name of the dental practice")
    practice_address: Optional[str] = Field(None, description="Practice address for the reminder")

    @field_validator("appointment_time")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("appointment_time must be timezone-aware; use a tz-aware datetime")
        return v

    @field_validator("phone_number")
    @classmethod
    def ensure_non_empty_phone(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("phone_number must not be empty")
        return stripped


class ReminderResult(BaseModel):
    """The result of generating a reminder."""

    appointment_id: str
    ssml: str
    idempotency_key: str
    locale: Locale


def _make_idempotency_key(appointment: Appointment) -> str:
    """Generate a deterministic idempotency key from appointment fields.

    The key is a UUID v5 (namespace + name) so the same input always
    produces the same key. This makes the generator idempotent.
    """
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
    raw = f"{appointment.appointment_id}|{appointment.appointment_time.isoformat()}|{appointment.locale.value}"
    return str(uuid.uuid5(namespace, raw))
