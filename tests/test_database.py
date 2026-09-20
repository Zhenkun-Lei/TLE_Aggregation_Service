import json
import tempfile
import unittest
from pathlib import Path

from tle_aggregation.database import ingest_gp_payload, latest_records


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