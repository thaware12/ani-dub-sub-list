from urllib.error import HTTPError
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


    for attempt in range(10):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)

        except HTTPError as exc:
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")

                if retry_after and retry_after.isdigit():
                    wait = int(retry_after) + 2
                else:
                    wait = 65

                print(f"Rate limited by AniKage. Waiting {wait}s...")
                time.sleep(wait)
                continue

            raise

        except Exception as exc:
            if attempt == 9:
                raise

            wait = min(2 ** attempt, 30)

            print(f"Request failed: {exc}")
            print(f"Retrying in {wait}s...")
            time.sleep(wait)

    raise RuntimeError("Failed to fetch AniKage")

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
            print(f"AniKage reports {expected_total} total anime.")

        items = payload.get("data", [])

        for anime in items:
            anilist_id = anime.get("anilistId")

            if not isinstance(anilist_id, int) or anilist_id <= 0:
                continue

            mal_id = anime.get("malId")
            sub_count = anime.get("subCount")
            dub_count = anime.get("dubCount")
            media_format = anime.get("format")

            record = {
                "mal_id": mal_id if isinstance(mal_id, int) else None,
                "format": media_format,
                "sub": sub_count if isinstance(sub_count, int) else 0,
                "dub": dub_count if isinstance(dub_count, int) else 0,
            }

            key = str(anilist_id)

            if key in records:
                old = records[key]

                record["sub"] = max(old["sub"], record["sub"])
                record["dub"] = max(old["dub"], record["dub"])

                if record["mal_id"] is None:
                    record["mal_id"] = old["mal_id"]

                if not record["format"]:
                    record["format"] = old["format"]

            records[key] = record

        print(
            f"Page {page}: {len(items)} entries | "
            f"{len(records)} unique AniList IDs"
        )

        if not payload.get("hasNext", False):
            break

        page += 1
        time.sleep(1.2)

    
    ordered = {
        key: records[key]
        for key in sorted(records, key=lambda value: int(value))
    }

    OUTPUT.write_text(
        json.dumps(
            ordered,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    metadata = {
        "source": "AniKage",
        "source_url": API,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reported_total": expected_total,
        "stored_records": len(ordered),
        "fields": {
            "key": "AniList ID",
            "mal_id": "MyAnimeList ID",
            "format": "Anime format",
            "sub": "Known subtitled episode count",
            "dub": "Known dubbed episode count",
        },
    }

    META_OUTPUT.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("Finished.")
    print(f"Stored records: {len(ordered)}")
    print(f"Database: {OUTPUT}")
    print(f"Metadata: {META_OUTPUT}")


if __name__ == "__main__":
    main()
