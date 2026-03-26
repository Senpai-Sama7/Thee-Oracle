#!/usr/bin/env python3
"""
Oracle state persistence helper.

This legacy infrastructure helper now mirrors the safe JSON serialization
approach used by the maintained runtime instead of `pickle`.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from google.genai import types


class OraclePersistence:
    """
    Persistent storage for Gemini chat history and thought signatures.

    History is stored as JSON-safe data, not pickled Python objects, so that
    loading persisted state cannot execute attacker-controlled content.
    """

    def __init__(self, db_path: str = "oracle_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    history_json TEXT,
                    thought_signatures TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON sessions(last_updated)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_metadata (
                    session_id TEXT,
                    key TEXT,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, key),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
                """
            )
            self._migrate_legacy_schema(conn)

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
        }
        if "history_json" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN history_json TEXT")

    @staticmethod
    def _serialize_history(history: list[types.Content]) -> str:
        return json.dumps([turn.model_dump(mode="json") for turn in history])

    @staticmethod
    def _deserialize_history(raw_history: str) -> list[types.Content]:
        payload = json.loads(raw_history)
        return [types.Content.model_validate(item) for item in payload]

    def save_session(self, session_id: str, history: list[types.Content]) -> None:
        try:
            history_json = self._serialize_history(history)
            signatures = self._extract_thought_signatures(history)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions
                    (session_id, history_json, thought_signatures, last_updated)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (session_id, history_json, json.dumps(signatures)),
                )
        except Exception as exc:
            print(f"[!] Persistence save error: {exc}")
            raise

    def load_session(self, session_id: str) -> list[types.Content]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT history_json FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()

            if not row or not row[0]:
                return []
            return self._deserialize_history(row[0])
        except Exception as exc:
            print(f"[!] Persistence load error: {exc}")
            return []

    def validate_session_freshness(self, session_id: str, max_age_hours: int = 24) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT last_updated FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()

            if not row:
                return False
            last_updated = datetime.fromisoformat(row[0])
            return datetime.now() - last_updated < timedelta(hours=max_age_hours)
        except Exception as exc:
            print(f"[!] Session validation error: {exc}")
            return False

    def cleanup_expired_sessions(self, max_age_hours: int = 168) -> int:
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE last_updated < ?",
                    (cutoff_time.isoformat(),),
                )
                return cursor.rowcount
        except Exception as exc:
            print(f"[!] Cleanup error: {exc}")
            return 0

    def list_sessions(self) -> list[dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT session_id, last_updated, created_at
                    FROM sessions
                    ORDER BY last_updated DESC
                    """
                ).fetchall()

            return [
                {
                    "session_id": row[0],
                    "last_updated": row[1],
                    "created_at": row[2],
                }
                for row in rows
            ]
        except Exception as exc:
            print(f"[!] List sessions error: {exc}")
            return []

    def get_session_stats(self) -> dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
                active_sessions = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE last_updated > ?",
                    ((datetime.now() - timedelta(hours=24)).isoformat(),),
                ).fetchone()[0]

            return {
                "database_size_mb": db_size / (1024 * 1024),
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "expired_sessions": total_sessions - active_sessions,
            }
        except Exception as exc:
            print(f"[!] Stats error: {exc}")
            return {}

    def _extract_thought_signatures(self, history: list[types.Content]) -> list[str]:
        signatures: list[str] = []
        try:
            for content in history:
                for part in getattr(content, "parts", []):
                    signature = getattr(part, "thought_signature", None)
                    if signature:
                        signatures.append(signature)
        except Exception as exc:
            print(f"[!] Signature extraction error: {exc}")
        return signatures

    def backup_database(self, backup_path: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            print(f"[+] Database backed up to {backup_path}")
        except Exception as exc:
            print(f"[!] Backup error: {exc}")
            raise

    def vacuum_database(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
            print("[+] Database vacuumed successfully")
        except Exception as exc:
            print(f"[!] Vacuum error: {exc}")
            raise
