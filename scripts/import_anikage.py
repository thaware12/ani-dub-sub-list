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
            "User-Agent": "ani-dub-sub-list/1.0",
            "Accept": "application/json",
        },
    )

    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except Exception as exc:
            if attempt ==
