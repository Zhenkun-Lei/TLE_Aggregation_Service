import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone

from tle_aggregation.spacetrack import SpaceTrackClient, SpaceTrackError


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


class FakeOpener:
    def __init__(self, responses):
        self.responses = iter(responses)

    def open(self, *_args, **_kwargs):
        return next(self.responses)


class ClientTests(unittest.TestCase):
    def test_invalid_json_is_rejected_without_retry(self):
        config = SimpleNamespace(
            spacetrack=SimpleNamespace(base_url="https://example.invalid", query="/gp"),
            timeout_seconds=1,
            user_agent="test",
        )
        client = SpaceTrackClient(config, opener=FakeOpener([FakeResponse(b"<html>blocked</html>")]))
        with self.assertRaises(SpaceTrackError):
            client.fetch_gp()

    def test_valid_json_array_is_accepted(self):
        config = SimpleNamespace(
            spacetrack=SimpleNamespace(base_url="https://example.invalid", query="/gp"),
            timeout_seconds=1,
            user_agent="test",
        )
        payload = json.dumps([{"NORAD_CAT_ID": "25544"}]).encode()
        client = SpaceTrackClient(config, opener=FakeOpener([FakeResponse(payload)]))
        self.assertEqual(client.fetch_gp(), payload)

    def test_archive_uses_configured_local_timezone(self):
        with tempfile.TemporaryDirectory() as directory:
            config = SimpleNamespace(
                spacetrack=SimpleNamespace(base_url="https://example.invalid", query="/gp"),
                timeout_seconds=1,
                user_agent="test",
                timezone="Asia/Shanghai",
                archive_root=Path(directory),
                database_path=Path(directory) / "tle.db",
            )
            client = SpaceTrackClient(config, opener=FakeOpener([]))
            client.login = lambda: None
            client.fetch_gp = lambda: json.dumps([{
                "NORAD_CAT_ID": "25544",
                "EPOCH": "2026-09-20T19:00:00",
            }]).encode()

            target = client.fetch_and_archive(
                datetime(2026, 9, 20, 19, 21, 27, tzinfo=timezone.utc)
            )

            self.assertEqual(target.parent.name, "2026-09-21")
            self.assertEqual(target.name, "gp-032127.json")

    def test_successive_archives_keep_sqlite_at_current_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = SimpleNamespace(
                spacetrack=SimpleNamespace(base_url="https://example.invalid", query="/gp"),
                timeout_seconds=1,
                user_agent="test",
                timezone="Asia/Shanghai",
                archive_root=Path(directory),
                database_path=Path(directory) / "tle.db",
            )
            payloads = iter([
                json.dumps([{
                    "NORAD_CAT_ID": "25544",
                    "EPOCH": "2026-09-20T19:00:00",
                }]).encode(),
                json.dumps([{
                    "NORAD_CAT_ID": "25544",
                    "EPOCH": "2026-09-21T19:00:00",
                }]).encode(),
            ])
            client = SpaceTrackClient(config, opener=FakeOpener([]))
            client.login = lambda: None
            client.fetch_gp = lambda: next(payloads)
            client.fetch_and_archive(datetime(2026, 9, 20, 19, 0, tzinfo=timezone.utc))
            client.fetch_and_archive(datetime(2026, 9, 21, 19, 0, tzinfo=timezone.utc))

            connection = sqlite3.connect(config.database_path)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM gp_records").fetchone()[0], 1)
            connection.close()
