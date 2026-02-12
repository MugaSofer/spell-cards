#!/usr/bin/env python3
"""
5etools Spell Converter
Downloads spell data from the 5etools GitHub repository and converts
it to the format used by the Spell Card Generator.

5etools has the most complete D&D 5e spell database, covering every
official WotC sourcebook including the 2024 PHB (XPHB).

Usage:
    cd scraper
    pip install -r requirements.txt
    python convert_5etools.py                        # All sources
    python convert_5etools.py --sources PHB XGE TCE  # Specific books
    python convert_5etools.py --sources XPHB         # 2024 PHB only
    python convert_5etools.py --list-sources         # Show available sources

Output:
    spells_5etools.json  - Spell database
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests

REPO_BASE = "https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data/spells"
OUTPUT_FILE = Path(__file__).parent / "spells_5etools.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}

SCHOOL_MAP = {
    "A": "Abjuration",
    "C": "Conjuration",
    "D": "Divination",
    "E": "Enchantment",
    "I": "Illusion",
    "N": "Necromancy",
    "T": "Transmutation",
    "V": "Evocation",
}

SPELL_CLASSES = [
    "Artificer", "Bard", "Cleric", "Druid", "Paladin",
    "Ranger", "Sorcerer", "Warlock", "Wizard"
]


def fetch_json(url: str) -> dict:
    """Fetch and parse JSON from a URL."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def clean_tags(text: str) -> str:
    """Remove 5etools {@tag ...} markup, keeping the display text."""
    # {@tag text|extra|extra} → text
    # {@tag text} → text
    # Some tags: damage, dice, spell, condition, creature, item, action,
    #            skill, sense, status, dc, d20, chance, book, note, filter, scaledamage
    def replace_tag(m):
        content = m.group(1)
        # Split on | and take first part (display text)
        parts = content.split("|")
        # For scaledamage, the first part is the base damage
        return parts[0]

    text = re.sub(r"\{@\w+ ([^}]+)\}", replace_tag, text)
    return text


def convert_time(time_data: list) -> str:
    """Convert 5etools time format to readable string."""
    if not time_data:
        return ""
    parts = []
    for t in time_data:
        num = t.get("number", 1)
        unit = t.get("unit", "")
        condition = t.get("condition", "")

        if unit == "action":
            s = f"{num} action" if num == 1 else f"{num} actions"
        elif unit == "bonus":
            s = "1 bonus action"
        elif unit == "reaction":
            s = "1 reaction"
            if condition:
                s += f", {clean_tags(condition)}"
        elif unit == "minute":
            s = f"{num} minute" if num == 1 else f"{num} minutes"
        elif unit == "hour":
            s = f"{num} hour" if num == 1 else f"{num} hours"
        else:
            s = f"{num} {unit}"
        parts.append(s)

    return " or ".join(parts)


def convert_range(range_data: dict) -> str:
    """Convert 5etools range format to readable string."""
    if not range_data:
        return ""

    rtype = range_data.get("type", "")
    dist = range_data.get("distance", {})
    dist_type = dist.get("type", "")
    amount = dist.get("amount", 0)

    if rtype == "special":
        return "Special"

    if dist_type == "self":
        return "Self"
    elif dist_type == "touch":
        return "Touch"
    elif dist_type == "sight":
        return "Sight"
    elif dist_type == "unlimited":
        return "Unlimited"
    elif dist_type == "feet":
        base = f"{amount} feet"
    elif dist_type == "miles":
        base = f"{amount} mile" if amount == 1 else f"{amount} miles"
    else:
        base = f"{amount} {dist_type}"

    # For area effects, append shape
    if rtype in ("line", "cone", "cube", "sphere", "hemisphere"):
        return f"Self ({base} {rtype})"

    return base


def convert_components(comp_data: dict) -> str:
    """Convert 5etools components format to readable string."""
    if not comp_data:
        return ""

    parts = []
    if comp_data.get("v"):
        parts.append("V")
    if comp_data.get("s"):
        parts.append("S")

    m = comp_data.get("m")
    if m:
        if isinstance(m, str):
            parts.append(f"M ({m})")
        elif isinstance(m, dict):
            parts.append(f"M ({m.get('text', '')})")

    return ", ".join(parts)


def convert_duration(dur_data: list) -> tuple[str, bool]:
    """Convert 5etools duration format. Returns (string, is_concentration)."""
    if not dur_data:
        return "", False

    d = dur_data[0]  # Take first duration entry
    dtype = d.get("type", "")
    concentration = d.get("concentration", False)

    if dtype == "instant":
        text = "Instantaneous"
    elif dtype == "permanent":
        ends = d.get("ends", [])
        if "dispel" in ends and "trigger" in ends:
            text = "Until dispelled or triggered"
        elif "dispel" in ends:
            text = "Until dispelled"
        else:
            text = "Permanent"
    elif dtype == "special":
        text = "Special"
    elif dtype == "timed":
        dur = d.get("duration", {})
        amount = dur.get("amount", 0)
        unit = dur.get("type", "")
        if unit == "round":
            text = f"{amount} round" if amount == 1 else f"{amount} rounds"
        elif unit == "minute":
            text = f"{amount} minute" if amount == 1 else f"{amount} minutes"
        elif unit == "hour":
            text = f"{amount} hour" if amount == 1 else f"{amount} hours"
        elif unit == "day":
            text = f"{amount} day" if amount == 1 else f"{amount} days"
        else:
            text = f"{amount} {unit}"

        if concentration:
            text = f"Concentration, up to {text}"
    else:
        text = dtype

    return text, concentration


def convert_entries(entries: list) -> str:
    """Convert 5etools entries to HTML description."""
    parts = []
    for entry in entries:
        if isinstance(entry, str):
            parts.append(f"<p>{clean_tags(entry)}</p>")
        elif isinstance(entry, dict):
            etype = entry.get("type", "")
            if etype == "entries":
                # Sub-entries with a name (like "At Higher Levels")
                inner = convert_entries(entry.get("entries", []))
                name = entry.get("name", "")
                if name:
                    parts.append(f"<p><b>{clean_tags(name)}.</b> {inner.replace('<p>', '').replace('</p>', '')}</p>")
                else:
                    parts.append(inner)
            elif etype == "list":
                items = entry.get("items", [])
                li_parts = []
                for item in items:
                    if isinstance(item, str):
                        li_parts.append(f"<li>{clean_tags(item)}</li>")
                    elif isinstance(item, dict):
                        text = item.get("entry", item.get("entries", [""])[0] if isinstance(item.get("entries"), list) else "")
                        name = item.get("name", "")
                        if isinstance(text, str):
                            text = clean_tags(text)
                        if name:
                            li_parts.append(f"<li><b>{clean_tags(name)}.</b> {text}</li>")
                        else:
                            li_parts.append(f"<li>{text}</li>")
                parts.append(f"<ul>{''.join(li_parts)}</ul>")
            elif etype == "table":
                # Simple table rendering
                rows = entry.get("rows", [])
                caption = entry.get("caption", "")
                headers_list = entry.get("colLabels", [])
                table_html = "<table>"
                if caption:
                    table_html += f"<caption>{clean_tags(caption)}</caption>"
                if headers_list:
                    table_html += "<tr>" + "".join(f"<th>{clean_tags(h)}</th>" for h in headers_list) + "</tr>"
                for row in rows:
                    cells = row if isinstance(row, list) else [row]
                    table_html += "<tr>" + "".join(f"<td>{clean_tags(str(c))}</td>" for c in cells) + "</tr>"
                table_html += "</table>"
                parts.append(table_html)
            elif etype == "quote":
                text = " ".join(entry.get("entries", []))
                parts.append(f"<p><i>{clean_tags(text)}</i></p>")
    return "\n".join(parts)


def convert_spell(raw: dict, class_map: dict) -> dict:
    """Convert a 5etools spell to our format."""
    name = raw["name"]
    source = raw.get("source", "")

    # School
    school = SCHOOL_MAP.get(raw.get("school", ""), "Unknown")

    # Time
    casting_time = convert_time(raw.get("time", []))

    # Range
    range_str = convert_range(raw.get("range", {}))

    # Components
    components = convert_components(raw.get("components", {}))

    # Duration
    duration, concentration = convert_duration(raw.get("duration", []))

    # Ritual
    ritual = raw.get("meta", {}).get("ritual", False)

    # Description
    description = convert_entries(raw.get("entries", []))

    # At Higher Levels
    at_higher_levels = ""
    for ahl in raw.get("entriesHigherLevel", []):
        inner_entries = ahl.get("entries", [])
        at_higher_levels = convert_entries(inner_entries)
        # Strip wrapping <p> tags for consistency
        at_higher_levels = re.sub(r"^<p>|</p>$", "", at_higher_levels.strip())
        break  # Take first one

    # Classes from the class map — check both "class" and "classVariant" keys
    classes = []
    spell_data = class_map.get(source, {}).get(name, {})
    spell_classes = spell_data.get("class", []) + spell_data.get("classVariant", [])
    seen = set()
    for cls in spell_classes:
        cls_name = cls.get("name", "")
        if cls_name in SPELL_CLASSES and cls_name not in seen:
            classes.append(cls_name)
            seen.add(cls_name)

    result = {
        "name": name,
        "source": source,
        "level": raw.get("level", 0),
        "school": school,
        "ritual": ritual,
        "casting_time": casting_time,
        "range": range_str,
        "components": components,
        "duration": duration,
        "concentration": concentration,
        "description": description,
        "at_higher_levels": at_higher_levels,
        "classes": classes,
    }

    # SRD flags (used by generate_srd_json.py)
    if raw.get("srd"):
        result["srd"] = True
    if raw.get("srd52"):
        result["srd52"] = True

    return result


def main():
    parser = argparse.ArgumentParser(description="Convert 5etools spell data")
    parser.add_argument("--sources", nargs="+", default=None,
                        help="Source books to include (e.g. PHB XGE TCE XPHB)")
    parser.add_argument("--list-sources", action="store_true",
                        help="List available source books and exit")
    args = parser.parse_args()

    print("=" * 50)
    print("5etools Spell Converter")
    print("=" * 50)

    # Fetch the index
    print("Fetching spell index...")
    index = fetch_json(f"{REPO_BASE}/index.json")

    if args.list_sources:
        print(f"\nAvailable sources ({len(index)}):")
        for code, filename in sorted(index.items()):
            print(f"  {code:15s} -> {filename}")
        return

    # Filter sources
    source_codes = args.sources if args.sources else list(index.keys())
    print(f"Sources: {', '.join(source_codes)}")

    # Fetch class mapping
    print("Fetching class mapping...")
    class_map = fetch_json(f"{REPO_BASE}/sources.json")

    # Fetch and convert spells
    all_spells = []
    for code in source_codes:
        filename = index.get(code)
        if not filename:
            print(f"  WARNING: Unknown source '{code}', skipping")
            continue

        print(f"  Fetching {code} ({filename})...")
        data = fetch_json(f"{REPO_BASE}/{filename}")
        raw_spells = data.get("spell", [])

        for raw in raw_spells:
            spell = convert_spell(raw, class_map)
            all_spells.append(spell)

        print(f"    {len(raw_spells)} spells")

    # Sort by level, then name
    all_spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))

    # Save
    output = OUTPUT_FILE
    if args.sources and len(args.sources) == 1:
        output = OUTPUT_FILE.parent / f"spells_5etools_{args.sources[0].lower()}.json"

    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_spells, f, indent=2, ensure_ascii=False)

    print("=" * 50)
    print(f"Saved {len(all_spells)} spells to {output}")
    print("=" * 50)

    # Summary
    by_level = {}
    for spell in all_spells:
        level = spell.get("level", 0)
        by_level[level] = by_level.get(level, 0) + 1

    print("\nSpells by level:")
    for level in sorted(by_level.keys()):
        label = "Cantrips" if level == 0 else f"Level {level}"
        print(f"  {label}: {by_level[level]}")

    by_source = {}
    for spell in all_spells:
        src = spell.get("source", "?")
        by_source[src] = by_source.get(src, 0) + 1

    print("\nSpells by source:")
    for src in sorted(by_source, key=lambda s: -by_source[s]):
        print(f"  {src}: {by_source[src]}")

    # Issues
    issues = []
    for spell in all_spells:
        if not spell.get("classes"):
            issues.append(f"  {spell['name']} ({spell['source']}): missing classes")

    if issues:
        print(f"\nSpells with issues ({len(issues)}):")
        for issue in issues[:20]:
            print(issue)
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")


if __name__ == "__main__":
    main()
