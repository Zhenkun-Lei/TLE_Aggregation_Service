from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SourceConfig:
    base_url: str
    username_env: str
    password_env: str
    query: str


@dataclass(frozen=True)
class AppConfig:
    timezone: str
    archive_root: Path
    database_path: Path
    min_interval_minutes: int
    timeout_seconds: int
    user_agent: str
    spacetrack: SourceConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream) or {}

    source = raw.get("sources", {}).get("spacetrack", {})
    policy = raw.get("policy", {})
    storage = raw.get("storage", {})
    required = ["base_url", "username_env", "password_env", "query"]
    missing = [key for key in required if not source.get(key)]
    if missing:
        raise ConfigError(f"missing Space-Track settings: {', '.join(missing)}")

    base_url = str(source["base_url"]).rstrip("/")
    if urlparse(base_url).scheme != "https":
        raise ConfigError("Space-Track base_url must use HTTPS")
    # Duplicate-fetch guard. The default stays well below the 24h systemd timer
    # period so the randomized daily run is never rejected, and short enough
    # that an out-of-band manual catch-up does not block the next day's run.
    interval = int(policy.get("min_interval_minutes", 300))
    if interval < 60:
        raise ConfigError("min_interval_minutes must be at least 60")

    timezone_name = str(raw.get("timezone", "Asia/Shanghai"))
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(f"unknown timezone: {timezone_name}") from exc

    return AppConfig(
        timezone=timezone_name,
        archive_root=Path(storage.get("root", "./archive")),
        database_path=Path(storage.get("database", "./archive/tle.db")),
        min_interval_minutes=interval,
        timeout_seconds=int(policy.get("request_timeout_seconds", 60)),
        user_agent=str(policy.get("user_agent", "tle-aggregation-service/0.1")),
        spacetrack=SourceConfig(
            base_url=base_url,
            username_env=str(source["username_env"]),
            password_env=str(source["password_env"]),
            query=str(source["query"]),
        ),
    )


def credentials(config: AppConfig) -> tuple[str, str]:
    username = os.environ.get(config.spacetrack.username_env)
    password = os.environ.get(config.spacetrack.password_env)
    if not username or not password:
        raise ConfigError(
            "Space-Track credentials must be supplied through the configured environment variables"
        )
    return username, password
