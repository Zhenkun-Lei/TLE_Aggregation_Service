import json
import unittest
from types import SimpleNamespace

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
