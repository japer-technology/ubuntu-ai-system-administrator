"""SQLite-backed conversation history.

The schema is forward-only and tracked via ``PRAGMA user_version``.
A structured ``events`` table stores ``tool_call`` /
``tool_observation`` / ``pending_tool_call`` records that the UI
renders alongside chat messages.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

_INSTALL_ROOT = Path(os.environ.get("AI_SYS_ADMIN_DIR", "/opt/ai-system-administrator"))
DB_PATH = Path(os.environ.get(
    "AI_SYS_ADMIN_HISTORY_DB", str(_INSTALL_ROOT / "state" / "conversations.db")
))

# Version 2 added durable reactivation. Version 3 narrowed its supported delay
# range. Version 4 raises the minimum delay to 5 seconds so the chat UI can
# settle between chained continuation turns. Version 5 records the most recent
# operator reset without deleting the older audit-supporting timer records.
SCHEMA_VERSION = 5

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  REAL NOT NULL,
    title       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    created_at      REAL NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    meta            TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS messages_by_conv
    ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    created_at      REAL NOT NULL,
    kind            TEXT NOT NULL,
    payload         TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS events_by_conv
    ON events(conversation_id, id);

CREATE TABLE IF NOT EXISTS reactivation_settings (
    singleton       INTEGER PRIMARY KEY CHECK (singleton = 1),
    enabled         INTEGER NOT NULL DEFAULT 1,
    minimum_seconds INTEGER NOT NULL DEFAULT 5,
    maximum_seconds INTEGER NOT NULL DEFAULT 3600,
    reset_at        REAL NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO reactivation_settings(singleton) VALUES (1);

CREATE TABLE IF NOT EXISTS reactivations (
    id              TEXT PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    created_at      REAL NOT NULL,
    fire_at         REAL NOT NULL,
    reason          TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    status          TEXT NOT NULL,
    actor           TEXT NOT NULL,
    error           TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS one_pending_reactivation
    ON reactivations(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS reactivations_due
    ON reactivations(status, fire_at);
"""


class History:
    def __init__(self, path: Path = DB_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Migration
    # ------------------------------------------------------------------
    def _migrate(self) -> None:
        cur = self._conn.execute("PRAGMA user_version")
        current = int(cur.fetchone()[0])
        if current >= SCHEMA_VERSION:
            return
        # Snapshot existing DB once, before any structural change. We
        # only snapshot if the file already contains user data — a
        # brand-new install has nothing worth backing up.
        try:
            has_data = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
            ).fetchone() is not None
        except sqlite3.DatabaseError:
            has_data = False
        if has_data and self._path.exists() and self._path.stat().st_size > 0:
            ts = time.strftime("%Y%m%dT%H%M%S", time.localtime())
            backup = self._path.with_name(f"{self._path.name}.bak.{ts}")
            try:
                shutil.copy2(self._path, backup)
            except OSError:
                # Best-effort: if the snapshot fails the migration
                # still proceeds — additive only, no destructive ops.
                pass
        if current < 4:
            has_reactivation_settings = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='reactivation_settings'"
            ).fetchone() is not None
            if has_reactivation_settings:
                self._conn.execute(
                    "UPDATE reactivation_settings SET "
                    "minimum_seconds = CASE "
                    "WHEN minimum_seconds = 30 THEN 5 "
                    "WHEN minimum_seconds < 5 THEN 5 "
                    "WHEN minimum_seconds > 3600 THEN 3600 "
                    "ELSE minimum_seconds END, "
                    "maximum_seconds = CASE "
                    "WHEN maximum_seconds = 86400 THEN 3600 "
                    "WHEN maximum_seconds < 5 THEN 5 "
                    "WHEN maximum_seconds > 3600 THEN 3600 "
                    "ELSE maximum_seconds END"
                )
                self._conn.execute(
                    "UPDATE reactivation_settings SET "
                    "maximum_seconds = minimum_seconds "
                    "WHERE maximum_seconds < minimum_seconds"
                )
        if current < 5:
            has_reactivation_settings = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='reactivation_settings'"
            ).fetchone() is not None
            if has_reactivation_settings:
                columns = {
                    str(row[1]) for row in self._conn.execute(
                        "PRAGMA table_info(reactivation_settings)"
                    ).fetchall()
                }
                if "reset_at" not in columns:
                    self._conn.execute(
                        "ALTER TABLE reactivation_settings "
                        "ADD COLUMN reset_at REAL NOT NULL DEFAULT 0"
                    )
        self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self._conn.commit()

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    @property
    def path(self) -> Path:
        """Return the SQLite database path backing this history store."""
        return self._path

    def create_conversation(self, title: str = "") -> int:
        cur = self._execute(
            "INSERT INTO conversations(created_at, title) VALUES (?, ?)",
            (time.time(), title),
        )
        return int(cur.lastrowid or 0)

    def list_conversations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, created_at, title FROM conversations "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [
                {"id": row[0], "created_at": row[1], "title": row[2]}
                for row in cur.fetchall()
            ]

    def usage_stats(self) -> dict[str, int]:
        """Return aggregate local conversation and tool usage counters."""
        with self._lock:
            conversations = int(self._conn.execute(
                "SELECT COUNT(*) FROM conversations"
            ).fetchone()[0])
            message_rows = self._conn.execute(
                "SELECT role, COUNT(*) FROM messages GROUP BY role"
            ).fetchall()
            event_rows = self._conn.execute(
                "SELECT kind, COUNT(*) FROM events GROUP BY kind"
            ).fetchall()
        messages = {str(role): int(count) for role, count in message_rows}
        events = {str(kind): int(count) for kind, count in event_rows}
        return {
            "conversations": conversations,
            "messages": sum(messages.values()),
            "user_messages": messages.get("user", 0),
            "assistant_messages": messages.get("assistant", 0),
            "tool_calls": events.get("tool_call", 0),
            "tool_observations": events.get("tool_observation", 0),
        }

    def get_conversation(self, conversation_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, created_at, title FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None
        return {"id": row[0], "created_at": row[1], "title": row[2]}

    def conversation_exists(self, conversation_id: int) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        return row is not None

    # ------------------------------------------------------------------
    # Timer reactivation
    # ------------------------------------------------------------------
    @staticmethod
    def _reactivation_row(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "id": row[0],
            "conversation_id": row[1],
            "created_at": row[2],
            "fire_at": row[3],
            "reason": row[4],
            "prompt": row[5],
            "status": row[6],
            "actor": row[7],
            "error": row[8],
        }

    def reactivation_settings(self) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT enabled, minimum_seconds, maximum_seconds "
                "FROM reactivation_settings WHERE singleton = 1"
            ).fetchone()
        return {
            "enabled": bool(row[0]),
            "minimum_seconds": int(row[1]),
            "maximum_seconds": int(row[2]),
        }

    def update_reactivation_settings(
        self,
        *,
        enabled: bool | None = None,
        minimum_seconds: int | None = None,
        maximum_seconds: int | None = None,
    ) -> dict[str, Any]:
        current = self.reactivation_settings()
        values = (
            int(current["enabled"] if enabled is None else enabled),
            int(current["minimum_seconds"] if minimum_seconds is None else minimum_seconds),
            int(current["maximum_seconds"] if maximum_seconds is None else maximum_seconds),
        )
        self._execute(
            "UPDATE reactivation_settings SET enabled = ?, minimum_seconds = ?, "
            "maximum_seconds = ? WHERE singleton = 1",
            values,
        )
        return self.reactivation_settings()

    def reset_reactivation(
        self,
        *,
        minimum_seconds: int,
        maximum_seconds: int,
    ) -> dict[str, Any] | None:
        """Restore defaults and retire the queued timer atomically.

        Existing timer rows remain available for audit and transcript
        reconstruction. ``reset_at`` makes pre-reset outcomes invisible to
        current status and starts continuation-chain numbering over.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT id, conversation_id, created_at, fire_at, reason, prompt, "
                "status, actor, error FROM reactivations "
                "WHERE status = 'pending' LIMIT 1"
            ).fetchone()
            pending = self._reactivation_row(row)
            reset_at = time.time()
            if pending is not None:
                self._conn.execute(
                    "UPDATE reactivations SET status = 'cancelled', "
                    "error = 'reset by operator' "
                    "WHERE id = ? AND status = 'pending'",
                    (pending["id"],),
                )
            self._conn.execute(
                "UPDATE reactivation_settings SET enabled = 1, "
                "minimum_seconds = ?, maximum_seconds = ?, reset_at = ? "
                "WHERE singleton = 1",
                (minimum_seconds, maximum_seconds, reset_at),
            )
            self._conn.commit()
        if pending is not None:
            pending["status"] = "cancelled"
            pending["error"] = "reset by operator"
        return pending

    def pending_reactivation(self) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, conversation_id, created_at, fire_at, reason, prompt, "
                "status, actor, error FROM reactivations "
                "WHERE status = 'pending' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return self._reactivation_row(row)

    def schedule_reactivation(
        self,
        conversation_id: int,
        fire_at: float,
        prompt: str,
        reason: str,
        *,
        actor: str = "agent",
        replace_existing: bool = False,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Create the one global pending timer, optionally replacing it."""
        with self._lock:
            existing_row = self._conn.execute(
                "SELECT id, conversation_id, created_at, fire_at, reason, prompt, "
                "status, actor, error FROM reactivations WHERE status = 'pending' "
                "LIMIT 1"
            ).fetchone()
            existing = self._reactivation_row(existing_row)
            if existing is not None and not replace_existing:
                return None, existing
            if existing is not None:
                self._conn.execute(
                    "UPDATE reactivations SET status = 'cancelled', "
                    "error = 'replaced' WHERE id = ? AND status = 'pending'",
                    (existing["id"],),
                )
            reactivation_id = uuid.uuid4().hex
            created_at = time.time()
            self._conn.execute(
                "INSERT INTO reactivations("
                "id, conversation_id, created_at, fire_at, reason, prompt, status, actor"
                ") VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                (reactivation_id, conversation_id, created_at, fire_at,
                 reason, prompt, actor),
            )
            self._conn.commit()
        return {
            "id": reactivation_id,
            "conversation_id": conversation_id,
            "created_at": created_at,
            "fire_at": fire_at,
            "reason": reason,
            "prompt": prompt,
            "status": "pending",
            "actor": actor,
            "error": None,
        }, existing

    def claim_due_reactivation(
        self,
        now: float,
        busy_conversations: Iterable[int] | None = None,
    ) -> dict[str, Any] | None:
        """Atomically claim a due timer so it can never fire twice.

        ``busy_conversations`` names conversations that already have a
        turn in flight; a timer for one of them is left pending so the
        continuation cannot run concurrently with the turn that is
        still producing the work it continues.
        """
        skip = {int(cid) for cid in (busy_conversations or ())}
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, conversation_id, created_at, fire_at, reason, prompt, "
                "status, actor, error FROM reactivations "
                "WHERE status = 'pending' AND fire_at <= ? "
                "ORDER BY fire_at",
                (now,),
            ).fetchall()
            item = None
            for row in rows:
                candidate = self._reactivation_row(row)
                if candidate is None:
                    continue
                if int(candidate["conversation_id"]) in skip:
                    continue
                item = candidate
                break
            if item is None:
                return None
            cur = self._conn.execute(
                "UPDATE reactivations SET status = 'firing' "
                "WHERE id = ? AND status = 'pending'",
                (item["id"],),
            )
            self._conn.commit()
            if cur.rowcount != 1:
                return None
        item["status"] = "firing"
        return item

    def last_reactivation(self) -> dict[str, Any] | None:
        """The most recent timer that already reached a terminal
        state, so operators can see why a continuation chain stopped."""
        with self._lock:
            reset_at = self._conn.execute(
                "SELECT reset_at FROM reactivation_settings WHERE singleton = 1"
            ).fetchone()[0]
            row = self._conn.execute(
                "SELECT id, conversation_id, created_at, fire_at, reason, prompt, "
                "status, actor, error FROM reactivations "
                "WHERE status NOT IN ('pending', 'firing') AND created_at > ? "
                "ORDER BY created_at DESC LIMIT 1",
                (reset_at,),
            ).fetchone()
        return self._reactivation_row(row)

    def count_reactivations(
        self, conversation_id: int, status: str = "fired"
    ) -> int:
        """How many timers in this conversation reached ``status``.

        Used to report continuation-chain depth so a chain that stops
        after a few turns can be diagnosed from the audit log."""
        with self._lock:
            reset_at = self._conn.execute(
                "SELECT reset_at FROM reactivation_settings WHERE singleton = 1"
            ).fetchone()[0]
            row = self._conn.execute(
                "SELECT COUNT(*) FROM reactivations "
                "WHERE conversation_id = ? AND status = ? AND created_at > ?",
                (conversation_id, status, reset_at),
            ).fetchone()
        return int(row[0]) if row else 0

    def finish_reactivation(
        self, reactivation_id: str, status: str, error: str | None = None
    ) -> bool:
        if status not in {"fired", "cancelled", "failed"}:
            raise ValueError(f"invalid terminal reactivation status: {status}")
        cur = self._execute(
            "UPDATE reactivations SET status = ?, error = ? "
            "WHERE id = ? AND status IN ('pending', 'firing')",
            (status, error, reactivation_id),
        )
        return cur.rowcount == 1

    def fail_orphaned_reactivations(self) -> list[dict[str, Any]]:
        """Mark timers claimed by a previous server process as failed."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, conversation_id, created_at, fire_at, reason, prompt, "
                "status, actor, error FROM reactivations WHERE status = 'firing'"
            ).fetchall()
            self._conn.execute(
                "UPDATE reactivations SET status = 'failed', "
                "error = 'server restarted while firing' "
                "WHERE status = 'firing'"
            )
            self._conn.commit()
        return [
            item for row in rows
            if (item := self._reactivation_row(row)) is not None
        ]

    def cancel_pending_reactivation(self, reason: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, conversation_id, created_at, fire_at, reason, prompt, "
                "status, actor, error FROM reactivations "
                "WHERE status = 'pending' LIMIT 1"
            ).fetchone()
            item = self._reactivation_row(row)
            if item is None:
                return None
            self._conn.execute(
                "UPDATE reactivations SET status = 'cancelled', error = ? "
                "WHERE id = ? AND status = 'pending'",
                (reason, item["id"]),
            )
            self._conn.commit()
        item["status"] = "cancelled"
        item["error"] = reason
        return item

    def set_title(self, conversation_id: int, title: str) -> bool:
        cur = self._execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title[:120], conversation_id),
        )
        return cur.rowcount > 0

    def add_message(self, conversation_id: int, role: str, content: str,
                    meta: dict[str, Any] | None = None) -> int:
        # FIX-3-17: insert + (conditional) title update must run in a
        # single transaction. Otherwise another reader can land between
        # the two commits and see a conversation with messages but
        # ``title = ''`` — which the UI then caches forever as
        # "(untitled)".
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO messages(conversation_id, created_at, role, "
                "content, meta) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, time.time(), role, content, meta_json),
            )
            message_id = int(cur.lastrowid or 0)
            if role == "user":
                row = self._conn.execute(
                    "SELECT title FROM conversations WHERE id = ?",
                    (conversation_id,),
                ).fetchone()
                if row and not row[0]:
                    self._conn.execute(
                        "UPDATE conversations SET title = ? WHERE id = ?",
                        (content[:60], conversation_id),
                    )
            self._conn.commit()
        return message_id

    def get_messages(self, conversation_id: int) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, created_at, role, content, meta FROM messages "
                "WHERE conversation_id = ? ORDER BY id ASC",
                (conversation_id,),
            )
            rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                meta = json.loads(row[4])
            except json.JSONDecodeError:
                meta = {}
            out.append({
                "id": row[0],
                "created_at": row[1],
                "role": row[2],
                "content": row[3],
                "meta": meta,
            })
        return out

    def latest_user_message(self, conversation_id: int,
                            offset: int = 0) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, created_at, role, content, meta FROM messages "
                "WHERE conversation_id = ? AND role = 'user' "
                "ORDER BY id DESC LIMIT 1 OFFSET ?",
                (conversation_id, max(offset, 0)),
            ).fetchone()
        if row is None:
            return None
        try:
            meta = json.loads(row[4])
        except json.JSONDecodeError:
            meta = {}
        return {
            "id": row[0],
            "created_at": row[1],
            "role": row[2],
            "content": row[3],
            "meta": meta,
        }

    def latest_summary(self, conversation_id: int) -> str | None:
        with self._lock:
            rows = self._conn.execute(
                "SELECT content, meta FROM messages "
                "WHERE conversation_id = ? AND role = 'system' "
                "ORDER BY id DESC",
                (conversation_id,),
            ).fetchall()
        for content, meta_json in rows:
            try:
                meta = json.loads(meta_json)
            except json.JSONDecodeError:
                meta = {}
            if meta.get("kind") == "summary":
                return str(content)
        return None

    def copy_conversation(self, conversation_id: int, *,
                          title: str = "",
                          before_message_id: int | None = None) -> int:
        """Copy a conversation, optionally truncating before a message.

        The source conversation is left untouched. When truncating, tool
        events at or after the cutoff message timestamp are omitted so a
        retry/undo branch does not replay events from turns it no longer
        contains.
        """
        with self._lock:
            source = self._conn.execute(
                "SELECT title FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if source is None:
                raise KeyError(f"conversation {conversation_id} not found")
            cutoff_ts: float | None = None
            message_where = "conversation_id = ?"
            message_params: list[Any] = [conversation_id]
            if before_message_id is not None:
                row = self._conn.execute(
                    "SELECT created_at FROM messages "
                    "WHERE conversation_id = ? AND id = ?",
                    (conversation_id, before_message_id),
                ).fetchone()
                if row is None:
                    raise KeyError(f"message {before_message_id} not found")
                cutoff_ts = float(row[0])
                message_where += " AND id < ?"
                message_params.append(before_message_id)

            chosen_title = (title or f"Branch of #{conversation_id}")[:120]
            cur = self._conn.execute(
                "INSERT INTO conversations(created_at, title) VALUES (?, ?)",
                (time.time(), chosen_title),
            )
            new_id = int(cur.lastrowid or 0)

            messages = self._conn.execute(
                "SELECT created_at, role, content, meta FROM messages "
                f"WHERE {message_where} ORDER BY id ASC",
                tuple(message_params),
            ).fetchall()
            for created_at, role, content, meta in messages:
                self._conn.execute(
                    "INSERT INTO messages(conversation_id, created_at, role, "
                    "content, meta) VALUES (?, ?, ?, ?, ?)",
                    (new_id, created_at, role, content, meta),
                )

            event_where = "conversation_id = ?"
            event_params: list[Any] = [conversation_id]
            if cutoff_ts is not None:
                event_where += " AND created_at < ?"
                event_params.append(cutoff_ts)
            events = self._conn.execute(
                "SELECT created_at, kind, payload FROM events "
                f"WHERE {event_where} ORDER BY id ASC",
                tuple(event_params),
            ).fetchall()
            for created_at, kind, payload in events:
                self._conn.execute(
                    "INSERT INTO events(conversation_id, created_at, kind, "
                    "payload) VALUES (?, ?, ?, ?)",
                    (new_id, created_at, kind, payload),
                )
            self._conn.commit()
            return new_id

    # ------------------------------------------------------------------
    # Events (Phase 2: tool_call / tool_observation / pending_tool_call)
    # ------------------------------------------------------------------
    def add_event(self, conversation_id: int, kind: str,
                  payload: dict[str, Any] | None = None) -> int:
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        cur = self._execute(
            "INSERT INTO events(conversation_id, created_at, kind, payload) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, time.time(), kind, payload_json),
        )
        return int(cur.lastrowid or 0)

    def get_events(self, conversation_id: int) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, created_at, kind, payload FROM events "
                "WHERE conversation_id = ? ORDER BY id ASC",
                (conversation_id,),
            )
            rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row[3])
            except json.JSONDecodeError:
                payload = {}
            out.append({
                "id": row[0],
                "created_at": row[1],
                "kind": row[2],
                "payload": payload,
            })
        return out

    def update_event(self, event_id: int, payload: dict[str, Any]) -> None:
        self._execute(
            "UPDATE events SET payload = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), event_id),
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
