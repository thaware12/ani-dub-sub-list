import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API = "https://anikage.cc/api/media/anime/browse"

OUTPUT = Path("data/progress.json")
META_OUTPUT = Path("data/snapshot-meta.json")

LIMIT = 100


def fetch_page(page: int) -> dict:
    params = urllib.parse.urlencode(
        {
            "page": page,
            "limit": LIMIT,
            "sort": "popularity",
            "adult": "true",
        }
    )

    url = f"{API}?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "anime-language-progress/1.0",
            "Accept": "application/json",
        },
    )

    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except Exception as exc:
            if attempt == 4:
                raise

            wait = 2 ** attempt
            print(f"Request failed: {exc}")
            print(f"Retrying in {wait}s...")
            time.sleep(wait)

    raise RuntimeError("Failed to fetch AniKage")


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    records = {}

    page = 1
    expected_total = None

    while True:
        print(f"Fetching page {page}...")

        payload = fetch_page(page)

        if expected_total is None:
            expected_total = payload.get("total")
            print(f"AniKage reports {
