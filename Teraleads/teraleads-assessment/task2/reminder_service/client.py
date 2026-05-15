"""Async TTS client with bounded exponential backoff, jitter, and circuit breaker."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = auto()  # Normal operation
    OPEN = auto()  # Failing — reject requests immediately
    HALF_OPEN = auto()  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Simple circuit breaker to prevent cascading failures.

    Why a circuit breaker instead of a kill switch:
    - A kill switch requires manual intervention (someone to flip it).
    - A circuit breaker auto-recovers after a cooldown, which is better
      for transient failures (e.g., a 30-second TTS outage).
    - If we need a manual kill switch, we can add a feature flag on top.
    - The circuit breaker is local to this process. In production you'd
      pair it with a distributed flag (e.g., LaunchDarkly) for global kill.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    _failures: int = 0
    _state: CircuitState = CircuitState.CLOSED
    _last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN after %d failures", self._failures)

    def __call__(self) -> bool:
        """Return True if the request is allowed, False if circuit is open."""
        return self.state != CircuitState.OPEN


class TTSClientError(Exception):
    """Non-retryable client error (4xx)."""


class TTSServerError(Exception):
    """Retryable server error (5xx or timeout)."""


class TTSRateLimitedError(Exception):
    """Rate-limited (429). Carries retry_after info."""

    def __init__(self, retry_after: int, message: str = "Rate limited"):
        self.retry_after = retry_after
        super().__init__(f"{message} (retry after {retry_after}s)")


@dataclass
class TTSClient:
    """Async HTTP client for a TTS synthesis API.

    Features:
    - Bounded exponential backoff with jitter
    - Per-status-code retry behaviour
    - Circuit breaker
    - Timeout on every external call
    - Idempotency key support
    """

    base_url: str
    api_key: str
    voice: str = "default"
    timeout: float = 10.0
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    _client: Optional[httpx.AsyncClient] = field(default=None, repr=False)

    async def __aenter__(self) -> TTSClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    async def synthesize(self, ssml: str, idempotency_key: str) -> dict:
        """Send a TTS synthesis request with retry logic.

        Args:
            ssml: The SSML to synthesize.
            idempotency_key: Deterministic key for deduplication.

        Returns:
            The JSON response body (must contain ``audio_url``).

        Raises:
            TTSClientError: On 4xx responses (terminal).
            TTSServerError: On 5xx / timeout after exhausting retries.
            TTSRateLimitedError: On 429 (caller should back off).
        """
        if not self.circuit_breaker():
            raise TTSServerError("Circuit breaker is OPEN — request rejected")

        if self._client is None:
            raise RuntimeError("TTSClient not used as async context manager")

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(
                    "/v1/synthesize",
                    json={
                        "ssml": ssml,
                        "idempotency_key": idempotency_key,
                        "voice": self.voice,
                    },
                )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                self.circuit_breaker.record_failure()
                last_exception = TTSServerError(f"HTTP error: {e}")
                if attempt < self.max_retries:
                    await self._backoff(attempt)
                continue

            if response.status_code == 200 or response.status_code == 202:
                self.circuit_breaker.record_success()
                return response.json()

            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 5)
                self.circuit_breaker.record_failure()
                raise TTSRateLimitedError(retry_after=retry_after)

            if 400 <= response.status_code < 500:
                self.circuit_breaker.record_failure()
                raise TTSClientError(
                    f"Client error {response.status_code}: {response.text}"
                )

            if response.status_code >= 500:
                self.circuit_breaker.record_failure()
                last_exception = TTSServerError(
                    f"Server error {response.status_code}: {response.text}"
                )
                if attempt < self.max_retries:
                    await self._backoff(attempt)
                continue

        raise TTSServerError(
            f"All {self.max_retries + 1} retries exhausted"
        ) from last_exception

    async def _backoff(self, attempt: int) -> None:
        """Bounded exponential backoff with full jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jittered = random.uniform(0, delay)
        logger.debug("Backing off %.2fs (attempt %d)", jittered, attempt + 1)
        await asyncio.sleep(jittered)
