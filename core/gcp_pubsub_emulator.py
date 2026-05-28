"""Delegate Pub/Sub to the official Google Pub/Sub emulator (P1.2).

When PUBSUB_EMULATOR_HOST is set, the simulator's REST/console handlers route
through these helpers so the console and any external gRPC SDK (pointed at the
same emulator + project) share ONE state. Topics/subscriptions are namespaced by
the active space's GCP project, preserving the space=project model.

All calls are synchronous gRPC; async handlers should wrap them in
asyncio.to_thread to avoid blocking the event loop.
"""
from __future__ import annotations

import base64
import os
from functools import lru_cache
from typing import Any


def _host() -> str:
    return os.environ.get("PUBSUB_EMULATOR_HOST") or os.environ.get("CLOUDLEARN_PUBSUB_EMULATOR_HOST") or ""


def available() -> bool:
    if not _host():
        return False
    try:
        import google.cloud.pubsub_v1  # noqa: F401
        return True
    except Exception:
        return False


def _ensure_env() -> None:
    h = _host()
    if h and not os.environ.get("PUBSUB_EMULATOR_HOST"):
        os.environ["PUBSUB_EMULATOR_HOST"] = h


@lru_cache(maxsize=1)
def _publisher():
    _ensure_env()
    from google.cloud import pubsub_v1
    return pubsub_v1.PublisherClient()


@lru_cache(maxsize=1)
def _subscriber():
    _ensure_env()
    from google.cloud import pubsub_v1
    return pubsub_v1.SubscriberClient()


# ── Topics ────────────────────────────────────────────────────────────────
def list_topics(project: str) -> list[dict]:
    pub = _publisher()
    out = []
    for t in pub.list_topics(request={"project": f"projects/{project}"}):
        out.append({"name": t.name.split("/")[-1], "labels": dict(t.labels),
                    "messageRetentionDuration": _dur(t.message_retention_duration),
                    "kmsKeyName": t.kms_key_name or ""})
    return out


def create_topic(project: str, topic_id: str, labels: dict | None = None) -> dict:
    pub = _publisher()
    path = pub.topic_path(project, topic_id)
    req: dict[str, Any] = {"name": path}
    if labels:
        req["labels"] = labels
    t = pub.create_topic(request=req)
    return {"name": topic_id, "labels": dict(t.labels)}


def get_topic(project: str, topic_id: str) -> dict | None:
    from google.api_core import exceptions
    pub = _publisher()
    try:
        t = pub.get_topic(request={"topic": pub.topic_path(project, topic_id)})
    except exceptions.NotFound:
        return None
    return {"name": topic_id, "labels": dict(t.labels),
            "messageRetentionDuration": _dur(t.message_retention_duration),
            "kmsKeyName": t.kms_key_name or ""}


def delete_topic(project: str, topic_id: str) -> bool:
    from google.api_core import exceptions
    pub = _publisher()
    try:
        pub.delete_topic(request={"topic": pub.topic_path(project, topic_id)})
        return True
    except exceptions.NotFound:
        return False


def publish(project: str, topic_id: str, data: bytes, attributes: dict | None = None, ordering_key: str = "") -> str:
    pub = _publisher()
    future = pub.publish(pub.topic_path(project, topic_id), data=data,
                         ordering_key=ordering_key or "", **(attributes or {}))
    return future.result(timeout=10)


# ── Subscriptions ───────────────────────────────────────────────────────────
def list_subscriptions(project: str) -> list[dict]:
    sub = _subscriber()
    out = []
    for s in sub.list_subscriptions(request={"project": f"projects/{project}"}):
        out.append(_sub_to_dict(s))
    return out


def create_subscription(project: str, sub_id: str, topic_id: str, ack_deadline: int = 10,
                        retention: str = "", labels: dict | None = None,
                        enable_ordering: bool = False) -> dict:
    sub = _subscriber()
    pub = _publisher()
    req: dict[str, Any] = {
        "name": sub.subscription_path(project, sub_id),
        "topic": pub.topic_path(project, topic_id),
        "ack_deadline_seconds": int(ack_deadline or 10),
        "enable_message_ordering": bool(enable_ordering),
    }
    if labels:
        req["labels"] = labels
    s = sub.create_subscription(request=req)
    return _sub_to_dict(s)


def get_subscription(project: str, sub_id: str) -> dict | None:
    from google.api_core import exceptions
    sub = _subscriber()
    try:
        s = sub.get_subscription(request={"subscription": sub.subscription_path(project, sub_id)})
    except exceptions.NotFound:
        return None
    return _sub_to_dict(s)


def delete_subscription(project: str, sub_id: str) -> bool:
    from google.api_core import exceptions
    sub = _subscriber()
    try:
        sub.delete_subscription(request={"subscription": sub.subscription_path(project, sub_id)})
        return True
    except exceptions.NotFound:
        return False


def pull(project: str, sub_id: str, max_messages: int = 1) -> list[dict]:
    sub = _subscriber()
    resp = sub.pull(request={"subscription": sub.subscription_path(project, sub_id),
                             "max_messages": max(1, int(max_messages or 1))}, timeout=5)
    received = []
    for rm in resp.received_messages:
        m = rm.message
        received.append({
            "ackId": rm.ack_id,
            "deliveryAttempt": rm.delivery_attempt or 0,
            "message": {
                "data": base64.b64encode(m.data or b"").decode("ascii"),
                "messageId": m.message_id,
                "attributes": dict(m.attributes),
                "orderingKey": m.ordering_key or "",
                "publishTime": m.publish_time.rfc3339() if m.publish_time else "",
            },
        })
    return received


def acknowledge(project: str, sub_id: str, ack_ids: list[str]) -> None:
    sub = _subscriber()
    if ack_ids:
        sub.acknowledge(request={"subscription": sub.subscription_path(project, sub_id), "ack_ids": ack_ids})


# ── helpers ──────────────────────────────────────────────────────────────────
def topic_subscriptions(project: str, topic_id: str) -> list[str]:
    pub = _publisher()
    try:
        return [s.split("/")[-1] for s in pub.list_topic_subscriptions(
            request={"topic": pub.topic_path(project, topic_id)})]
    except Exception:
        return []


def _sub_to_dict(s) -> dict:
    return {
        "name": s.name.split("/")[-1],
        "topic": s.topic.split("/")[-1] if s.topic else "",
        "ackDeadlineSeconds": s.ack_deadline_seconds or 10,
        "retainAckedMessages": bool(s.retain_acked_messages),
        "messageRetentionDuration": _dur(s.message_retention_duration),
        "labels": dict(s.labels),
        "enableMessageOrdering": bool(s.enable_message_ordering),
    }


def _dur(d) -> str:
    try:
        secs = int(d.total_seconds()) if hasattr(d, "total_seconds") else int(getattr(d, "seconds", 0))
        return f"{secs}s" if secs else ""  # empty when unset (topics have no default retention)
    except Exception:
        return ""
