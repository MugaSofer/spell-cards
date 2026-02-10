# D&D 5e Spell Scraper

Scrapes spell data from [dnd5e.wikidot.com](http://dnd5e.wikidot.com) and outputs a JSON file compatible with the [Spell Card Generator](https://github.com/MugaSofer/spell-cards).

The website ships with SRD 5.1 spells only (319 spells, freely licensed). Use this scraper to generate a complete dataset of 500+ spells for personal use.

## Setup

```bash
cd scraper
pip install -r requirements.txt
```

## Usage

**Full scrape** (fetches all spell pages from the wiki):
```bash
python scrape_spells.py
```

**Reparse only** (uses cached HTML, no network requests):
```bash
python scrape_spells.py --reparse
```

This outputs:
- `spells.json` — Full spell database
- `raw_html/` — Cached HTML for each spell page

## Using with the Spell Card Generator

Copy `spells.json` to the project root directory, or use the "Load custom spells.json" button in the web interface to load it directly.

## Regenerating SRD spells

If you need to regenerate the SRD-only spell list:

```bash
python scrape_spells.py          # or --reparse if you have cached HTML
python generate_srd_json.py      # outputs srd_spells.json to project root
```
