import json
import time
import urllib.request
from collections import defaultdict
from pathlib import Path


PROGRESS_PATH = Path("data/progress.json")

FEEDS = {
    "sub": (
        "https://raw.githubusercontent.com/"
        "RockinChaos/AniSchedule/master/raw/sub-episode-feed.json"
    ),
    "dub": (
        "https://raw.githubusercontent.com/"
        "RockinChaos/AniSchedule/master/raw/dub-episode-feed.json"
    ),
}


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ani-dub-sub-list/1.0",
            "Accept": "application/json",
        },
    )

    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)

        except Exception as exc:
            if attempt == 4:
                raise

            wait = min(2 ** attempt, 30)
            print(f"Request failed: {exc}")
            print(f"Retrying in {wait}s...")
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {url}")


def positive_int(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value > 0 else None

    if isinstance(value, str) and value.isdigit():
        number = int(value)
        return number if number > 0 else None

    return None


def episode_number(value):
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    if isinstance(value, float) and value.is_integer():
        number = int(value)
        return number if number >= 0 else None

    return None


def build_mal_index(records):
    index = {}

    for anilist_id, record in records.items():
        mal_id = positive_int(record.get("mal_id"))

        if mal_id is not None:
            index[mal_id] = anilist_id

    return index


def resolve_anime(entry, records, mal_index):
    anilist_id = positive_int(entry.get("id"))
    mal_id = positive_int(entry.get("idMal"))

    # AniList ID is our primary identity.
    if anilist_id is not None:
        key = str(anilist_id)

        # Cross-check against MAL when both mappings already exist.
        if mal_id is not None and mal_id in mal_index:
            existing_key = mal_index[mal_id]

            if existing_key != key:
                print(
                    "ID conflict: "
                    f"AniList {anilist_id}, MAL {mal_id}, "
                    f"stored AniList {existing_key}. Skipping."
                )
                return None

        return key

    # If AniSchedule has no AniList ID, use MAL only if we already know
    # which AniList record that MAL ID belongs to.
    if mal_id is not None:
        return mal_index.get(mal_id)

    return None


def candidate_count(episodes):
    if not episodes:
        return 0

    # Store AniSchedule's highest released episode number.
    # Do not count feed rows, because Episode 0 would make
    # the value one higher than the normal episode numbering.
    return max(episodes)


def merge_progress(old_value, episodes):
    if not episodes:
        return old_value

    latest = max(episodes)

    # Special correction for Episode 0.
    #
    # If AniSchedule explicitly contains the complete sequence
    # 0, 1, 2, ... latest, and the old AniKage count is exactly
    # one higher, AniKage probably counted Episode 0 as an
    # additional episode.
    #
    # Our value represents latest numbered episode, so 0..12 = 12.
    if 0 in episodes and old_value == latest + 1:
        complete_sequence = set(range(0, latest + 1))

        if complete_sequence.issubset(episodes):
            return latest

    return max(old_value, latest)


def main():
    if not PROGRESS_PATH.exists():
        raise RuntimeError(
            "data/progress.json does not exist. "
            "Run the AniKage snapshot importer first."
        )

    records = json.loads(
        PROGRESS_PATH.read_text(encoding="utf-8")
    )

    mal_index = build_mal_index(records)

    feed_episodes = {
        "sub": defaultdict(set),
        "dub": defaultdict(set),
    }

    feed_metadata = {}

    skipped = 0

    for language, url in FEEDS.items():
        print(f"Fetching AniSchedule {language.upper()} feed...")

        feed = fetch_json(url)

        print(
            f"{language.upper()} feed contains "
            f"{len(feed)} episode entries."
        )

        for entry in feed:
            key = resolve_anime(
                entry,
                records,
                mal_index,
            )

            if key is None:
                skipped += 1
                continue

            episode = episode_number(
                (entry.get("episode") or {}).get("aired")
            )

            if episode is None:
                continue

            feed_episodes[language][key].add(episode)

            if key not in feed_metadata:
                feed_metadata[key] = {
                    "mal_id": positive_int(entry.get("idMal")),
                    "format": entry.get("format"),
                }

    changed = 0
    new_records = 0
    sub_changes = 0
    dub_changes = 0

    all_keys = (
        set(feed_episodes["sub"])
        | set(feed_episodes["dub"])
    )

    for key in all_keys:
        metadata = feed_metadata.get(key, {})

        if key not in records:
            records[key] = {
                "mal_id": metadata.get("mal_id"),
                "format": metadata.get("format"),
                "sub": 0,
                "dub": 0,
            }

            new_records += 1

            mal_id = metadata.get("mal_id")
            if mal_id is not None:
                mal_index[mal_id] = key

        record = records[key]

        # Fill missing metadata, but do not overwrite existing mappings.
        if record.get("mal_id") is None:
            record["mal_id"] = metadata.get("mal_id")

        if not record.get("format"):
            record["format"] = metadata.get("format")

        old_sub = int(record.get("sub") or 0)
        old_dub = int(record.get("dub") or 0)

        schedule_sub = candidate_count(
            feed_episodes["sub"].get(key, set())
        )

        schedule_dub = candidate_count(
            feed_episodes["dub"].get(key, set())
        )

        # Critical safety rule:
        # AniSchedule is allowed to increase our historical snapshot,
        # NEVER decrease it.
      new_sub = merge_progress(
    old_sub,
    feed_episodes["sub"].get(key, set()),
)

new_dub = merge_progress(
    old_dub,
    feed_episodes["dub"].get(key, set()),
)

        record_changed = False

        if new_sub != old_sub:
            record["sub"] = new_sub
            sub_changes += 1
            record_changed = True

            print(
                f"AniList {key}: "
                f"SUB {old_sub} -> {new_sub}"
            )

        if new_dub != old_dub:
            record["dub"] = new_dub
            dub_changes += 1
            record_changed = True

            print(
                f"AniList {key}: "
                f"DUB {old_dub} -> {new_dub}"
            )

        if record_changed:
            changed += 1

    if changed == 0 and new_records == 0:
        print()
        print("No SUB/DUB progress changes.")
        print(f"Skipped unresolved/conflicting entries: {skipped}")
        return

    ordered = {
        key: records[key]
        for key in sorted(
            records,
            key=lambda value: int(value),
        )
    }

    PROGRESS_PATH.write_text(
        json.dumps(
            ordered,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    print()
    print("AniSchedule update complete.")
    print(f"Anime changed: {changed}")
    print(f"New anime added: {new_records}")
    print(f"SUB increases: {sub_changes}")
    print(f"DUB increases: {dub_changes}")
    print(f"Total records: {len(ordered)}")
    print(f"Skipped unresolved/conflicting entries: {skipped}")


if __name__ == "__main__":
    main()
