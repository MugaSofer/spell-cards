# D&D 5e Spell Scraper

Scrapes spell data from Wikidot spell databases and outputs a JSON file compatible with the [Spell Card Generator](https://github.com/MugaSofer/spell-cards).

Supports two sources:
- **2014 rules** — [dnd5e.wikidot.com](http://dnd5e.wikidot.com) (500+ spells from PHB, XGE, TCE, etc.)
- **2024 rules** — [dnd2024.wikidot.com](http://dnd2024.wikidot.com) (400+ spells from the 2024 PHB)

The website ships with SRD 5.1 spells only (319 spells, freely licensed). Use this scraper to generate a complete dataset for personal use.

## Setup

```bash
cd scraper
pip install -r requirements.txt
```

## Usage

**Scrape 2014 spells** (default):
```bash
python scrape_spells.py
```

**Scrape 2024 spells**:
```bash
python scrape_spells.py --site 2024
```

**Reparse only** (uses cached HTML, no network requests):
```bash
python scrape_spells.py --reparse
python scrape_spells.py --site 2024 --reparse
```

Output per site:
| Site | Spell database | Cached HTML |
|------|---------------|-------------|
| 2014 | `spells.json` | `raw_html/` |
| 2024 | `spells_2024.json` | `raw_html_2024/` |

## Using with the Spell Card Generator

Use the "Load custom spells.json" button in the web interface to load the output file directly.

## Regenerating SRD spells

If you need to regenerate the SRD-only spell list (used by the public website):

```bash
python scrape_spells.py          # or --reparse if you have cached HTML
python generate_srd_json.py      # outputs srd_spells.json to project root
```
