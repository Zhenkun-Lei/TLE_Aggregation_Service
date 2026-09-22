import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tle_aggregation.database import (
    compact_database,
    ingest_gp_payload,
    latest_records,
    migrate_database,
)


class DatabaseTests(unittest.TestCase):
    def test_ingest_preserves_history_and_queries_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tle.db"
            first = json.dumps([{
                "NORAD_CAT_ID": 25544,
                "OBJECT_NAME": "ISS",
                "EPOCH": "2026-09-19T00:00:00",
            }]).encode()
            second = json.dumps([{
                "NORAD_CAT_ID": 25544,
                "OBJECT_NAME": "ISS",
                "EPOCH": "2026-09-20T00:00:00",
            }]).encode()
            ingest_gp_payload(path, first, "spacetrack", "first.json")
            ingest_gp_payload(path, second, "spacetrack", "second.json")
            self.assertEqual(len(latest_records(path, "25544")), 2)
            self.assertEqual(latest_records(path)[0][3], "2026-09-20T00:00:00")

    def test_compact_keeps_only_latest_record_per_satellite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tle.db"
            first = json.dumps([{
                "NORAD_CAT_ID": 25544,
                "OBJECT_NAME": "ISS",
                "EPOCH": "2026-09-19T00:00:00",
            }]).encode()
            second = json.dumps([{
                "NORAD_CAT_ID": 25544,
                "OBJECT_NAME": "ISS",
                "EPOCH": "2026-09-20T00:00:00",
            }]).encode()
            ingest_gp_payload(path, first, "spacetrack", "first.json")
            ingest_gp_payload(path, second, "spacetrack", "second.json")

            before, after, migrated = compact_database(path, latest_only=True)

            self.assertEqual((before, after, migrated), (2, 1, False))
            self.assertEqual(len(latest_records(path, "25544")), 1)

    def test_legacy_database_migrates_to_hash_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tle.db"
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    payload_path TEXT NOT NULL
                );
                CREATE TABLE gp_records (
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
            """)
            connection.execute(
                "INSERT INTO runs(source, retrieved_at, record_count, payload_path) VALUES (?, ?, ?, ?)",
                ("spacetrack", "2026-09-20T00:00:00+00:00", 1, "first.json"),
            )
            raw = json.dumps({"NORAD_CAT_ID": 25544, "EPOCH": "2026-09-20T00:00:00"})
            connection.execute(
                """INSERT INTO gp_records
                   (run_id, source, retrieved_at, norad_cat_id, epoch, raw_json)
                   VALUES (1, 'spacetrack', '2026-09-20T00:00:00+00:00', '25544',
                           '2026-09-20T00:00:00', ?)""",
                (raw,),
            )
            connection.commit()
            connection.close()

            self.assertTrue(migrate_database(path))
            self.assertFalse(migrate_database(path))
            self.assertEqual(len(latest_records(path, "25544")), 1)
