"""Sample Roblox CCU (players online now) for a set of games.

Appends one row per game per run to ccu_log.csv (long format).
A game that fails to fetch gets NO row (a gap), never a fake zero.
Exits with status 1 if any game failed, so the Actions run shows red.
"""
import csv
import datetime as dt
import os
import sys
import time

import requests

GAMES = {
    "Kizuna": 79285429406839,
    "Gakuran": 128736949265057,
    "Ishin": 95132192110941,
}
CSV_PATH = "ccu_log.csv"
FIELDS = ["timestamp_utc", "game", "playing", "visits", "favorites"]

SESSION = requests.Session()


def get_json(url, attempts=4):
    """GET with retries and backoff. Returns parsed JSON or None."""
    delay = 2
    for i in range(attempts):
        try:
            r = SESSION.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
            print(f"HTTP {r.status_code} from {url} (attempt {i + 1})", file=sys.stderr)
        except (requests.RequestException, ValueError) as e:
            print(f"{type(e).__name__}: {e} (attempt {i + 1})", file=sys.stderr)
        if i < attempts - 1:
            time.sleep(delay)
            delay *= 2
    return None


def resolve_universes():
    """place id -> universe id, per game. Games that fail are left out."""
    out = {}
    for name, place_id in GAMES.items():
        data = get_json(f"https://apis.roblox.com/universes/v1/places/{place_id}/universe")
        uid = data.get("universeId") if data else None
        if uid:
            out[name] = uid
        else:
            print(f"Could not resolve universe for {name}", file=sys.stderr)
    return out


def fetch_stats(universes):
    if not universes:
        return {}
    ids = ",".join(str(u) for u in universes.values())
    data = get_json(f"https://games.roblox.com/v1/games?universeIds={ids}")
    if not data:
        return {}
    by_id = {g.get("id"): g for g in data.get("data", [])}
    stats = {}
    for name, uid in universes.items():
        g = by_id.get(uid)
        if g is None or not isinstance(g.get("playing"), int):
            print(f"No usable stats returned for {name}", file=sys.stderr)
            continue
        stats[name] = {
            "playing": g["playing"],
            "visits": g.get("visits"),
            "favorites": g.get("favoritedCount"),
        }
    return stats


def append_rows(rows):
    new_file = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        if new_file:
            w.writeheader()
        w.writerows(rows)


def main():
    ts = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    stats = fetch_stats(resolve_universes())
    rows = [
        {"timestamp_utc": ts, "game": name, **s}
        for name, s in stats.items()
    ]
    if rows:
        append_rows(rows)

    missing = [g for g in GAMES if g not in stats]
    if missing:
        print(f"FAILED to fetch: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
