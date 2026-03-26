#!/usr/bin/env python3
"""
Oracle State Persistence Layer for Gemini 3.1 Pro
Handles serialization of chat history and thought signatures for stateful reasoning
"""

import sqlite3
import pickle
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from google.genai import types

class OraclePersistence:
    """
    Persistent storage for Gemini 3.1 Pro chat history and thought signatures.
    Ensures stateful reasoning across service restarts and crashes.
    """

    def __init__(self, db_path: str = "oracle_state.db"):
        """
        Initialize the persistence layer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    history_blob BLOB,
                    thought_signatures TEXT,  -- JSON array of active signatures
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_updated
                ON sessions(last_updated)
            """)

            # Table for session metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_metadata (
                    session_id TEXT,
                    key TEXT,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (session_id, key),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

    def save_session(self, session_id: str, history: List[types.Content]):
        """
        Save the complete conversation history with thought signatures.

        Args:
            session_id: Unique identifier for the session
            history: List of types.Content objects from the conversation
        """
        try:
            # Serialize the history
            history_blob = pickle.dumps(history)

            # Extract thought signatures from history
            signatures = self._extract_thought_signatures(history)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO sessions
                       (session_id, history_blob, thought_signatures, last_updated)
                       VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                    (session_id, history_blob, json.dumps(signatures))
                )

        except Exception as e:
            print(f"[!] Persistence save error: {e}")
            raise

    def load_session(self, session_id: str) -> List[types.Content]:
        """
        Load conversation history for a session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            List of types.Content objects, or empty list if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT history_blob FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()

                if row:
                    return pickle.loads(row[0])
                else:
                    return []

        except Exception as e:
            print(f"[!] Persistence load error: {e}")
            return []

    def validate_session_freshness(self, session_id: str, max_age_hours: int = 24) -> bool:
        """
        Check if a session is still fresh (within thought signature TTL).

        Args:
            session_id: Session to check
            max_age_hours: Maximum age in hours (default 24 for 3.1 Pro signatures)

        Returns:
            True if session is fresh, False if expired
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT last_updated FROM sessions WHERE session_id = ?",
                    (session_id,)
                ).fetchone()

                if row:
                    last_updated = datetime.fromisoformat(row[0])
                    max_age = timedelta(hours=max_age_hours)
                    return datetime.now() - last_updated < max_age
                else:
                    return False

        except Exception as e:
            print(f"[!] Session validation error: {e}")
            return False

    def cleanup_expired_sessions(self, max_age_hours: int = 168) -> int:
        """
        Remove sessions older than the specified age.

        Args:
            max_age_hours: Maximum age in hours (default 7 days)

        Returns:
            Number of sessions removed
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE last_updated < ?",
                    (cutoff_time.isoformat(),)
                )
                return cursor.rowcount

        except Exception as e:
            print(f"[!] Cleanup error: {e}")
            return 0

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions with metadata.

        Returns:
            List of session dictionaries with metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT session_id, last_updated, created_at
                    FROM sessions
                    ORDER BY last_updated DESC
                """).fetchall()

                return [
                    {
                        "session_id": row[0],
                        "last_updated": row[1],
                        "created_at": row[2]
                    }
                    for row in rows
                ]

        except Exception as e:
            print(f"[!] List sessions error: {e}")
            return []

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get database file size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

                # Get session counts
                total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
                active_sessions = conn.execute(
                    "SELECT COUNT(*) FROM sessions WHERE last_updated > ?",
                    ((datetime.now() - timedelta(hours=24)).isoformat(),)
                ).fetchone()[0]

                return {
                    "database_size_mb": db_size / (1024 * 1024),
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "expired_sessions": total_sessions - active_sessions
                }

        except Exception as e:
            print(f"[!] Stats error: {e}")
            return {}

    def _extract_thought_signatures(self, history: List[types.Content]) -> List[str]:
        """
        Extract thought signatures from conversation history.

        Args:
            history: List of types.Content objects

        Returns:
            List of thought signature strings
        """
        signatures = []

        try:
            for content in history:
                if hasattr(content, 'parts'):
                    for part in content.parts:
                        if hasattr(part, 'thought_signature') and part.thought_signature:
                            signatures.append(part.thought_signature)
        except Exception as e:
            print(f"[!] Signature extraction error: {e}")

        return signatures

    def backup_database(self, backup_path: str):
        """
        Create a backup of the database.

        Args:
            backup_path: Path for the backup file
        """
        try:
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            print(f"[+] Database backed up to {backup_path}")

        except Exception as e:
            print(f"[!] Backup error: {e}")
            raise

    def vacuum_database(self):
        """Optimize the database by reclaiming unused space."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
            print("[+] Database vacuumed successfully")

        except Exception as e:
            print(f"[!] Vacuum error: {e}")
            raise
