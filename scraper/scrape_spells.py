#!/usr/bin/env python3
"""
D&D 5e Spell Scraper
Extracts spell data from Wikidot spell databases and saves to JSON.
Also saves raw HTML for debugging/reprocessing.

Usage:
    cd scraper
    pip install -r requirements.txt
    python scrape_spells.py                  # Scrape 2014 spells (dnd5e.wikidot.com)
    python scrape_spells.py --site 2024      # Scrape 2024 spells (dnd2024.wikidot.com)
    python scrape_spells.py --reparse        # Reparse from saved HTML (no network)

Output:
    spells.json / spells_2024.json  - Spell database
    raw_html/ / raw_html_2024/      - Cached HTML for each spell page
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SPELL_CLASSES = [
    "Artificer", "Bard", "Cleric", "Druid", "Paladin",
    "Ranger", "Sorcerer", "Warlock", "Wizard"
]

SCHOOLS = ["abjuration", "conjuration", "divination", "enchantment",
           "evocation", "illusion", "necromancy", "transmutation"]

SOURCE_MAP_2014 = {
    "player's handbook": "PHB",
    "xanathar's guide to everything": "XGE",
    "tasha's cauldron of everything": "TCE",
    "sword coast adventurer's guide": "SCAG",
    "explorer's guide to wildemount": "EGW",
    "fizban's treasury of dragons": "FTD",
    "strixhaven: a curriculum of chaos": "SCC",
    "acquisitions incorporated": "AI",
    "elemental evil player's companion": "EEPC",
}

SOURCE_MAP_2024 = {
    "player's handbook": "PHB24",
    "dungeon master's guide": "DMG24",
    "free rules": "Free24",
}

SITE_CONFIGS = {
    "2014": {
        "base_url": "http://dnd5e.wikidot.com",
        "spell_list_path": "/spells",
        "raw_html_dir": Path(__file__).parent / "raw_html",
        "output_file": Path(__file__).parent / "spells.json",
        "label": "D&D 5e (2014)",
        "default_source": "PHB",
        "source_map": SOURCE_MAP_2014,
    },
    "2024": {
        "base_url": "http://dnd2024.wikidot.com",
        "spell_list_path": "/spell:all",
        "raw_html_dir": Path(__file__).parent / "raw_html_2024",
        "output_file": Path(__file__).parent / "spells_2024.json",
        "label": "D&D 5e (2024)",
        "default_source": "PHB24",
        "source_map": SOURCE_MAP_2024,
    },
}

# Module-level state set by configure_site()
BASE_URL = ""
SPELL_LIST_URL = ""
RAW_HTML_DIR = Path()
OUTPUT_FILE = Path()
SITE = "2014"
DEFAULT_SOURCE = "PHB"
SOURCE_MAP = {}


def configure_site(site: str):
    """Set module-level variables based on the chosen site."""
    global BASE_URL, SPELL_LIST_URL, RAW_HTML_DIR, OUTPUT_FILE
    global SITE, DEFAULT_SOURCE, SOURCE_MAP
    config = SITE_CONFIGS[site]
    BASE_URL = config["base_url"]
    SPELL_LIST_URL = config["base_url"] + config["spell_list_path"]
    RAW_HTML_DIR = config["raw_html_dir"]
    OUTPUT_FILE = config["output_file"]
    SITE = site
    DEFAULT_SOURCE = config["default_source"]
    SOURCE_MAP = config["source_map"]


def get_soup(url: str) -> BeautifulSoup:
    """Fetch a URL and return BeautifulSoup object."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def get_all_spell_links() -> list[dict]:
    """Get list of all spell names and URLs from the main spell list."""
    print("Fetching spell list...")
    soup = get_soup(SPELL_LIST_URL)

    spells = []
    seen_slugs = set()
    content = soup.find("div", {"id": "page-content"})
    if not content:
        raise ValueError("Could not find page content")

    for table in content.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if cells:
                link = cells[0].find("a")
                if link and link.get("href", "").startswith("/spell:"):
                    spell_slug = link["href"].replace("/spell:", "")
                    # Deduplicate (2024 site has tabbed tables that might overlap)
                    if spell_slug in seen_slugs:
                        continue
                    seen_slugs.add(spell_slug)
                    spell_name = link.text.strip()
                    spells.append({
                        "name": spell_name,
                        "slug": spell_slug,
                        "url": BASE_URL + link["href"]
                    })

    print(f"Found {len(spells)} spells")
    return spells


def fetch_and_save_html(url: str, slug: str) -> str:
    """Fetch a spell page and save the raw HTML."""
    RAW_HTML_DIR.mkdir(exist_ok=True)
    html_path = RAW_HTML_DIR / f"{slug}.html"

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    html_path.write_text(resp.text, encoding="utf-8")
    return resp.text


def load_html(slug: str) -> str | None:
    """Load saved HTML for a spell."""
    html_path = RAW_HTML_DIR / f"{slug}.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return None


def parse_spell_html(html: str, name: str) -> dict | None:
    """Parse spell data from HTML content."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("div", {"id": "page-content"})
        if not content:
            return None

        spell = {"name": name}

        # Get all content elements (paragraphs and lists) for structured parsing
        paragraphs = content.find_all(["p", "ul", "ol"])

        # === Parse source (usually first paragraph) ===
        spell["source"] = DEFAULT_SOURCE
        for p in paragraphs[:2]:
            text = p.get_text(strip=True)
            if text.lower().startswith("source:"):
                source_text = text[7:].strip()
                for full_name, abbrev in SOURCE_MAP.items():
                    if full_name in source_text.lower():
                        spell["source"] = abbrev
                        break
                else:
                    spell["source"] = source_text.split()[0][:5] if source_text else DEFAULT_SOURCE
                break

        # === Parse spell level, school, and (for 2024) classes from <em> tag ===
        spell["level"] = 0
        spell["school"] = "Unknown"
        spell["ritual"] = False
        classes_from_level_line = []

        for p in paragraphs[:4]:
            em = p.find("em")
            if em:
                em_text = em.get_text(strip=True)
                text = em_text.lower()

                # Extract classes from parenthetical — 2024 format embeds classes
                # in the level/school line like "Level 3 Evocation (Sorcerer, Wizard)"
                class_match = re.search(r"\(([^)]+)\)", em_text)
                if class_match:
                    for cls_name in class_match.group(1).split(","):
                        cls_name = cls_name.strip()
                        if cls_name in SPELL_CLASSES:
                            classes_from_level_line.append(cls_name)

                # Check for cantrip
                if "cantrip" in text:
                    spell["level"] = 0
                    for school in SCHOOLS:
                        if school in text:
                            spell["school"] = school.capitalize()
                            break
                    spell["ritual"] = "(ritual)" in text
                    break

                # 2014 format: "3rd-level evocation"
                level_match = re.search(r"(\d+)(?:st|nd|rd|th)[- ]level", text)
                if level_match:
                    spell["level"] = int(level_match.group(1))
                    for school in SCHOOLS:
                        if school in text:
                            spell["school"] = school.capitalize()
                            break
                    spell["ritual"] = "(ritual)" in text
                    break

                # 2024 format: "Level 3 Evocation"
                level_match = re.search(r"level (\d+)", text)
                if level_match:
                    spell["level"] = int(level_match.group(1))
                    for school in SCHOOLS:
                        if school in text:
                            spell["school"] = school.capitalize()
                            break
                    spell["ritual"] = "(ritual)" in text
                    break

        # === Parse stat block ===
        # The stat block is in a <p> with <strong> labels and <br/> separators
        spell["casting_time"] = ""
        spell["range"] = ""
        spell["components"] = ""
        spell["duration"] = ""

        for p in paragraphs:
            strongs = p.find_all("strong")
            if not strongs:
                continue

            # Check if this paragraph has stat labels
            has_stats = any("casting time" in s.get_text(strip=True).lower() for s in strongs)
            if not has_stats:
                continue

            # Found the stat block paragraph - parse it
            for strong in strongs:
                label = strong.get_text(strip=True).lower().rstrip(":")

                # Get all text after this strong tag until next <br/> or <strong>
                next_text = ""
                for sibling in strong.next_siblings:
                    if isinstance(sibling, NavigableString):
                        next_text += str(sibling)
                    elif sibling.name in ["br", "strong", "b"]:
                        break
                    else:
                        # Inline elements like <a>, <em>, <span> — extract text
                        next_text += sibling.get_text()
                next_text = next_text.strip()

                if "casting time" in label:
                    spell["casting_time"] = next_text
                elif label == "range":
                    spell["range"] = next_text
                elif "component" in label:
                    spell["components"] = next_text
                elif "duration" in label:
                    spell["duration"] = next_text

            break  # Found and parsed stat block

        # Check for concentration in duration
        spell["concentration"] = "concentration" in spell["duration"].lower()

        # Check for ritual — 2014 puts "(ritual)" in level line (already handled above),
        # 2024 puts "or Ritual" in casting time
        if not spell["ritual"] and "ritual" in spell["casting_time"].lower():
            spell["ritual"] = True

        # === Parse description ===
        # Preserve HTML formatting (paragraphs, bold, etc.)
        description_parts = []
        at_higher_levels_html = ""
        found_stat_block = False
        found_spell_lists = False

        for p in paragraphs:
            text = p.get_text(strip=True)
            text_lower = text.lower()

            # Skip source line
            if text_lower.startswith("source:"):
                continue

            # Skip level/school line (detected by <em> tag containing level/school pattern)
            if p.find("em"):
                em_text = p.find("em").get_text(strip=True).lower()
                if "cantrip" in em_text or re.search(r"(\d+)(?:st|nd|rd|th)[- ]level|level \d+", em_text):
                    continue

            # Skip stat block paragraph
            if p.find("strong") and any(x in text_lower for x in ["casting time:", "range:", "duration:"]):
                found_stat_block = True
                continue

            # Stop at class list — 2014 format has "Spell Lists." section at bottom
            if "spell list" in text_lower and p.find("a"):
                # Extract classes from links
                spell["classes"] = []
                for link in p.find_all("a"):
                    link_text = link.get_text(strip=True)
                    if link_text in SPELL_CLASSES:
                        spell["classes"].append(link_text)
                found_spell_lists = True
                continue

            # Skip anything after spell lists
            if found_spell_lists:
                continue

            # Check for "At Higher Levels" (2014) or "Using a Higher-Level Spell Slot" (2024)
            if re.search(r"at higher levels\.?", text_lower) or re.search(r"using a higher[- ]level spell slot\.?", text_lower):
                inner_html = p.decode_contents()
                # Remove the bold/italic label — various HTML nesting orders
                inner_html = re.sub(r"<strong>\s*<em>\s*At Higher Levels\.?\s*</em>\s*</strong>", "", inner_html, flags=re.IGNORECASE)
                inner_html = re.sub(r"<em>\s*<strong>\s*At Higher Levels\.?\s*</strong>\s*</em>", "", inner_html, flags=re.IGNORECASE)
                inner_html = re.sub(r"<strong>\s*Using a Higher[- ]Level Spell Slot\.?\s*</strong>", "", inner_html, flags=re.IGNORECASE)
                at_higher_levels_html = inner_html.strip()
                continue

            # After stat block, collect description as HTML
            if found_stat_block:
                # Keep lists as-is, wrap paragraphs in <p> tags
                if p.name in ["ul", "ol"]:
                    description_parts.append(str(p))
                else:
                    inner_html = p.decode_contents()
                    description_parts.append(f"<p>{inner_html}</p>")

        spell["description"] = "\n".join(description_parts).strip()
        spell["at_higher_levels"] = at_higher_levels_html

        # Assign classes — prefer Spell Lists section, then level line, then page tags
        if not spell.get("classes"):
            if classes_from_level_line:
                spell["classes"] = classes_from_level_line
            else:
                spell["classes"] = []
                tags_div = soup.find("div", class_="page-tags")
                if tags_div:
                    for link in tags_div.find_all("a"):
                        tag = link.get_text(strip=True).capitalize()
                        if tag in SPELL_CLASSES:
                            spell["classes"].append(tag)

        return spell

    except Exception as e:
        print(f"  Error parsing {name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def scrape_all_spells(reparse_only: bool = False) -> list[dict]:
    """Scrape all spells from the wiki."""
    spell_links = get_all_spell_links()
    spells = []

    RAW_HTML_DIR.mkdir(exist_ok=True)

    for i, item in enumerate(spell_links):
        print(f"  [{i+1}/{len(spell_links)}] {item['name']}...")

        html = None
        if reparse_only:
            html = load_html(item["slug"])
            if not html:
                print(f"    No saved HTML, skipping")
                continue
        else:
            try:
                html = fetch_and_save_html(item["url"], item["slug"])
                time.sleep(0.1)  # Brief delay between requests
            except Exception as e:
                print(f"    Fetch error: {e}")
                # Try to use cached version
                html = load_html(item["slug"])
                if not html:
                    continue

        spell = parse_spell_html(html, item["name"])
        if spell:
            spells.append(spell)

    return spells


def main():
    parser = argparse.ArgumentParser(description="Scrape D&D 5e spells from Wikidot")
    parser.add_argument("--site", choices=["2014", "2024"], default="2014",
                        help="Which site to scrape: 2014 (dnd5e.wikidot.com) or 2024 (dnd2024.wikidot.com)")
    parser.add_argument("--reparse", action="store_true",
                        help="Reparse from saved HTML files (no network requests)")
    args = parser.parse_args()

    configure_site(args.site)

    label = SITE_CONFIGS[args.site]["label"]
    print("=" * 50)
    print(f"D&D Spell Scraper — {label}")
    print(f"Source: {BASE_URL}")
    print("=" * 50)

    if args.reparse:
        print("Reparsing from saved HTML files...")

    spells = scrape_all_spells(reparse_only=args.reparse)

    # Sort by level, then name
    spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(spells, f, indent=2, ensure_ascii=False)

    print("=" * 50)
    print(f"Saved {len(spells)} spells to {OUTPUT_FILE}")
    print(f"Raw HTML saved to {RAW_HTML_DIR}/")
    print("=" * 50)

    # Print summary
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
        for issue in issues[:20]:  # Show first 20
            print(issue)
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")


if __name__ == "__main__":
    main()
