from __future__ import annotations

import argparse
import json

from .config import ConfigError, load_config
from .database import latest_records
from .spacetrack import SpaceTrackClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--database", help="SQLite database path for query")
    parser.add_argument("--norad", help="NORAD catalog ID for query")
    parser.add_argument("command", choices=["validate", "fetch", "query"])
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
