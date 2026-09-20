from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
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
    UNIQUE(source, norad_cat_id, epoch, raw_json)
);
CREATE INDEX IF NOT EXISTS idx_gp_norad_epoch
    ON gp_records(norad_cat_id, epoch DESC);
CREATE INDEX IF NOT EXISTS idx_gp_retrieved_at
    ON gp_records(retrieved_at DESC);
"""


def _value(record: dict, *names: str):
    for name in names:
        if record.get(name) is not None:
            return record[name]
    return None


def open_database(path: str | Path) -> sqlite3.Connection:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
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
                     object_id, epoch, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id, source, retrieved, str(norad),
                        _value(record, "OBJECT_NAME", "object_name"),
                        _value(record, "OBJECT_ID", "object_id"),
                        _value(record, "EPOCH", "epoch"),
                        json.dumps(record, ensure_ascii=False, sort_keys=True),
                    ),
                )
        return int(run_id), len(records)
    finally:
        connection.close()


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