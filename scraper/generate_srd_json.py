#!/usr/bin/env python3
"""
Filters spell data down to SRD spells only.
Outputs srd_spells.json (5.1) or srd_spells_2024.json (5.2) for use with the public website.

Usage:
    python generate_srd_json.py                  # SRD 5.1 from Wikidot data
    python generate_srd_json.py --edition 2024   # SRD 5.2 from 5etools data

SRD 5.1: Expects spells.json (output of scrape_spells.py). Uses hardcoded spell list.
SRD 5.2: Expects spells_5etools_xphb.json (output of convert_5etools.py --sources XPHB).
          Uses the srd52 flag from 5etools data.
"""

import argparse
import json
from pathlib import Path

# PHB name -> SRD name (None means the name is already the SRD name)
# This dict contains BOTH:
#   - PHB names that need renaming (value = SRD name)
#   - SRD names that match as-is (value = None)
SRD_SPELLS = {
    "Acid Arrow": None,
    "Acid Splash": None,
    "Aid": None,
    "Alarm": None,
    "Alter Self": None,
    "Animal Friendship": None,
    "Animal Messenger": None,
    "Animal Shapes": None,
    "Animate Dead": None,
    "Animate Objects": None,
    "Antilife Shell": None,
    "Antimagic Field": None,
    "Antipathy/Sympathy": None,
    "Arcane Eye": None,
    "Arcane Hand": None,
    "Arcane Lock": None,
    "Arcane Sword": None,
    "Arcanist's Magic Aura": None,
    "Astral Projection": None,
    "Augury": None,
    "Awaken": None,
    "Bane": None,
    "Banishment": None,
    "Barkskin": None,
    "Beacon of Hope": None,
    "Bestow Curse": None,
    "Bigby's Hand": "Arcane Hand",
    "Black Tentacles": None,
    "Blade Barrier": None,
    "Bless": None,
    "Blight": None,
    "Blindness/Deafness": None,
    "Blink": None,
    "Blur": None,
    "Branding Smite": None,
    "Burning Hands": None,
    "Call Lightning": None,
    "Calm Emotions": None,
    "Chain Lightning": None,
    "Charm Person": None,
    "Chill Touch": None,
    "Circle of Death": None,
    "Clairvoyance": None,
    "Clone": None,
    "Cloudkill": None,
    "Color Spray": None,
    "Command": None,
    "Commune": None,
    "Commune with Nature": None,
    "Comprehend Languages": None,
    "Compulsion": None,
    "Cone of Cold": None,
    "Confusion": None,
    "Conjure Animals": None,
    "Conjure Celestial": None,
    "Conjure Elemental": None,
    "Conjure Fey": None,
    "Conjure Minor Elementals": None,
    "Conjure Woodland Beings": None,
    "Contact Other Plane": None,
    "Contagion": None,
    "Contingency": None,
    "Continual Flame": None,
    "Control Water": None,
    "Control Weather": None,
    "Counterspell": None,
    "Create Food and Water": None,
    "Create Undead": None,
    "Create or Destroy Water": None,
    "Creation": None,
    "Cure Wounds": None,
    "Dancing Lights": None,
    "Darkness": None,
    "Darkvision": None,
    "Daylight": None,
    "Death Ward": None,
    "Delayed Blast Fireball": None,
    "Demiplane": None,
    "Detect Evil and Good": None,
    "Detect Magic": None,
    "Detect Poison and Disease": None,
    "Detect Thoughts": None,
    "Dimension Door": None,
    "Disguise Self": None,
    "Disintegrate": None,
    "Dispel Evil and Good": None,
    "Dispel Magic": None,
    "Divination": None,
    "Divine Favor": None,
    "Divine Word": None,
    "Dominate Beast": None,
    "Dominate Monster": None,
    "Dominate Person": None,
    "Drawmij's Instant Summons": "Instant Summons",
    "Dream": None,
    "Druidcraft": None,
    "Earthquake": None,
    "Eldritch Blast": None,
    "Enhance Ability": None,
    "Enlarge/Reduce": None,
    "Entangle": None,
    "Enthrall": None,
    "Etherealness": None,
    "Evard's Black Tentacles": "Black Tentacles",
    "Expeditious Retreat": None,
    "Eyebite": None,
    "Fabricate": None,
    "Faerie Fire": None,
    "Faithful Hound": None,
    "False Life": None,
    "Fear": None,
    "Feather Fall": None,
    "Feeblemind": None,
    "Find Familiar": None,
    "Find Steed": None,
    "Find Traps": None,
    "Find the Path": None,
    "Finger of Death": None,
    "Fire Bolt": None,
    "Fire Shield": None,
    "Fire Storm": None,
    "Fireball": None,
    "Flame Blade": None,
    "Flame Strike": None,
    "Flaming Sphere": None,
    "Flesh to Stone": None,
    "Floating Disk": None,
    "Fly": None,
    "Fog Cloud": None,
    "Forbiddance": None,
    "Forcecage": None,
    "Foresight": None,
    "Freedom of Movement": None,
    "Freezing Sphere": None,
    "Gaseous Form": None,
    "Gate": None,
    "Geas": None,
    "Gentle Repose": None,
    "Giant Insect": None,
    "Glibness": None,
    "Globe of Invulnerability": None,
    "Glyph of Warding": None,
    "Goodberry": None,
    "Grease": None,
    "Greater Invisibility": None,
    "Greater Restoration": None,
    "Guardian of Faith": None,
    "Guards and Wards": None,
    "Guidance": None,
    "Guiding Bolt": None,
    "Gust of Wind": None,
    "Hallow": None,
    "Hallucinatory Terrain": None,
    "Harm": None,
    "Haste": None,
    "Heal": None,
    "Healing Word": None,
    "Heat Metal": None,
    "Hellish Rebuke": None,
    "Heroes' Feast": None,
    "Heroism": None,
    "Hideous Laughter": None,
    "Hold Monster": None,
    "Hold Person": None,
    "Holy Aura": None,
    "Hunter's Mark": None,
    "Hypnotic Pattern": None,
    "Ice Storm": None,
    "Identify": None,
    "Illusory Script": None,
    "Imprisonment": None,
    "Incendiary Cloud": None,
    "Inflict Wounds": None,
    "Insect Plague": None,
    "Instant Summons": None,
    "Invisibility": None,
    "Irresistible Dance": None,
    "Jump": None,
    "Knock": None,
    "Legend Lore": None,
    "Leomund's Secret Chest": "Secret Chest",
    "Leomund's Tiny Hut": "Tiny Hut",
    "Lesser Restoration": None,
    "Levitate": None,
    "Light": None,
    "Lightning Bolt": None,
    "Locate Animals or Plants": None,
    "Locate Creature": None,
    "Locate Object": None,
    "Longstrider": None,
    "Mage Armor": None,
    "Mage Hand": None,
    "Magic Circle": None,
    "Magic Jar": None,
    "Magic Missile": None,
    "Magic Mouth": None,
    "Magic Weapon": None,
    "Magnificent Mansion": None,
    "Major Image": None,
    "Mass Cure Wounds": None,
    "Mass Heal": None,
    "Mass Healing Word": None,
    "Mass Suggestion": None,
    "Maze": None,
    "Meld into Stone": None,
    "Melf's Acid Arrow": "Acid Arrow",
    "Mending": None,
    "Message": None,
    "Meteor Swarm": None,
    "Mind Blank": None,
    "Minor Illusion": None,
    "Mirage Arcane": None,
    "Mirror Image": None,
    "Mislead": None,
    "Misty Step": None,
    "Modify Memory": None,
    "Moonbeam": None,
    "Mordenkainen's Faithful Hound": "Faithful Hound",
    "Mordenkainen's Magnificent Mansion": "Magnificent Mansion",
    "Mordenkainen's Private Sanctum": "Private Sanctum",
    "Mordenkainen's Sword": "Arcane Sword",
    "Move Earth": None,
    "Nondetection": None,
    "Nystul's Magic Aura": "Arcanist's Magic Aura",
    "Otiluke's Freezing Sphere": "Freezing Sphere",
    "Otiluke's Resilient Sphere": "Resilient Sphere",
    "Otto's Irresistible Dance": "Irresistible Dance",
    "Pass Without Trace": None,
    "Passwall": None,
    "Phantasmal Killer": None,
    "Phantom Steed": None,
    "Planar Ally": None,
    "Planar Binding": None,
    "Plane Shift": None,
    "Plant Growth": None,
    "Poison Spray": None,
    "Polymorph": None,
    "Power Word: Kill": None,
    "Power Word: Stun": None,
    "Prayer of Healing": None,
    "Prestidigitation": None,
    "Prismatic Spray": None,
    "Prismatic Wall": None,
    "Private Sanctum": None,
    "Produce Flame": None,
    "Programmed Illusion": None,
    "Project Image": None,
    "Protection from Energy": None,
    "Protection from Evil and Good": None,
    "Protection from Poison": None,
    "Purify Food and Drink": None,
    "Raise Dead": None,
    "Rary's Telepathic Bond": "Telepathic Bond",
    "Ray of Enfeeblement": None,
    "Ray of Frost": None,
    "Regenerate": None,
    "Reincarnate": None,
    "Remove Curse": None,
    "Resilient Sphere": None,
    "Resistance": None,
    "Resurrection": None,
    "Reverse Gravity": None,
    "Revivify": None,
    "Rope Trick": None,
    "Sacred Flame": None,
    "Sanctuary": None,
    "Scorching Ray": None,
    "Scrying": None,
    "Secret Chest": None,
    "See Invisibility": None,
    "Seeming": None,
    "Sending": None,
    "Sequester": None,
    "Shapechange": None,
    "Shatter": None,
    "Shield": None,
    "Shield of Faith": None,
    "Shillelagh": None,
    "Shocking Grasp": None,
    "Silence": None,
    "Silent Image": None,
    "Simulacrum": None,
    "Sleep": None,
    "Sleet Storm": None,
    "Slow": None,
    "Spare the Dying": None,
    "Speak with Animals": None,
    "Speak with Dead": None,
    "Speak with Plants": None,
    "Spider Climb": None,
    "Spike Growth": None,
    "Spirit Guardians": None,
    "Spiritual Weapon": None,
    "Stinking Cloud": None,
    "Stone Shape": None,
    "Stoneskin": None,
    "Storm of Vengeance": None,
    "Suggestion": None,
    "Sunbeam": None,
    "Sunburst": None,
    "Symbol": None,
    "Tasha's Hideous Laughter": "Hideous Laughter",
    "Telekinesis": None,
    "Telepathic Bond": None,
    "Teleport": None,
    "Teleportation Circle": None,
    "Tenser's Floating Disk": "Floating Disk",
    "Thaumaturgy": None,
    "Thunderwave": None,
    "Time Stop": None,
    "Tiny Hut": None,
    "Tongues": None,
    "Transport via Plants": None,
    "Tree Stride": None,
    "True Polymorph": None,
    "True Resurrection": None,
    "True Seeing": None,
    "True Strike": None,
    "Unseen Servant": None,
    "Vampiric Touch": None,
    "Vicious Mockery": None,
    "Wall of Fire": None,
    "Wall of Force": None,
    "Wall of Ice": None,
    "Wall of Stone": None,
    "Wall of Thorns": None,
    "Warding Bond": None,
    "Water Breathing": None,
    "Water Walk": None,
    "Web": None,
    "Weird": None,
    "Wind Walk": None,
    "Wind Wall": None,
    "Wish": None,
    "Word of Recall": None,
    "Zone of Truth": None,
}


def generate_srd51():
    """Generate SRD 5.1 spell list.

    Prefers 5etools PHB data (has subclass info), falls back to Wikidot data.
    """
    script_dir = Path(__file__).parent
    output_file = script_dir.parent / "srd_spells.json"

    # Prefer 5etools data (has subclass info + srd flag)
    fivetools_file = script_dir / "spells_5etools_phb.json"
    wikidot_file = script_dir / "spells.json"

    if fivetools_file.exists():
        print(f"Reading from {fivetools_file.name} (5etools, has subclass data)")
        with open(fivetools_file, "r", encoding="utf-8") as f:
            all_spells = json.load(f)
        # Filter by srd flag and apply name de-branding
        srd_spells = []
        for spell in all_spells:
            if not spell.get("srd"):
                continue
            new_spell = dict(spell)
            srd_name = SRD_SPELLS.get(spell["name"])
            if srd_name is not None:
                new_spell["name"] = srd_name
            new_spell["source"] = "SRD"
            new_spell.pop("srd", None)
            new_spell.pop("srd52", None)
            srd_spells.append(new_spell)
    elif wikidot_file.exists():
        print(f"Reading from {wikidot_file.name} (Wikidot)")
        with open(wikidot_file, "r", encoding="utf-8") as f:
            all_spells = json.load(f)
        srd_spells = []
        matched = set()
        for spell in all_spells:
            name = spell["name"]
            if name in SRD_SPELLS:
                new_spell = dict(spell)
                srd_name = SRD_SPELLS[name]
                if srd_name is not None:
                    new_spell["name"] = srd_name
                new_spell["source"] = "SRD"
                srd_spells.append(new_spell)
                matched.add(name)
        srd_only_names = {v for v in SRD_SPELLS.values() if v is not None}
        matchable_names = set(SRD_SPELLS.keys()) - srd_only_names
        unmatched = matchable_names - matched
        if unmatched:
            print(f"\nWARNING: {len(unmatched)} SRD spells not found:")
            for name in sorted(unmatched):
                print(f"  - {name}")
    else:
        print(f"ERROR: No input file found.")
        print(f"Run: python convert_5etools.py --sources PHB")
        print(f"  or: python scrape_spells.py")
        return []

    srd_spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(srd_spells, f, indent=2, ensure_ascii=False)

    print(f"Generated {output_file.name}: {len(srd_spells)} SRD 5.1 spells")
    return srd_spells


def generate_srd52():
    """Generate SRD 5.2 spell list from 5etools XPHB data."""
    script_dir = Path(__file__).parent
    input_file = script_dir / "spells_5etools_xphb.json"
    output_file = script_dir.parent / "srd_spells_2024.json"

    if not input_file.exists():
        print(f"ERROR: {input_file} not found.")
        print("Run first: python convert_5etools.py --sources XPHB")
        return []

    with open(input_file, "r", encoding="utf-8") as f:
        all_spells = json.load(f)

    srd_spells = []
    for spell in all_spells:
        if spell.get("srd52"):
            new_spell = dict(spell)
            new_spell["source"] = "SRD"
            # Remove the srd/srd52 flags from the output
            new_spell.pop("srd", None)
            new_spell.pop("srd52", None)
            srd_spells.append(new_spell)

    srd_spells.sort(key=lambda s: (s.get("level", 0), s.get("name", "")))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(srd_spells, f, indent=2, ensure_ascii=False)

    print(f"Generated {output_file.name}: {len(srd_spells)} SRD 5.2 spells")
    return srd_spells


def print_summary(srd_spells):
    """Print level breakdown."""
    by_level = {}
    for spell in srd_spells:
        level = spell.get("level", 0)
        by_level[level] = by_level.get(level, 0) + 1

    print("\nBy level:")
    for level in sorted(by_level.keys()):
        label = "Cantrips" if level == 0 else f"Level {level}"
        print(f"  {label}: {by_level[level]}")


def main():
    parser = argparse.ArgumentParser(description="Generate SRD spell JSON for the website")
    parser.add_argument("--edition", choices=["2014", "2024"], default="2014",
                        help="Which SRD edition (default: 2014)")
    args = parser.parse_args()

    if args.edition == "2024":
        spells = generate_srd52()
    else:
        spells = generate_srd51()

    if spells:
        print_summary(spells)


if __name__ == "__main__":
    main()
