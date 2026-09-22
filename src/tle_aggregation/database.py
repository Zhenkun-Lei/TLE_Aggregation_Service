from __future__ import annotations

import json
import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    payload_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS gp_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(run_id),
    source TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    norad_cat_id TEXT NOT NULL,
    object_name TEXT,
    object_id TEXT,
    epoch TEXT,
    raw_json TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    UNIQUE(source, norad_cat_id, epoch, record_hash)
);
CREATE INDEX IF NOT EXISTS idx_gp_norad_epoch
    ON gp_records(norad_cat_id, epoch DESC);
CREATE INDEX IF NOT EXISTS idx_gp_retrieved_at
    ON gp_records(retrieved_at DESC);
"""

LEGACY_SCHEMA_ERROR = (
    "database uses the legacy schema; run the compact command before fetching"
)


def _value(record: dict, *names: str):
    for name in names:
        if record.get(name) is not None:
            return record[name]
    return None


def _canonical_json(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _record_hash(record: dict) -> str:
    return hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def open_database(path: str | Path) -> sqlite3.Connection:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    if "record_hash" not in _columns(connection, "gp_records"):
        connection.close()
        raise RuntimeError(LEGACY_SCHEMA_ERROR)
    return connection


def ingest_gp_payload(
    database_path: str | Path,
    payload: bytes,
    source: str,
    payload_path: str,
    retrieved_at: str | None = None,
) -> tuple[int, int]:
    records = json.loads(payload)
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("GP payload must be a JSON array of objects")
    retrieved = retrieved_at or datetime.now(timezone.utc).isoformat()
    connection = open_database(database_path)
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO runs(source, retrieved_at, record_count, payload_path) VALUES (?, ?, ?, ?)",
                (source, retrieved, len(records), payload_path),
            )
            run_id = cursor.lastrowid
            for record in records:
                norad = _value(record, "NORAD_CAT_ID", "NORAD_CATNR", "norad_cat_id")
                if norad is None:
                    raise ValueError("GP record is missing NORAD_CAT_ID")
                connection.execute(
                    """INSERT OR IGNORE INTO gp_records
                    (run_id, source, retrieved_at, norad_cat_id, object_name,
                     object_id, epoch, raw_json, record_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, source, retrieved, str(norad),
                        _value(record, "OBJECT_NAME", "object_name"),
                        _value(record, "OBJECT_ID", "object_id"),
                        _value(record, "EPOCH", "epoch"),
                        json.dumps(record, ensure_ascii=False, sort_keys=True),
                        _record_hash(record),
                    ),
                )
        return int(run_id), len(records)
    finally:
        connection.close()


def last_run_at(database_path: str | Path) -> str | None:
    connection = open_database(database_path)
    try:
        row = connection.execute(
            "SELECT retrieved_at FROM runs ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        connection.close()


def migrate_database(database_path: str | Path) -> bool:
    """Migrate the legacy raw-JSON unique index to a compact hash index."""
    path = Path(database_path)
    if not path.exists():
        open_database(path).close()
        return False

    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        if "gp_records" not in {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }:
            connection.executescript(SCHEMA)
            return False
        if "record_hash" in _columns(connection, "gp_records"):
            return False

        with connection:
            connection.execute(
                """CREATE TABLE gp_records_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES runs(run_id),
                    source TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    norad_cat_id TEXT NOT NULL,
                    object_name TEXT,
                    object_id TEXT,
                    epoch TEXT,
                    raw_json TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    UNIQUE(source, norad_cat_id, epoch, record_hash)
                )"""
            )
            rows = connection.execute(
                """SELECT id, run_id, source, retrieved_at, norad_cat_id,
                    object_name, object_id, epoch, raw_json
                    FROM gp_records ORDER BY id"""
            )
            for row in rows:
                raw_json = row[8]
                record_hash = _record_hash(json.loads(raw_json))
                connection.execute(
                    """INSERT OR IGNORE INTO gp_records_new
                        (id, run_id, source, retrieved_at, norad_cat_id,
                         object_name, object_id, epoch, raw_json, record_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (*row, record_hash),
                )
            connection.execute("DROP TABLE gp_records")
            connection.execute("ALTER TABLE gp_records_new RENAME TO gp_records")
            connection.execute(
                """CREATE INDEX idx_gp_norad_epoch
                   ON gp_records(norad_cat_id, epoch DESC)"""
            )
            connection.execute(
                """CREATE INDEX idx_gp_retrieved_at
                   ON gp_records(retrieved_at DESC)"""
            )
            connection.execute("PRAGMA user_version = 2")
        return True
    finally:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.close()


def compact_database(
    database_path: str | Path,
    *,
    latest_only: bool = False,
    keep_history_days: int | None = None,
) -> tuple[int, int, bool]:
    """Migrate, optionally prune history, and reclaim SQLite pages."""
    if latest_only and keep_history_days is not None:
        raise ValueError("choose either latest_only or keep_history_days")
    if keep_history_days is not None and keep_history_days < 1:
        raise ValueError("keep_history_days must be at least 1")

    migrated = migrate_database(database_path)
    connection = open_database(database_path)
    try:
        before = connection.execute("SELECT COUNT(*) FROM gp_records").fetchone()[0]
        if latest_only:
            connection.execute(
                """DELETE FROM gp_records
                   WHERE id IN (
                       SELECT id FROM (
                           SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY source, norad_cat_id
                                   ORDER BY epoch DESC, retrieved_at DESC, id DESC
                               ) AS row_number
                           FROM gp_records
                       )
                       WHERE row_number > 1
                   )"""
            )
        elif keep_history_days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=keep_history_days)
            connection.execute(
                "DELETE FROM gp_records WHERE retrieved_at < ?",
                (cutoff.isoformat(),),
            )
        connection.commit()
        after = connection.execute("SELECT COUNT(*) FROM gp_records").fetchone()[0]
    finally:
        connection.close()

    vacuum = sqlite3.connect(database_path)
    try:
        vacuum.execute("VACUUM")
    finally:
        vacuum.close()
    return before, after, migrated


def latest_records(database_path: str | Path, norad_cat_id: str | None = None):
    connection = open_database(database_path)
    try:
        if norad_cat_id:
            query = """SELECT norad_cat_id, object_name, object_id, epoch,
                retrieved_at, source, raw_json FROM gp_records
                WHERE norad_cat_id = ? ORDER BY epoch DESC, retrieved_at DESC"""
            rows = connection.execute(query, (str(norad_cat_id),)).fetchall()
        else:
            query = """SELECT r.norad_cat_id, r.object_name, r.object_id,
                r.epoch, r.retrieved_at, r.source, r.raw_json
                FROM gp_records r WHERE r.id = (
                    SELECT r2.id FROM gp_records r2
                    WHERE r2.norad_cat_id = r.norad_cat_id
                    ORDER BY r2.epoch DESC, r2.retrieved_at DESC LIMIT 1
                ) ORDER BY r.norad_cat_id"""
            rows = connection.execute(query).fetchall()
        return rows
    finally:
        connection.close()
