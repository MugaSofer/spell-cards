#!/usr/bin/env python3
"""
Open5e Spell Fetcher
Downloads spell data from the Open5e REST API (api.open5e.com).

Includes SRD spells plus third-party OGL content (Kobold Press, etc.).
Does NOT include non-SRD WotC spells (PHB-only, XGE, TCE, etc.) — use
the Wikidot scraper for those.

Usage:
    cd scraper
    pip install -r requirements.txt
    python scrape_open5e.py                    # Fetch all 1400+ spells
    python scrape_open5e.py --source wotc-srd  # SRD spells only
    python scrape_open5e.py --source dmag      # Deep Magic only
    python scrape_open5e.py --list-sources     # Show available sources

Output:
    spells_open5e.json  - Spell database
"""

import argparse
import json
import sys
from pathlib import Path

import requests

API_BASE = "https://api.open5e.com/v1/spells/"
OUTPUT_FILE = Path(__file__).parent / "spells_open5e.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SPELL_CLASSES = [
    "Artificer", "Bard", "Cleric", "Druid", "Paladin",
    "Ranger", "Sorcerer", "Warlock", "Wizard"
]


def list_sources():
    """List available spell sources with counts."""
    print("Fetching source list...")
    # Get all spells in one pass to count by source
    sources = {}
    url = f"{API_BASE}?limit=500&format=json"
    while url:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for sp in data["results"]:
            key = sp["document__slug"]
            if key not in sources:
                sources[key] = {"title": sp["document__title"], "count": 0}
            sources[key]["count"] += 1
        url = data.get("next")

    total = sum(s["count"] for s in sources.values())
    print(f"\nAvailable sources ({total} total spells):\n")
    for slug in sorted(sources):
        s = sources[slug]
        print(f"  {slug:20s} {s['title']:40s} ({s['count']} spells)")


def fetch_all_spells(source: str | None = None) -> list[dict]:
    """Fetch spells from the Open5e API."""
    params = "limit=500&format=json"
    if source:
        params += f"&document__slug={source}"

    url = f"{API_BASE}?{params}"
    raw_spells = []

    while url:
        print(f"  Fetching page ({len(raw_spells)} so far)...")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        raw_spells.extend(data["results"])
        url = data.get("next")

    print(f"  Fetched {len(raw_spells)} spells from API")
    return raw_spells


def convert_spell(raw: dict) -> dict:
    """Convert an Open5e API spell to our format."""
    # Parse classes from dnd_class string
    classes = []
    dnd_class = raw.get("dnd_class", "")
    for cls in SPELL_CLASSES:
        if cls.lower() in dnd_class.lower():
            classes.append(cls)

    # Build components string including material
    components = raw.get("components", "")
    material = raw.get("material", "")
    if material and "M" in components:
        components = components.replace("M", f"M ({material.rstrip('.')})")

    # Map source
    source_slug = raw.get("document__slug", "")
    source_map = {
        "wotc-srd": "SRD",
        "a5e": "A5E",
        "dmag": "DM",
        "dmag-e": "DM-E",
        "kp": "KP",
        "toh": "ToH",
        "warlock": "WA",
        "o5e": "O5E",
    }
    source = source_map.get(source_slug, source_slug.upper()[:5])

    # Description — open5e uses plain text, wrap in <p> tags
    desc = raw.get("desc", "")
    if desc and not desc.startswith("<"):
        desc = "\n".join(f"<p>{para}</p>" for para in desc.split("\n") if para.strip())

    higher = raw.get("higher_level", "")

    # Subclass spell lists (e.g. "Cleric: Knowledge", "Warlock: Fiend")
    subclasses = []
    archetype = raw.get("archetype", "")
    if archetype:
        for part in archetype.split(","):
            part = part.strip()
            # Fix entries missing the class prefix (e.g. "Grassland" -> "Druid: Grassland")
            if ":" not in part:
                circles = raw.get("circles", "")
                if circles and part.lower() in circles.lower():
                    part = f"Druid: {part}"
                else:
                    continue
            subclasses.append(part)

    result = {
        "name": raw["name"],
        "source": source,
        "level": raw.get("level_int", raw.get("spell_level", 0)),
        "school": raw.get("school", "Unknown"),
        "ritual": raw.get("can_be_cast_as_ritual", False),
        "casting_time": raw.get("casting_time", ""),
        "range": raw.get("range", ""),
        "components": components,
        "duration": raw.get("duration", ""),
        "concentration": raw.get("requires_concentration", False),
        "description": desc,
        "at_higher_levels": higher,
        "classes": classes,
    }

    if subclasses:
        result["subclasses"] = subclasses

    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch D&D 5e spells from Open5e API")
    parser.add_argument("--source", type=str, default=None,
                        help="Filter by source (e.g. wotc-srd, dmag, a5e)")
    parser.add_argument("--list-sources", action="store_true",
                        help="List available spell sources and exit")
    args = parser.parse_args()

    print("=" * 50)
    print("Open5e Spell Fetcher")
    print("Source: https://api.open5e.com")
    print("=" * 50)

    if args.list_sources:
        list_sources()
        return

    if args.source:
        print(f"Filtering by source: {args.source}")

    raw_spells = fetch_all_spells(source=args.source)
    spells = []
    for raw in raw_spells:
        spell = convert_spell(raw)
        if spell:
            spells.append(spell)

    # Sort by level, then name
    spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))

    # Save to JSON
    output = OUTPUT_FILE
    if args.source:
        output = OUTPUT_FILE.parent / f"spells_open5e_{args.source}.json"

    with open(output, "w", encoding="utf-8") as f:
        json.dump(spells, f, indent=2, ensure_ascii=False)

    print("=" * 50)
    print(f"Saved {len(spells)} spells to {output}")
    print("=" * 50)

    # Summary
    by_level = {}
    for spell in spells:
        level = spell.get("level", 0)
        by_level[level] = by_level.get(level, 0) + 1

    print("\nSpells by level:")
    for level in sorted(by_level.keys()):
        label = "Cantrips" if level == 0 else f"Level {level}"
        print(f"  {label}: {by_level[level]}")

    # Check for issues
    issues = []
    for spell in spells:
        if not spell.get("casting_time"):
            issues.append(f"  {spell['name']}: missing casting_time")
        if not spell.get("classes"):
            issues.append(f"  {spell['name']}: missing classes")

    if issues:
        print(f"\nSpells with issues ({len(issues)}):")
        for issue in issues[:20]:
            print(issue)
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")


if __name__ == "__main__":
    main()
