import uuid
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def uuid4_str() -> str:
    return str(uuid.uuid4())

