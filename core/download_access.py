"""Owner-only download access and privacy-preserving interest telemetry."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import os
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / ".local" / "download_interest.sqlite3"
DEFAULT_OWNER_USERNAME = "fxtrader81"
DEFAULT_CONTACT_EMAIL = "fxtrader81@gmail.com"


def _secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def owner_username() -> str:
    return _secret("DOWNLOAD_OWNER_USERNAME") or DEFAULT_OWNER_USERNAME


def contact_email() -> str:
    return _secret("DOWNLOAD_CONTACT_EMAIL") or DEFAULT_CONTACT_EMAIL


def credentials_configured() -> bool:
    return bool(_secret("DOWNLOAD_OWNER_PASSWORD"))


def verify_owner_credentials(username: str, password: str) -> bool:
    configured_password = _secret("DOWNLOAD_OWNER_PASSWORD")
    if not configured_password:
        return False
    return hmac.compare_digest(str(username).strip(), owner_username()) and hmac.compare_digest(
        str(password), configured_password
    )


def _connect(path: Path | str):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS download_interest (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               resource TEXT NOT NULL,
               session_hash TEXT NOT NULL,
               clicked_at TEXT NOT NULL
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_download_interest_time "
        "ON download_interest(clicked_at DESC)"
    )
    return conn


def _session_hash(session_token: str) -> str:
    return hashlib.sha256(str(session_token).encode("utf-8")).hexdigest()


def record_interest(
    resource: str,
    session_token: str,
    *,
    path: Path | str | None = None,
    clicked_at: datetime | None = None,
) -> bool:
    """Store one anonymous click, suppressing rapid rerun duplicates."""
    if not resource or not session_token:
        raise ValueError("下载资料和会话标识不能为空")
    click_time = (clicked_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    timestamp = click_time.isoformat()
    session_hash = _session_hash(session_token)
    with closing(_connect(path or STORE)) as conn, conn:
        latest = conn.execute(
            """SELECT clicked_at FROM download_interest
               WHERE resource=? AND session_hash=? ORDER BY id DESC LIMIT 1""",
            (str(resource), session_hash),
        ).fetchone()
        if latest:
            latest_time = datetime.fromisoformat(latest[0]).astimezone(timezone.utc)
            elapsed = (click_time - latest_time).total_seconds()
            if 0 <= elapsed < 30:
                return False
        conn.execute(
            "INSERT INTO download_interest(resource, session_hash, clicked_at) VALUES(?,?,?)",
            (str(resource), session_hash, timestamp),
        )
    return True


def interest_stats(*, path: Path | str | None = None) -> dict:
    target = Path(path or STORE)
    if not target.exists():
        return {
            "total_clicks": 0,
            "approx_sessions": 0,
            "last_clicked_at": None,
            "by_resource": [],
            "storage": "local_sqlite_current_instance",
        }
    with closing(_connect(target)) as conn:
        total, sessions, last = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT session_hash), MAX(clicked_at) FROM download_interest"
        ).fetchone()
        rows = conn.execute(
            """SELECT resource, COUNT(*) AS clicks, COUNT(DISTINCT session_hash) AS sessions
               FROM download_interest GROUP BY resource ORDER BY clicks DESC, resource"""
        ).fetchall()
    return {
        "total_clicks": int(total),
        "approx_sessions": int(sessions),
        "last_clicked_at": last,
        "by_resource": [
            {"resource": resource, "clicks": int(clicks), "approx_sessions": int(unique_sessions)}
            for resource, clicks, unique_sessions in rows
        ],
        "storage": "local_sqlite_current_instance",
    }
