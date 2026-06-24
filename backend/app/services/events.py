import json
from collections.abc import Generator

from redis import Redis

from app.core.config import settings

redis_connection = Redis.from_url(settings.redis_url, decode_responses=True)


def publish_event(job_id: str, event: dict) -> None:
    payload = json.dumps(event, ensure_ascii=False)
    history_key = _history_key(job_id)
    redis_connection.rpush(history_key, payload)
    redis_connection.ltrim(history_key, -settings.event_history_limit, -1)
    redis_connection.publish(_channel(job_id), payload)


def event_stream(job_id: str) -> Generator[str, None, None]:
    history_key = _history_key(job_id)
    for payload in redis_connection.lrange(history_key, 0, -1):
        yield _format_sse(payload)

    pubsub = redis_connection.pubsub()
    pubsub.subscribe(_channel(job_id))
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=15)
            if message and message.get("data"):
                yield _format_sse(str(message["data"]))
            else:
                yield ": keep-alive\n\n"
    finally:
        pubsub.close()


def _channel(job_id: str) -> str:
    return f"job:{job_id}:events"


def _history_key(job_id: str) -> str:
    return f"job:{job_id}:events:history"


def _format_sse(payload: str) -> str:
    return f"data: {payload}\n\n"
