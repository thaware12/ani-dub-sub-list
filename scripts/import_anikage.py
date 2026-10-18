import json
import time
from pathlib import Path

import requests

API = "https://anikage.cc/api/media/anime/browse"

OUTPUT = Path("data/progress.json")


def fetch_page(page: int, limit: int = 100):
    response = requests.get(
        API,
        params={
            "page": page,
            "limit": limit,
            "sort": "popularity",
            "adult": "true",
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    progress = {}

    page = 1

    while True:
        print(f"Fetching page {page}...")

        result = fetch_page(page)

        items = result.get("data", [])

        for anime in items:
            anilist_id = anime.get("anilistId")

            if not anilist_id:
                continue

            progress[str(anilist_id)] = {
                "anilist_id": anilist_id,
                "
