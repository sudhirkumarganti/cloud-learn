"""Tamper-evident security audit trail with hash chain.

Each event includes prev_hash = SHA256(prev_entry_json + prev_hash),
forming an append-only chain. Breaking the chain (deleting/reordering
events) is detectable via verify_chain().
"""
from __future__ import annotations
import hashlib
import json
import os
import time
import sqlite3
import threading
from pathlib import Path

_DB_PATH = Path(os.environ.get("CLOUDLEARN_STATE_FILE",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cloudlearn_state.sqlite3")))
_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS security_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            source_ip TEXT DEFAULT '',
            timestamp TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL
        )
    """)
    conn.commit()


def _compute_hash(entry_json: str, prev_hash: str) -> str:
    return hashlib.sha256(f"{entry_json}|{prev_hash}".encode()).hexdigest()


def _get_last_hash(conn) -> str:
    row = conn.execute(
        "SELECT entry_hash FROM security_audit ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else hashlib.sha256(b"genesis").hexdigest()


def append_event(event_type: str, detail: dict | None = None,
                 request=None, source_ip: str = "") -> None:
    """Append a security event to the hash-chained audit log."""
    if request and not source_ip:
        try:
            source_ip = request.client.host if request.client else ""
        except Exception:
            pass
    detail_json = json.dumps(detail or {}, default=str)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    with _lock:
        try:
            conn = _connect()
            _ensure_schema(conn)
            prev_hash = _get_last_hash(conn)
            entry_json = json.dumps({
                "event_type": event_type,
                "detail": detail or {},
                "source_ip": source_ip,
                "timestamp": timestamp,
            }, default=str)
            entry_hash = _compute_hash(entry_json, prev_hash)
            conn.execute(
                "INSERT INTO security_audit (event_type, detail_json, source_ip, timestamp, prev_hash, entry_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (event_type, detail_json, source_ip, timestamp, prev_hash, entry_hash),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


def read_log(limit: int = 100, offset: int = 0) -> list[dict]:
    """Read recent audit events."""
    try:
        conn = _connect()
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, event_type, detail_json, source_ip, timestamp, prev_hash, entry_hash FROM security_audit ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "event_type": r[1], "detail": json.loads(r[2]),
             "source_ip": r[3], "timestamp": r[4], "prev_hash": r[5], "entry_hash": r[6]}
            for r in rows
        ]
    except Exception:
        return []


def verify_chain() -> tuple[bool, int, str]:
    """Verify the hash chain integrity. Returns (ok, broken_at_id, reason)."""
    try:
        conn = _connect()
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, event_type, detail_json, source_ip, timestamp, prev_hash, entry_hash FROM security_audit ORDER BY id ASC"
        ).fetchall()
        conn.close()
    except Exception:
        return True, 0, "unable_to_read"

    if not rows:
        return True, 0, ""

    expected_prev = hashlib.sha256(b"genesis").hexdigest()
    for row in rows:
        rid, event_type, detail_json, source_ip, timestamp, prev_hash, entry_hash = row
        if prev_hash != expected_prev:
            return False, rid, f"prev_hash mismatch at id={rid}"
        entry_json = json.dumps({
            "event_type": event_type,
            "detail": json.loads(detail_json),
            "source_ip": source_ip,
            "timestamp": timestamp,
        }, default=str)
        computed = _compute_hash(entry_json, prev_hash)
        if computed != entry_hash:
            return False, rid, f"entry_hash mismatch at id={rid}"
        expected_prev = entry_hash
    return True, 0, ""
