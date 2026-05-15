# DESIGN.md — reminder_service

## Observability

**What we log:**

- Every TTS request attempt (idempotency_key, attempt number, response status).
- Circuit breaker state transitions (CLOSED → OPEN → HALF_OPEN).
- Backoff delays (level DEBUG, to avoid noise at INFO).
- Terminal failures (exhausted retries, 4xx client errors).

**What we trace:**

- A `trace_id` propagated from the caller (via `Appointment.appointment_id`). This lets us correlate a reminder generation → TTS synthesis → audio delivery in one trace.

**What we alert on:**

- Circuit breaker OPEN for > 5 minutes → likely sustained TTS outage.
- Rate limit (429) frequency > 10/minute → we are sending too many requests;可能需要throttling upstream.
- Client error (4xx) rate > 1% → likely a bug in our request construction.

## Idempotency Strategy

We use **UUID v5** (namespace + deterministic name) to generate the idempotency key:

```
key = uuid5("6ba7b810-...", f"{appointment_id}|{appointment_time}|{locale}")
```

Why not UUID v4 (random)? Because we need idempotency: the same appointment must always produce the same key. UUID v4 would produce a different key on every call, defeating the purpose.

Why not a hash of the full SSML? Because the SSML depends on the appointment fields, and we want the key to be computable _before_ generating the SSML (e.g., for pre-flight dedup checks).

The downstream TTS service is expected to:

- Return 200 on first synthesis.
- Return 202 on subsequent requests with the same idempotency key (cache hit).

## Feature Flags

What we would put behind a feature flag:

1. **New locale rollout** — Enable `ar` or `fr` for a subset of practices before global rollout.
2. **Circuit breaker parameters** — `failure_threshold` and `recovery_timeout` should be configurable per-deployment without a code deploy.
3. **Voice selection** — Allow per-practice voice override (e.g., "en-US-Wavenet-F" vs "en-US-Standard-A").
4. **Kill switch** — A global flag to disable TTS synthesis entirely (e.g., if the TTS provider is having a major incident). This complements the circuit breaker.

## What We Intentionally Left Out (and Why)

| Feature                         | Why omitted                                                                                                                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Database persistence**        | This is a library, not a service. Persistence belongs in the caller.                                                                                                               |
| **Retry queue / DLQ**           | Out of scope for a library. The caller should implement a retry queue if needed.                                                                                                   |
| **Metrics export (Prometheus)** | Would add a dependency (`prometheus-client`). We log structured data instead; a log shipper can convert to metrics.                                                                |
| **Full Arabic/Spanish scripts** | The spec says stubs are acceptable for `es` and `ar`. The dispatch mechanism is production-shaped; filling in the scripts is a content task, not an engineering one.               |
| **Async generator**             | `generate_reminder` is synchronous because it's pure computation (string building). Making it async would add complexity without benefit.                                          |
| **SSML validation**             | We trust the generator to produce valid SSML. Adding an XML validator would be defensive but adds a dependency (`lxml`). We recommend adding it if callers can inject custom text. |
