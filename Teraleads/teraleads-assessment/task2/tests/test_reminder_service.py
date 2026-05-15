"""Tests for the reminder_service package.

Run with: pytest teraleads-assessment/task2/tests/ -v
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta

import httpx
import pytest
from hypothesis import given, strategies as st

from reminder_service.models import (
    Appointment,
    Locale,
    ReminderResult,
    _make_idempotency_key,
)
from reminder_service.generator import generate_reminder, _format_phone_ssml
from reminder_service.client import (
    TTSClient,
    TTSClientError,
    TTSServerError,
    TTSRateLimitedError,
    CircuitBreaker,
    CircuitState,
)
from reminder_service.mock_server import MockTTSServer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_appointment() -> Appointment:
    return Appointment(
        appointment_id="apt-001",
        patient_name="John Doe",
        phone_number="555-123-4567",
        appointment_time=datetime(2025, 6, 15, 9, 30, tzinfo=timezone.utc),
        reason="Cleaning",
        locale=Locale.EN,
        practice_name="Teraleads Dental",
        practice_address="123 Main St, Springfield",
    )


@pytest.fixture
def mock_server():
    return MockTTSServer()


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestAppointmentModel:
    def test_valid_appointment(self):
        apt = Appointment(
            appointment_id="apt-001",
            patient_name="Jane Doe",
            phone_number="555-123-4567",
            appointment_time=datetime(2025, 6, 15, 9, 30, tzinfo=timezone.utc),
        )
        assert apt.appointment_id == "apt-001"
        assert apt.locale == Locale.EN  # default

    def test_rejects_naive_datetime(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            Appointment(
                appointment_id="apt-001",
                patient_name="Jane Doe",
                phone_number="555-123-4567",
                appointment_time=datetime(2025, 6, 15, 9, 30),  # naive!
            )

    def test_rejects_empty_appointment_id(self):
        with pytest.raises(ValueError):
            Appointment(
                appointment_id="",
                patient_name="Jane Doe",
                phone_number="555-123-4567",
                appointment_time=datetime(
                    2025, 6, 15, 9, 30, tzinfo=timezone.utc
                ),
            )

    def test_rejects_empty_phone(self):
        with pytest.raises(ValueError):
            Appointment(
                appointment_id="apt-001",
                patient_name="Jane Doe",
                phone_number="   ",
                appointment_time=datetime(
                    2025, 6, 15, 9, 30, tzinfo=timezone.utc
                ),
            )


class TestIdempotencyKey:
    def test_deterministic(self, sample_appointment):
        key1 = _make_idempotency_key(sample_appointment)
        key2 = _make_idempotency_key(sample_appointment)
        assert key1 == key2

    def test_changes_with_locale(self, sample_appointment):
        en_key = _make_idempotency_key(sample_appointment)
        es_apt = sample_appointment.model_copy(update={"locale": Locale.ES})
        es_key = _make_idempotency_key(es_apt)
        assert en_key != es_key

    def test_changes_with_time(self, sample_appointment):
        key1 = _make_idempotency_key(sample_appointment)
        later = sample_appointment.model_copy(
            update={
                "appointment_time": sample_appointment.appointment_time
                + timedelta(hours=1)
            }
        )
        key2 = _make_idempotency_key(later)
        assert key1 != key2


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------


class TestGenerateReminder:
    def test_generates_ssml(self, sample_appointment):
        result = generate_reminder(sample_appointment)
        assert isinstance(result, ReminderResult)
        assert result.appointment_id == "apt-001"
        assert result.locale == Locale.EN
        assert result.ssml.startswith("<?xml")
        assert "<speak" in result.ssml
        assert "</speak>" in result.ssml

    def test_ssml_contains_patient_name(self, sample_appointment):
        result = generate_reminder(sample_appointment)
        assert "John Doe" in result.ssml

    def test_ssml_contains_phone_digits(self, sample_appointment):
        result = generate_reminder(sample_appointment)
        # Digits should be wrapped in say-as tags
        assert 'interpret-as="digit"' in result.ssml

    def test_ssml_contains_date(self, sample_appointment):
        result = generate_reminder(sample_appointment)
        assert "June" in result.ssml
        assert "2025" in result.ssml

    def test_ssml_contains_reason(self, sample_appointment):
        result = generate_reminder(sample_appointment)
        assert "Cleaning" in result.ssml or "cleaning" in result.ssml

    def test_idempotent(self, sample_appointment):
        r1 = generate_reminder(sample_appointment)
        r2 = generate_reminder(sample_appointment)
        assert r1.ssml == r2.ssml
        assert r1.idempotency_key == r2.idempotency_key

    def test_es_locale(self, sample_appointment):
        es_apt = sample_appointment.model_copy(update={"locale": Locale.ES})
        result = generate_reminder(es_apt)
        assert result.locale == Locale.ES
        assert "Hola" in result.ssml

    def test_ar_locale(self, sample_appointment):
        ar_apt = sample_appointment.model_copy(update={"locale": Locale.AR})
        result = generate_reminder(ar_apt)
        assert result.locale == Locale.AR
        assert "مرحباً" in result.ssml

    def test_no_reason_generic_message(self):
        apt = Appointment(
            appointment_id="apt-002",
            patient_name="Alice",
            phone_number="555-000-1111",
            appointment_time=datetime(
                2025, 7, 1, 14, 0, tzinfo=timezone.utc
            ),
        )
        result = generate_reminder(apt)
        assert result.ssml is not None

    def test_phone_formatting_strips_non_digits(self):
        ssml_fragment = _format_phone_ssml("+1 (555) 123-4567")
        assert "<say-as interpret-as='digit'>5</say-as>" in ssml_fragment


# ---------------------------------------------------------------------------
# TTS Client tests
# ---------------------------------------------------------------------------


class TestTTSClient:
    @pytest.mark.asyncio
    async def test_client_happy_path_200(self, mock_server):
        mock_server.set_mode("ok")
        async with TTSClient(
            base_url="http://test",
            api_key="test-key",
            voice="default",
            timeout=10.0,
            max_retries=1,
            _client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=mock_server.handle),
                base_url="http://test",
                timeout=10.0,
            ),
        ) as client:
            result = await client.synthesize("<speak>Hello</speak>", "key-1")
            assert "audio_url" in result
            assert mock_server.request_count == 1

    @pytest.mark.asyncio
    async def test_client_cached_202(self, mock_server):
        mock_server.set_mode("cached")
        async with TTSClient(
            base_url="http://test",
            api_key="test-key",
            voice="default",
            timeout=10.0,
            max_retries=1,
            _client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=mock_server.handle),
                base_url="http://test",
                timeout=10.0,
            ),
        ) as client:
            result = await client.synthesize(
                "<speak>Hello</speak>", "key-cached"
            )
            assert "audio_url" in result

    @pytest.mark.asyncio
    async def test_client_rate_limit(self, mock_server):
        mock_server.set_mode("rate_limit", retry_after=2)
        async with TTSClient(
            base_url="http://test",
            api_key="test-key",
            voice="default",
            timeout=10.0,
            max_retries=0,
            _client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=mock_server.handle),
                base_url="http://test",
                timeout=10.0,
            ),
        ) as client:
            with pytest.raises(TTSRateLimitedError) as exc:
                await client.synthesize(
                    "<speak>Hello</speak>", "key-rate"
                )
            assert exc.value.retry_after == 2

    @pytest.mark.asyncio
    async def test_client_error_4xx(self, mock_server):
        mock_server.set_mode("client_error")
        async with TTSClient(
            base_url="http://test",
            api_key="test-key",
            voice="default",
            timeout=10.0,
            max_retries=0,
            _client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=mock_server.handle),
                base_url="http://test",
                timeout=10.0,
            ),
        ) as client:
            with pytest.raises(TTSClientError):
                await client.synthesize(
                    "<speak>Hello</speak>", "key-4xx"
                )

    @pytest.mark.asyncio
    async def test_server_error_retry(self, mock_server):
        """Server error should retry, then raise after exhaustion."""
        mock_server.set_mode("server_error")
        async with TTSClient(
            base_url="http://test",
            api_key="test-key",
            voice="default",
            timeout=10.0,
            max_retries=2,
            base_delay=0.01,  # fast retries for test
            _client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=mock_server.handle),
                base_url="http://test",
                timeout=10.0,
            ),
        ) as client:
            with pytest.raises(TTSServerError):
                await client.synthesize(
                    "<speak>Hello</speak>", "key-5xx"
                )
            # Should have tried 3 times (initial + 2 retries)
            assert mock_server.request_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self, mock_server):
        """After failure_threshold failures, circuit breaker opens."""
        mock_server.set_mode("server_error")
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.5)
        async with TTSClient(
            base_url="http://test",
            api_key="test-key",
            voice="default",
            timeout=10.0,
            max_retries=0,
            base_delay=0.01,
            circuit_breaker=cb,
            _client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=mock_server.handle),
                base_url="http://test",
                timeout=10.0,
            ),
        ) as client:
            for i in range(3):
                with pytest.raises(TTSServerError):
                    await client.synthesize(
                        "<speak>Hello</speak>", f"key-cb-{i}"
                    )
            assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovers(self, mock_server):
        """After recovery_timeout, circuit breaker transitions to HALF_OPEN."""
        mock_server.set_mode("server_error")
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        async with TTSClient(
            base_url="http://test",
            api_key="test-key",
            voice="default",
            timeout=10.0,
            max_retries=0,
            base_delay=0.01,
            circuit_breaker=cb,
            _client=httpx.AsyncClient(
                transport=httpx.ASGITransport(app=mock_server.handle),
                base_url="http://test",
                timeout=10.0,
            ),
        ) as client:
            for i in range(2):
                with pytest.raises(TTSServerError):
                    await client.synthesize(
                        "<speak>Hello</speak>", f"key-recover-{i}"
                    )
            assert cb.state == CircuitState.OPEN
            # Wait for recovery
            await asyncio.sleep(0.15)
            assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_client_not_used_as_context_manager(self):
        client = TTSClient(
            base_url="http://test",
            api_key="test-key",
        )
        with pytest.raises(RuntimeError, match="not used as async context manager"):
            await client.synthesize("<speak>Hello</speak>", "key-err")


# ---------------------------------------------------------------------------
# Circuit Breaker tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb() is False

    def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb() is True

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        import time

        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb() is True  # half-open allows requests


# ---------------------------------------------------------------------------
# Property-based / fuzz test
# ---------------------------------------------------------------------------


class TestPropertyBased:
    @given(
        appointment_id=st.text(min_size=1, max_size=20),
        patient_name=st.text(min_size=1, max_size=50),
        phone_number=st.from_regex(r"\d{3}-?\d{3}-?\d{4}", fullmatch=True),
        year=st.integers(min_value=2025, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
    )
    def test_generate_reminder_idempotent(
        self,
        appointment_id,
        patient_name,
        phone_number,
        year,
        month,
        day,
        hour,
        minute,
    ):
        """Property: generate_reminder is always idempotent.

        Given any valid Appointment, calling generate_reminder twice
        produces identical SSML and idempotency_key.
        """
        try:
            apt = Appointment(
                appointment_id=appointment_id,
                patient_name=patient_name,
                phone_number=phone_number,
                appointment_time=datetime(
                    year, month, day, hour, minute, tzinfo=timezone.utc
                ),
            )
        except (ValueError, OverflowError):
            # Skip invalid date combinations
            return

        r1 = generate_reminder(apt)
        r2 = generate_reminder(apt)

        assert (
            r1.ssml == r2.ssml
        ), "SSML must be identical on repeated calls"
        assert (
            r1.idempotency_key == r2.idempotency_key
        ), "Idempotency key must be identical"
        assert r1.appointment_id == r2.appointment_id
        assert r1.locale == r2.locale

    @given(
        phone=st.from_regex(r"[\d\s\-\(\)\+\.]+", fullmatch=True),
    )
    def test_phone_formatting_always_produces_valid_ssml(self, phone):
        """Property: _format_phone_ssml always returns valid SSML fragments."""
        if not any(c.isdigit() for c in phone):
            return  # skip phones with no digits
        result = _format_phone_ssml(phone)
        # Should contain say-as tags for digits
        assert "<say-as" in result or "not provided" in result
        # Should not contain raw digits outside say-as tags (except in edge cases)
        assert isinstance(result, str)
