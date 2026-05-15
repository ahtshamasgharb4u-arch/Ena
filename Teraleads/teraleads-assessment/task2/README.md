# reminder_service

A Python library for generating and delivering dental appointment reminders via TTS (Text-to-Speech).

## Installation

```bash
# Requires Python 3.11+
pip install pydantic httpx
# For running tests:
pip install pytest hypothesis
```

## Running Tests

```bash
# From the project root:
pytest teraleads-assessment/task2/tests/ -v

# Run with coverage:
pytest teraleads-assessment/task2/tests/ -v --cov=reminder_service
```

## Contract Decisions (3–5 bullets)

- **Idempotency via UUID v5**: The same `Appointment` input always produces the same SSML and idempotency key. The key is derived from `appointment_id`, `appointment_time`, and `locale` using UUID v5 (deterministic, not random). This lets the downstream TTS service safely deduplicate requests.
- **Circuit breaker over kill switch**: A local circuit breaker auto-recovers after a cooldown period, which is appropriate for transient TTS outages. A kill switch would require manual intervention; we recommend pairing this with a distributed feature flag (e.g., LaunchDarkly) for global kill scenarios.
- **Per-status-code retry behaviour**: 4xx errors are terminal (no retry). 5xx and timeouts are retried with bounded exponential backoff + jitter. 429 (rate limit) raises immediately with a `retry_after` hint so the caller can decide how to handle it.
- **Timezone-aware datetimes required**: `Appointment.appointment_time` must be timezone-aware. Naive datetimes are rejected at validation to prevent ambiguity across locales and DST boundaries.
- **SSML digit readback**: Phone numbers are rendered as individual `<say-as interpret-as='digit'>` tags with pauses, preventing the TTS engine from reading "555" as "five hundred fifty-five".

## AI Assistance

This code was developed with the assistance of an AI coding tool (Claude/Code). All generated code has been reviewed and understood by the author.
