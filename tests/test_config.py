import os
import tempfile
import unittest
from pathlib import Path

from tle_aggregation.config import ConfigError, credentials, load_config


class ConfigTests(unittest.TestCase):
    def test_example_config_loads_without_credentials(self):
        config = load_config(Path(__file__).parents[1] / "config.example.yaml")
        self.assertEqual(config.timezone, "Asia/Shanghai")
        with self.assertRaises(ConfigError):
            credentials(config)

    def test_http_source_is_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as file:
            file.write("""sources:\n  spacetrack:\n    base_url: http://example.invalid\n    username_env: U\n    password_env: P\n    query: /query\n""")
            path = file.name
        try:
            with self.assertRaises(ConfigError):
                load_config(path)
        finally:
            os.unlink(path)
