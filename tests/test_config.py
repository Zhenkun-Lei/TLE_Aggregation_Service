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

    def test_unknown_timezone_is_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as file:
            file.write("""timezone: Not/A_Timezone
sources:
  spacetrack:
    base_url: https://example.invalid
    username_env: U
    password_env: P
    query: /query
""")
            path = file.name
        try:
            with self.assertRaises(ConfigError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_min_interval_default_matches_template_and_stays_below_24h(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as file:
            file.write("""sources:
  spacetrack:
    base_url: https://example.invalid
    username_env: U
    password_env: P
    query: /query
""")
            path = file.name
        try:
            default_interval = load_config(path).min_interval_minutes
        finally:
            os.unlink(path)

        template = load_config(Path(__file__).parents[1] / "config.example.yaml")

        self.assertEqual(default_interval, 1200)
        self.assertEqual(template.min_interval_minutes, default_interval)
        # The systemd timer runs once every 24h, so the minimum interval must
        # stay lower or the randomized daily run can be skipped.
        self.assertLess(default_interval, 1440)
