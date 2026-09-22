from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request
from urllib.request import HTTPCookieProcessor
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from http.cookiejar import CookieJar
from zoneinfo import ZoneInfo

from .config import AppConfig, credentials
from .database import compact_database, ingest_gp_payload


class SpaceTrackError(RuntimeError):
    pass


class SpaceTrackClient:
    """One-session client with no automatic retry on authentication or block errors."""

    def __init__(self, config: AppConfig, opener=None, sleep=time.sleep):
        self.config = config
        self.opener = opener or request.build_opener(HTTPCookieProcessor(CookieJar()))
        self.sleep = sleep

    def _post(self, path: str, fields: dict[str, str]) -> bytes:
        body = urlencode(fields).encode("utf-8")
        req = request.Request(
            self.config.spacetrack.base_url + path,
            data=body,
            headers={"User-Agent": self.config.user_agent},
            method="POST",
        )
        try:
            with self.opener.open(req, timeout=self.config.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code in {401, 403, 404}:
                raise SpaceTrackError(f"Space-Track returned non-retryable HTTP {exc.code}") from exc
            raise SpaceTrackError(f"Space-Track login failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise SpaceTrackError(f"Space-Track network error: {exc.reason}") from exc

    def login(self) -> None:
        username, password = credentials(self.config)
        self._post("/ajaxauth/login", {"identity": username, "password": password})

    def fetch_gp(self) -> bytes:
        url = self.config.spacetrack.base_url + self.config.spacetrack.query
        req = request.Request(url, headers={"User-Agent": self.config.user_agent})
        try:
            with self.opener.open(req, timeout=self.config.timeout_seconds) as response:
                payload = response.read()
        except HTTPError as exc:
            if exc.code in {401, 403, 404}:
                raise SpaceTrackError(f"Space-Track returned non-retryable HTTP {exc.code}") from exc
            raise SpaceTrackError(f"Space-Track GP request failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise SpaceTrackError(f"Space-Track network error: {exc.reason}") from exc

        if not payload.strip():
            raise SpaceTrackError("Space-Track returned an empty response")
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise SpaceTrackError("Space-Track returned non-JSON content") from exc
        if not isinstance(decoded, list):
            raise SpaceTrackError("Space-Track GP response is not a JSON array")
        return payload

    def fetch_and_archive(self, now: datetime | None = None) -> Path:
        self.login()
        payload = self.fetch_gp()
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now_utc = now.astimezone(timezone.utc)
        local_now = now_utc.astimezone(ZoneInfo(self.config.timezone))
        target_dir = self.config.archive_root / "raw" / "spacetrack" / local_now.strftime("%Y-%m-%d")
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"gp-{local_now.strftime('%H%M%S')}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
        ingest_gp_payload(
            self.config.database_path,
            payload,
            source="spacetrack",
            payload_path=str(target),
            retrieved_at=now_utc.isoformat(),
        )
        # The production database is a current-state cache. Full payloads remain
        # available in the dated archive, while SQLite keeps one row per object.
        compact_database(self.config.database_path, latest_only=True)
        return target
