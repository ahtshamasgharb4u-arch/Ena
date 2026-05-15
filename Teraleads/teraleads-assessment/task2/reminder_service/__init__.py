"""reminder_service — A library for generating and delivering appointment reminders via TTS."""

from reminder_service.models import Appointment, ReminderResult, Locale
from reminder_service.generator import generate_reminder
from reminder_service.client import TTSClient, TTSClientError, TTSServerError, TTSRateLimitedError

__all__ = [
    "Appointment",
    "ReminderResult",
    "Locale",
    "generate_reminder",
    "TTSClient",
    "TTSClientError",
    "TTSServerError",
    "TTSRateLimitedError",
]
