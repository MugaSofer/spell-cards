# D&D 5e Spell Scrapers

Tools for downloading spell data from various sources, outputting JSON files compatible with the [Spell Card Generator](https://github.com/MugaSofer/spell-cards).

The website ships with SRD 5.1 spells only (319 spells, freely licensed). Use these scrapers to generate a complete dataset for personal use.

## Setup

```bash
cd scraper
pip install -r requirements.txt
```

## Sources

### Wikidot (scrape_spells.py)

Scrapes from Wikidot spell databases. Best for complete WotC spell lists.

```bash
python scrape_spells.py                  # 2014 rules (dnd5e.wikidot.com, 500+ spells)
python scrape_spells.py --site 2024      # 2024 rules (dnd2024.wikidot.com, 400+ spells)
python scrape_spells.py --reparse        # Reparse from cached HTML (no network)
```

| Site | Spell database | Cached HTML |
|------|---------------|-------------|
| 2014 | `spells.json` | `raw_html/` |
| 2024 | `spells_2024.json` | `raw_html_2024/` |

### Open5e (scrape_open5e.py)

Downloads from the [Open5e REST API](https://api.open5e.com). Includes SRD spells plus third-party OGL content (Kobold Press Deep Magic, Level Up A5E, Tome of Heroes, etc.). Does **not** include non-SRD WotC spells.

```bash
python scrape_open5e.py                    # All 1400+ spells
python scrape_open5e.py --source wotc-srd  # SRD only (319 spells)
python scrape_open5e.py --source dmag      # Deep Magic only (500+ spells)
python scrape_open5e.py --list-sources     # Show available sources
```

Output: `spells_open5e.json` (or `spells_open5e_<source>.json` when filtered)

### 5etools (convert_5etools.py)

Converts spell data from the [5etools](https://5e.tools) GitHub repository. The most complete D&D 5e spell database, covering every official WotC sourcebook including the 2024 PHB (XPHB). 936 spells from 17 sources.

```bash
python convert_5etools.py                        # All sources (936 spells)
python convert_5etools.py --sources PHB XGE TCE  # Specific books
python convert_5etools.py --sources XPHB         # 2024 PHB only
python convert_5etools.py --list-sources         # Show available sources
```

Output: `spells_5etools.json` (or `spells_5etools_<source>.json` when filtered to one source)

## Using with the Spell Card Generator

Use the "Load custom spells.json" button in the web interface to load any output file directly.

## Regenerating SRD spells

If you need to regenerate the SRD-only spell lists (used by the public website):

```bash
# SRD 5.1 (319 spells, 2014 rules)
python scrape_spells.py          # or --reparse if you have cached HTML
python generate_srd_json.py      # outputs srd_spells.json to project root

# SRD 5.2 (339 spells, 2024 rules)
python convert_5etools.py --sources XPHB
python generate_srd_json.py --edition 2024   # outputs srd_spells_2024.json to project root
```
