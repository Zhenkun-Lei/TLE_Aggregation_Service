from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path

from .config import ConfigError, load_config
from .database import compact_database, last_run_at, latest_records
from .spacetrack import SpaceTrackClient


@contextmanager
def _database_lock(database_path: str | Path):
    lock_path = Path(f"{database_path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--database", help="SQLite database path for query")
    parser.add_argument("--norad", help="NORAD catalog ID for query")
    parser.add_argument("--force", action="store_true", help="ignore the fetch interval")
    parser.add_argument("--latest-only", action="store_true", help="keep only the newest record per satellite")
    parser.add_argument("--keep-history-days", type=int, help="keep records from this many recent days")
    parser.add_argument("command", choices=["validate", "fetch", "query", "compact"])
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.command == "validate":
            print("configuration valid; credentials are not checked")
            return 0
        if args.command == "query":
            database_path = args.database or str(config.database_path)
            for row in latest_records(database_path, args.norad):
                print(json.dumps({
                    "norad_cat_id": row[0], "object_name": row[1],
                    "object_id": row[2], "epoch": row[3],
                    "retrieved_at": row[4], "source": row[5],
                    "record": json.loads(row[6]),
                }, ensure_ascii=False))
            return 0
        if args.command == "compact":
            if args.latest_only and args.keep_history_days is not None:
                parser.error("choose either --latest-only or --keep-history-days")
            if not args.latest_only and args.keep_history_days is None:
                parser.error("compact requires --latest-only or --keep-history-days")
            with _database_lock(config.database_path):
                before, after, migrated = compact_database(
                    config.database_path,
                    latest_only=args.latest_only,
                    keep_history_days=args.keep_history_days,
                )
            print(f"compact complete; rows {before} -> {after}; migrated={migrated}")
            return 0

        with _database_lock(config.database_path):
            if not args.force:
                previous = last_run_at(config.database_path)
                if previous:
                    previous_dt = datetime.fromisoformat(previous).astimezone(timezone.utc)
                    elapsed_seconds = (datetime.now(timezone.utc) - previous_dt).total_seconds()
                    minimum_seconds = config.min_interval_minutes * 60
                    if elapsed_seconds < minimum_seconds:
                        remaining = int(minimum_seconds - max(0, elapsed_seconds))
                        print(
                            f"fetch skipped; last successful run was {previous}; "
                            f"minimum interval has {remaining}s remaining"
                        )
                        return 0
            target = SpaceTrackClient(config).fetch_and_archive()
            print(target)
            return 0
    except ConfigError as exc:
        parser.error(str(exc))
    except Exception as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
