# Task 2b: Logic and Code Reading — Debugging Three Python Snippets

---

## Snippet A

```python
import asyncio, requests


async def send_reminders(appointments):
    results = []
    for appt in appointments:
        r = requests.post("https://tts/api", json=appt, timeout=5)
        results.append(r.json())
    return results


asyncio.run(send_reminders(load_appointments()))
```

### The Bug(s)

**Bug 1: Blocking I/O in an async function.** `requests.post()` is a synchronous, blocking call. Inside an `async def`, this blocks the entire event loop — no other coroutines can run while waiting for the HTTP response. The function is declared `async` but gains zero benefit from it.

**Bug 2: Missing `await`.** Even if `requests` were replaced with an async HTTP library (e.g., `httpx`), the call is not awaited. The coroutine would be created but never executed, and `r` would be a coroutine object, not a response.

### Root Cause

Python's `asyncio` event loop is single-threaded. Calling a synchronous I/O function (like `requests.post`) inside a coroutine blocks the entire loop. The `async def` keyword does not magically make synchronous code asynchronous — it only enables the use of `await`. The developer confused "declaring a function async" with "making it non-blocking."

### Production Blast Radius

At 2 a.m., when the reminder service processes 500 appointments:

- Each `requests.post()` blocks the event loop for ~200ms (TTS API latency).
- 500 appointments × 200ms = 100 seconds of sequential blocking.
- The service appears hung. Health checks time out. The orchestrator kills and restarts the pod.
- On restart, the same backlog is re-queued, causing a crash loop.
- Meanwhile, patients don't get their reminders because the TTS requests never complete in time.

### Fix

Replace `requests` with `httpx.AsyncClient` and `await` the call:

```python
import asyncio
import httpx


async def send_reminders(appointments):
    async with httpx.AsyncClient() as client:
        results = []
        for appt in appointments:
            r = await client.post("https://tts/api", json=appt, timeout=5)
            results.append(r.json())
        return results


asyncio.run(send_reminders(load_appointments()))
```

---

## Snippet B

```python
def reminder_attempts(appointment_id, history={}):
    history[appointment_id] = history.get(appointment_id, 0) + 1
    if history[appointment_id] > 3:
        raise RuntimeError("max retries exceeded")
    return history[appointment_id]
```

### The Bug(s)

**Bug: Mutable default argument.** `history={}` is evaluated once at function definition time, not at call time. All calls to `reminder_attempts` share the _same_ dictionary object. This means retry counts leak across different appointment IDs and across different callers.

### Root Cause

In Python, default argument values are evaluated when the `def` statement is executed (i.e., when the module loads), not when the function is called. Mutable objects like `list` and `dict` accumulate state across calls. This is a well-known Python gotcha (see [Python docs](https://docs.python.org/3/tutorial/controlflow.html#default-argument-values)).

### Production Blast Radius

At 2 a.m., two different workflows call `reminder_attempts`:

- Workflow A retries appointment `apt-001` three times (history = `{"apt-001": 3}`).
- Workflow B retries appointment `apt-002` once (history = `{"apt-001": 3, "apt-002": 1}`).
- Workflow A retries `apt-001` again: `history["apt-001"]` is already 3, so it raises `RuntimeError("max retries exceeded")` prematurely.
- The reminder for `apt-001` is silently dropped. The patient never gets their reminder.
- Worse, if the function is used in a long-running process, the dict grows unboundedly, causing a memory leak.

### Fix

Use `None` as the default and create a new dict inside the function:

```python
def reminder_attempts(appointment_id, history=None):
    if history is None:
        history = {}
    history[appointment_id] = history.get(appointment_id, 0) + 1
    if history[appointment_id] > 3:
        raise RuntimeError("max retries exceeded")
    return history[appointment_id]
```

---

## Snippet C

```python
def deliver(reminder):
    try:
        send_to_tts(reminder)
        log("delivered")
    except TTSError as e:
        log(f"tts failed: {e}")
        raise
    finally:
        return "ok"
```

### The Bug(s)

**Bug: `finally` block overrides the exception.** The `finally` clause executes unconditionally and returns `"ok"`. In Python, a `return` in a `finally` block suppresses any active exception (including the `raise` in the `except` block). The caller always receives `"ok"`, even when `send_to_tts` fails.

### Root Cause

Python's exception handling semantics: if a `finally` clause contains a `return`, `break`, or `continue`, any pending exception is discarded. The `return "ok"` in `finally` effectively swallows the `TTSError`. This is documented behaviour (see [Python docs](https://docs.python.org/3/reference/compound_stmts.html#the-try-statement)), but it's counterintuitive and rarely what you want.

### Production Blast Radius

At 2 a.m., `send_to_tts` fails with a `TTSError` (e.g., TTS provider is down). The `except` block logs the error and re-raises. But `finally` returns `"ok"`. The caller sees a successful result and marks the reminder as "delivered." The patient never receives their reminder, but the system thinks it was sent. No alert fires. No retry happens. The failure is completely silent.

### Fix

Remove the `finally` block, or move the `return` outside the `try`/`except`:

```python
def deliver(reminder):
    try:
        send_to_tts(reminder)
        log("delivered")
        return "ok"
    except TTSError as e:
        log(f"tts failed: {e}")
        raise
```

Or, if cleanup is needed in `finally`, do not return from it:

```python
def deliver(reminder):
    try:
        send_to_tts(reminder)
        log("delivered")
    except TTSError as e:
        log(f"tts failed: {e}")
        raise
    finally:
        cleanup()  # no return here
    return "ok"
```
