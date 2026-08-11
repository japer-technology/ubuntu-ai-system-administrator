"""SQLite state with explicit retention and secret-minimising exports."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

from . import SESSION_LIFETIME_SECONDS
from .auth import valid_password_record
from .errors import AuthenticationError, NotFoundError, ValidationError

SCHEMA_VERSION = 1
_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS conversations_by_updated
    ON conversations(updated_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL
        REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS messages_by_conversation
    ON messages(conversation_id, created_at, id);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    canonical_root TEXT NOT NULL UNIQUE,
    root_device INTEGER NOT NULL,
    root_inode INTEGER NOT NULL,
    sharing_mode TEXT NOT NULL CHECK (sharing_mode = 'friend-share'),
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    relative_path TEXT NOT NULL,
    operation TEXT NOT NULL,
    result TEXT NOT NULL,
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS workspace_events_by_time
    ON workspace_events(timestamp);

CREATE TABLE IF NOT EXISTS sessions (
    token_digest TEXT PRIMARY KEY,
    csrf_digest TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    revoked_at REAL
);

CREATE INDEX IF NOT EXISTS sessions_by_expiry
    ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS settings (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version INTEGER NOT NULL,
    model_base_url TEXT NOT NULL,
    model TEXT NOT NULL,
    history_retention_days INTEGER NOT NULL
        CHECK (history_retention_days BETWEEN 1 AND 365),
    audit_retention_days INTEGER NOT NULL
        CHECK (audit_retention_days BETWEEN 30 AND 3650),
    history_enabled INTEGER NOT NULL CHECK (history_enabled IN (0, 1)),
    suspended INTEGER NOT NULL CHECK (suspended IN (0, 1))
);

CREATE TABLE IF NOT EXISTS auth_state (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    password_hash TEXT NOT NULL,
    rotated_at REAL NOT NULL
);
"""


def _identifier() -> str:
    return str(uuid.uuid4())


class Database:
    """Own Friend state without sharing a connection between HTTP threads."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _secure_journal(self) -> None:
        journal = self.path.with_name(f"{self.path.name}-journal")
        if not (journal.exists() or journal.is_symlink()):
            return
        details = journal.lstat()
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise ValidationError("Friend SQLite journal must be one regular file.")
        os.chmod(journal, 0o600)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() or self.path.is_symlink():
            details = self.path.lstat()
            if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                raise ValidationError("Friend state database must be one regular file.")
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = PERSIST")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA secure_delete = ON")
        try:
            self._secure_journal()
        except ValidationError:
            connection.close()
            raise
        return connection

    def initialize(
        self,
        *,
        password_hash: str,
        model_base_url: str,
        model: str,
        history_retention_days: int,
        audit_retention_days: int,
    ) -> None:
        """Create schema and initial settings while preserving valid auth."""
        if not valid_password_record(password_hash):
            raise ValidationError("The owner password record is invalid.")
        with self._connect() as connection:
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current > SCHEMA_VERSION:
                raise ValidationError("Friend state was created by a newer release.")
            connection.executescript(_SCHEMA)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.execute(
                """
                INSERT INTO settings(
                    singleton, schema_version, model_base_url, model,
                    history_retention_days, audit_retention_days,
                    history_enabled, suspended
                ) VALUES (1, ?, ?, ?, ?, ?, 1, 0)
                ON CONFLICT(singleton) DO UPDATE SET
                    schema_version = excluded.schema_version
                """,
                (
                    SCHEMA_VERSION,
                    model_base_url,
                    model,
                    history_retention_days,
                    audit_retention_days,
                ),
            )
            row = connection.execute(
                "SELECT password_hash FROM auth_state WHERE singleton = 1"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO auth_state(singleton, password_hash, rotated_at) "
                    "VALUES (1, ?, ?)",
                    (password_hash, time.time()),
                )
            elif not valid_password_record(str(row["password_hash"])):
                raise ValidationError("Stored owner authentication state is invalid.")
        os.chmod(self.path, 0o600)
        self._secure_journal()

    def require_ready(self) -> None:
        """Fail closed when schema or authentication material is incomplete."""
        if not self.path.is_file():
            raise ValidationError("Friend state database is missing.")
        with self._connect() as connection:
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current != SCHEMA_VERSION:
                raise ValidationError("Friend state schema is not supported.")
            settings = connection.execute(
                "SELECT schema_version FROM settings WHERE singleton = 1"
            ).fetchone()
            auth = connection.execute(
                "SELECT password_hash FROM auth_state WHERE singleton = 1"
            ).fetchone()
        if settings is None or int(settings["schema_version"]) != SCHEMA_VERSION:
            raise ValidationError("Friend settings are incomplete.")
        if auth is None or not valid_password_record(str(auth["password_hash"])):
            raise ValidationError("Friend owner authentication is incomplete.")

    def integrity_check(self) -> str:
        with self._connect() as connection:
            return str(connection.execute("PRAGMA integrity_check").fetchone()[0])

    def settings(self) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT schema_version, model_base_url, model,
                       history_retention_days, audit_retention_days,
                       history_enabled, suspended
                FROM settings WHERE singleton = 1
                """
            ).fetchone()
        if row is None:
            raise ValidationError("Friend settings are missing.")
        return {
            "schema_version": int(row["schema_version"]),
            "model_base_url": str(row["model_base_url"]),
            "model": str(row["model"]),
            "history_retention_days": int(row["history_retention_days"]),
            "audit_retention_days": int(row["audit_retention_days"]),
            "history_enabled": bool(row["history_enabled"]),
            "suspended": bool(row["suspended"]),
        }

    def update_settings(self, changes: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "model_base_url",
            "model",
            "history_retention_days",
            "audit_retention_days",
            "history_enabled",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValidationError(f"Unknown setting: {sorted(unknown)[0]}")
        current = self.settings()
        merged = {**current, **changes}
        history_days = merged["history_retention_days"]
        audit_days = merged["audit_retention_days"]
        if (
            isinstance(history_days, bool)
            or not isinstance(history_days, int)
            or not 1 <= history_days <= 365
        ):
            raise ValidationError("History retention must be between 1 and 365 days.")
        if (
            isinstance(audit_days, bool)
            or not isinstance(audit_days, int)
            or not 30 <= audit_days <= 3650
        ):
            raise ValidationError("Audit retention must be between 30 and 3650 days.")
        if not isinstance(merged["history_enabled"], bool):
            raise ValidationError("history_enabled must be boolean.")
        if not isinstance(merged["model"], str) or not merged["model"].strip():
            raise ValidationError("Model ID must not be empty.")
        if (
            not isinstance(merged["model_base_url"], str)
            or not merged["model_base_url"].strip()
        ):
            raise ValidationError("Model endpoint must not be empty.")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE settings SET model_base_url = ?, model = ?,
                    history_retention_days = ?, audit_retention_days = ?,
                    history_enabled = ?
                WHERE singleton = 1
                """,
                (
                    merged["model_base_url"],
                    merged["model"],
                    history_days,
                    audit_days,
                    int(merged["history_enabled"]),
                ),
            )
            if "history_retention_days" in changes:
                connection.execute(
                    "UPDATE conversations "
                    "SET expires_at = updated_at + ?",
                    (history_days * 86_400,),
                )
        self.prune()
        return self.settings()

    def password_record(self) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM auth_state WHERE singleton = 1"
            ).fetchone()
        if row is None or not valid_password_record(str(row["password_hash"])):
            raise ValidationError("Friend owner authentication is invalid.")
        return str(row["password_hash"])

    def rotate_password(self, password_hash: str) -> None:
        if not valid_password_record(password_hash):
            raise ValidationError("The new password record is invalid.")
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "UPDATE auth_state SET password_hash = ?, rotated_at = ? "
                "WHERE singleton = 1",
                (password_hash, now),
            )
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE revoked_at IS NULL",
                (now,),
            )

    def create_session(
        self, token_digest: str, csrf_digest: str, *, now: float | None = None
    ) -> float:
        created = now if now is not None else time.time()
        expires = created + SESSION_LIFETIME_SECONDS
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions(
                    token_digest, csrf_digest, created_at, expires_at, revoked_at
                ) VALUES (?, ?, ?, ?, NULL)
                """,
                (token_digest, csrf_digest, created, expires),
            )
        return expires

    def active_session(
        self, token_digest: str, *, now: float | None = None
    ) -> dict[str, Any] | None:
        current = now if now is not None else time.time()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT token_digest, csrf_digest, created_at, expires_at
                FROM sessions
                WHERE token_digest = ? AND revoked_at IS NULL AND expires_at > ?
                """,
                (token_digest, current),
            ).fetchone()
        return dict(row) if row is not None else None

    def revoke_session(self, token_digest: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE sessions SET revoked_at = ? "
                "WHERE token_digest = ? AND revoked_at IS NULL",
                (time.time(), token_digest),
            )

    def replace_session_csrf(self, token_digest: str, csrf_digest: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE sessions SET csrf_digest = ?
                WHERE token_digest = ? AND revoked_at IS NULL AND expires_at > ?
                """,
                (csrf_digest, token_digest, time.time()),
            )
        if cursor.rowcount == 0:
            raise AuthenticationError("Session is expired or revoked.")

    def revoke_all_sessions(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE revoked_at IS NULL",
                (time.time(),),
            )

    def create_conversation(self, title: str) -> str:
        settings = self.settings()
        now = time.time()
        conversation_id = _identifier()
        expires = now + int(settings["history_retention_days"]) * 86_400
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations(id, title, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, title.strip()[:120] or "Conversation", now, now, expires),
            )
        return conversation_id

    def add_message(self, conversation_id: str, role: str, content: str) -> str:
        if role not in {"user", "assistant", "system"}:
            raise ValidationError("Message role is invalid.")
        if not isinstance(content, str) or not content:
            raise ValidationError("Message content must not be empty.")
        settings = self.settings()
        now = time.time()
        expires = now + int(settings["history_retention_days"]) * 86_400
        message_id = _identifier()
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if exists is None:
                raise NotFoundError("Conversation does not exist.")
            connection.execute(
                """
                INSERT INTO messages(id, conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, conversation_id, role, content, now),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ?, expires_at = ? WHERE id = ?",
                (now, expires, conversation_id),
            )
        return message_id

    def list_conversations(self, limit: int | None = 100) -> list[dict[str, Any]]:
        self.prune()
        parameters: tuple[int, ...] = ()
        limit_clause = ""
        if limit is not None:
            bounded = max(1, min(limit, 100))
            limit_clause = " LIMIT ?"
            parameters = (bounded,)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, created_at, updated_at, expires_at
                FROM conversations ORDER BY updated_at DESC
                """
                + limit_clause,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def conversation(self, conversation_id: str) -> dict[str, Any]:
        self.prune()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at, expires_at
                FROM conversations WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
            messages = connection.execute(
                """
                SELECT id, role, content, created_at FROM messages
                WHERE conversation_id = ? ORDER BY created_at, id
                """,
                (conversation_id,),
            ).fetchall()
        if row is None:
            raise NotFoundError("Conversation does not exist.")
        result = dict(row)
        result["messages"] = [dict(message) for message in messages]
        return result

    def delete_conversation(self, conversation_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?", (conversation_id,)
            )
        if cursor.rowcount == 0:
            raise NotFoundError("Conversation does not exist.")

    def export(self) -> dict[str, Any]:
        self.prune()
        settings = self.settings()
        safe_settings = {
            key: settings[key]
            for key in (
                "schema_version",
                "model_base_url",
                "model",
                "history_retention_days",
                "audit_retention_days",
                "history_enabled",
                "suspended",
            )
        }
        with self._connect() as connection:
            connection.execute("BEGIN")
            conversation_rows = connection.execute(
                """
                SELECT id, title, created_at, updated_at, expires_at
                FROM conversations ORDER BY updated_at DESC
                """
            ).fetchall()
            message_rows = connection.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM messages ORDER BY conversation_id, created_at, id
                """
            ).fetchall()
        conversations = [dict(row) for row in conversation_rows]
        by_id = {str(item["id"]): item for item in conversations}
        for item in conversations:
            item["messages"] = []
        for row in message_rows:
            conversation = by_id.get(str(row["conversation_id"]))
            if conversation is not None:
                conversation["messages"].append(
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "content": row["content"],
                        "created_at": row["created_at"],
                    }
                )
        return {
            "export_version": 1,
            "product_id": "imaginary-friend",
            "exported_at": time.time(),
            "configuration": safe_settings,
            "conversations": conversations,
            "workspaces": self.list_workspaces(),
        }

    def register_workspace(
        self,
        *,
        canonical_root: str,
        root_device: int,
        root_inode: int,
        enabled: bool = True,
    ) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM workspaces WHERE canonical_root = ?",
                (canonical_root,),
            ).fetchone()
            if row is None:
                workspace_id = _identifier()
                connection.execute(
                    """
                    INSERT INTO workspaces(
                        id, canonical_root, root_device, root_inode,
                        sharing_mode, enabled, created_at
                    ) VALUES (?, ?, ?, ?, 'friend-share', ?, ?)
                    """,
                    (
                        workspace_id,
                        canonical_root,
                        root_device,
                        root_inode,
                        int(enabled),
                        time.time(),
                    ),
                )
            else:
                workspace_id = str(row["id"])
                connection.execute(
                    """
                    UPDATE workspaces SET root_device = ?, root_inode = ?,
                        enabled = ? WHERE id = ?
                    """,
                    (root_device, root_inode, int(enabled), workspace_id),
                )
        return workspace_id

    def list_workspaces(self, *, include_disabled: bool = True) -> list[dict[str, Any]]:
        where = "" if include_disabled else " WHERE enabled = 1"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, canonical_root, root_device, root_inode,
                       sharing_mode, enabled, created_at
                FROM workspaces
                """
                + where
                + " ORDER BY created_at, id"
            ).fetchall()
        result = [dict(row) for row in rows]
        for item in result:
            item["enabled"] = bool(item["enabled"])
        return result

    def workspace(self, workspace_id: str, *, require_enabled: bool = True) -> dict[str, Any]:
        clause = " AND enabled = 1" if require_enabled else ""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, canonical_root, root_device, root_inode,
                       sharing_mode, enabled, created_at
                FROM workspaces WHERE id = ?
                """
                + clause,
                (workspace_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError("Workspace does not exist or is disabled.")
        result = dict(row)
        result["enabled"] = bool(result["enabled"])
        return result

    def set_workspace_enabled(self, workspace_id: str, enabled: bool) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE workspaces SET enabled = ? WHERE id = ?",
                (int(enabled), workspace_id),
            )
        if cursor.rowcount == 0:
            raise NotFoundError("Workspace does not exist.")

    def workspace_event(
        self, workspace_id: str, relative_path: str, operation: str, result: str
    ) -> str:
        event_id = _identifier()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workspace_events(
                    id, workspace_id, relative_path, operation, result, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    workspace_id,
                    relative_path,
                    operation,
                    result,
                    time.time(),
                ),
            )
        return event_id

    def workspace_events(self, limit: int = 200) -> list[dict[str, Any]]:
        self.prune()
        bounded = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, workspace_id, relative_path, operation, result, timestamp
                FROM workspace_events ORDER BY timestamp DESC LIMIT ?
                """,
                (bounded,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_suspended(self, suspended: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE settings SET suspended = ? WHERE singleton = 1",
                (int(suspended),),
            )
            if suspended:
                connection.execute(
                    "UPDATE sessions SET revoked_at = ? WHERE revoked_at IS NULL",
                    (time.time(),),
                )

    def prune(self, *, now: float | None = None) -> None:
        current = now if now is not None else time.time()
        settings = self.settings()
        audit_cutoff = current - int(settings["audit_retention_days"]) * 86_400
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM conversations WHERE expires_at <= ?", (current,)
            )
            connection.execute(
                "DELETE FROM sessions WHERE expires_at <= ? OR revoked_at IS NOT NULL",
                (current,),
            )
            connection.execute(
                "DELETE FROM workspace_events WHERE timestamp < ?", (audit_cutoff,)
            )

    def backup_to(self, destination: Path) -> None:
        """Create a consistent SQLite copy and revoke sessions in that copy."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
                target.execute("DELETE FROM sessions")
                target.commit()
            finally:
                target.close()
        os.chmod(destination, 0o600)

    def table_names(self) -> Iterator[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        return (str(row["name"]) for row in rows)

    def export_json(self) -> str:
        return json.dumps(self.export(), ensure_ascii=False, sort_keys=True)
