"""Reminder SSML generation with locale dispatch."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from reminder_service.models import (
    Appointment,
    Locale,
    ReminderResult,
    _make_idempotency_key,
)


def _format_phone_ssml(phone: str) -> str:
    """Convert a phone number into digit-by-digit SSML readback.

    Strips all non-digit characters, then wraps each digit in
    <say-as interpret-as="digit"> to ensure the TTS reads them
    individually (e.g., "5 5 5 1 2 3 4 5 6 7") rather than as
    a single number ("five hundred fifty-five thousand...").
    """
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return "<break time='0.5s'/>number not provided"
    spaced = " ".join(f"<say-as interpret-as='digit'>{d}</say-as>" for d in digits)
    # Group with pauses for natural listening
    if len(digits) == 10:
        return (
            f"<break time='0.3s'/>"
            f"{' '.join(f'<say-as interpret-as=\"digit\">{d}</say-as>' for d in digits[:3])}"
            f"<break time='0.2s'/>"
            f"{' '.join(f'<say-as interpret-as=\"digit\">{d}</say-as>' for d in digits[3:6])}"
            f"<break time='0.2s'/>"
            f"{' '.join(f'<say-as interpret-as=\"digit\">{d}</say-as>' for d in digits[6:])}"
        )
    return f"<break time='0.3s'/>{spaced}"


def _format_datetime_ssml(dt: datetime) -> str:
    """Format a datetime into a natural-sounding SSML date string."""
    day = dt.strftime("%A")  # Monday, Tuesday, etc.
    date_str = dt.strftime("%B %d, %Y")  # January 15, 2025
    time_str = dt.strftime("%I:%M %p").lstrip("0")  # 9:30 AM
    return f"{day}, {date_str} at {time_str}"


def _build_en_ssml(appointment: Appointment) -> str:
    """Build a natural-sounding English SSML reminder script."""
    dt_str = _format_datetime_ssml(appointment.appointment_time)
    phone_ssml = _format_phone_ssml(appointment.phone_number)
    reason_text = f" for a {appointment.reason.lower()}" if appointment.reason else ""
    address_text = (
        f" at {appointment.practice_address}" if appointment.practice_address else ""
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<speak version='1.1' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
        "<prosody rate='medium' pitch='default'>"
        f"<break time='0.5s'/>"
        f"Hello {appointment.patient_name}. "
        f"<break time='0.3s'/>"
        f"This is a reminder from {appointment.practice_name} "
        f"about your appointment on {dt_str}{reason_text}.{address_text}"
        f"<break time='0.5s'/>"
        f"If you need to reach us, your phone number on file is "
        f"{phone_ssml}."
        f"<break time='0.5s'/>"
        f"Please call us if you need to reschedule or cancel."
        f"<break time='0.5s'/>"
        f"Thank you, and we look forward to seeing you."
        "</prosody>"
        "</speak>"
    )


def _build_es_ssml(appointment: Appointment) -> str:
    """Build a Spanish SSML reminder (stub — production-shaped dispatch)."""
    dt_str = _format_datetime_ssml(appointment.appointment_time)
    phone_ssml = _format_phone_ssml(appointment.phone_number)
    reason_text = f" para {appointment.reason.lower()}" if appointment.reason else ""

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<speak version='1.1' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='es-ES'>"
        "<prosody rate='medium' pitch='default'>"
        f"<break time='0.5s'/>"
        f"Hola {appointment.patient_name}. "
        f"<break time='0.3s'/>"
        f"Este es un recordatorio de {appointment.practice_name} "
        f"para su cita el {dt_str}{reason_text}."
        f"<break time='0.5s'/>"
        f"Su número de teléfono registrado es {phone_ssml}."
        f"<break time='0.5s'/>"
        f"Llámenos si necesita reprogramar o cancelar."
        f"<break time='0.5s'/>"
        f"Gracias, y esperamos verle pronto."
        "</prosody>"
        "</speak>"
    )


def _build_ar_ssml(appointment: Appointment) -> str:
    """Build an Arabic SSML reminder (stub — production-shaped dispatch)."""
    dt_str = _format_datetime_ssml(appointment.appointment_time)
    phone_ssml = _format_phone_ssml(appointment.phone_number)
    reason_text = f" لـ {appointment.reason}" if appointment.reason else ""

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<speak version='1.1' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='ar-SA'>"
        "<prosody rate='medium' pitch='default'>"
        f"<break time='0.5s'/>"
        f"مرحباً {appointment.patient_name}. "
        f"<break time='0.3s'/>"
        f"هذا تذكير من {appointment.practice_name} "
        f"بموعدك في {dt_str}{reason_text}."
        f"<break time='0.5s'/>"
        f"رقم هاتفك المسجل هو {phone_ssml}."
        f"<break time='0.5s'/>"
        f"يرجى الاتصال بنا إذا كنت بحاجة إلى إعادة الجدولة أو الإلغاء."
        f"<break time='0.5s'/>"
        f"شكراً، ونتطلع لرؤيتك."
        "</prosody>"
        "</speak>"
    )


_LOCALE_DISPATCH = {
    Locale.EN: _build_en_ssml,
    Locale.ES: _build_es_ssml,
    Locale.AR: _build_ar_ssml,
}


def generate_reminder(appointment: Appointment) -> ReminderResult:
    """Generate a reminder for the given appointment.

    The function is idempotent: calling it twice with the same
    ``Appointment`` produces identical SSML and the same
    ``idempotency_key``.

    Args:
        appointment: A validated Appointment model.

    Returns:
        A ReminderResult containing the SSML string, idempotency key,
        and locale.

    Raises:
        ValueError: If the appointment's locale is unsupported.
    """
    builder = _LOCALE_DISPATCH.get(appointment.locale)
    if builder is None:
        raise ValueError(f"Unsupported locale: {appointment.locale}")

    ssml = builder(appointment)
    idempotency_key = _make_idempotency_key(appointment)

    return ReminderResult(
        appointment_id=appointment.appointment_id,
        ssml=ssml,
        idempotency_key=idempotency_key,
        locale=appointment.locale,
    )
