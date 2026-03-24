#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
move_modifiers.py

Move ingredient modifiers from the Notes column to the Ingredient column
in recipe markdown tables, restoring the original phrasing as written in
the cookbook (e.g., "Grated Sharp Cheese" instead of "Sharp Cheese | Grated").

Modes:
    --report    Show what would change (writes JSON report)
    --apply     Apply the changes to recipe files
    --dry-run   With --apply, preview without writing

Usage:
    python _tools/move_modifiers.py _book_recipes/ --report
    python _tools/move_modifiers.py _book_recipes/ --apply
    python _tools/move_modifiers.py _book_recipes/ --apply --dry-run
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).parent
REPO_ROOT = TOOLS_DIR.parent
MODIFIERS_PATH = REPO_ROOT / "_data" / "ingredient_modifiers.yml"
STATS_DIR = REPO_ROOT / ".recipe_stats"

ALL_DASHES = re.compile(r"^\s*-+\s*$")


# ---------------------------------------------------------------------------
# Modifier loading
# ---------------------------------------------------------------------------

def load_modifiers():
    """Load modifier lists from the shared YAML data file."""
    data = yaml.safe_load(MODIFIERS_PATH.read_text(encoding="utf-8")) or {}
    prefixes = data.get("prefixes", [])
    # Sort longest first so multi-word modifiers match before single-word ones
    prefixes.sort(key=lambda m: -len(m))
    return prefixes


# ---------------------------------------------------------------------------
# Table parsing (mirrors format_recipes.py)
# ---------------------------------------------------------------------------

def is_table_row(line):
    """Return True if line appears to be a markdown table row."""
    stripped = line.strip()
    return (stripped.startswith("|") and stripped.endswith("|")
            and stripped.count("|") > 1)


def split_row(line):
    """Split a markdown table line into its constituent cells."""
    core = line.strip()
    if core.startswith("|"):
        core = core[1:]
    if core.endswith("|"):
        core = core[:-1]
    return [c.strip() for c in core.split("|")]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def extract_modifier_from_notes(notes_text, modifier_list):
    """
    Check if notes_text starts with a known modifier.

    Returns (modifier_canonical_casing, remaining_notes) or (None, None).
    """
    notes_stripped = notes_text.strip()
    if not notes_stripped:
        return None, None

    notes_lower = notes_stripped.lower()

    for mod in modifier_list:  # already sorted longest-first
        mod_lower = mod.lower()

        # Exact match (notes = just the modifier)
        if notes_lower == mod_lower:
            return mod, ""

        # Mixed: modifier + separator + remaining text
        for sep in [" - ", ", "]:
            if notes_lower.startswith(mod_lower + sep):
                remainder = notes_stripped[len(mod) + len(sep):]
                return mod, remainder.strip()

    return None, None


def process_file(path, modifier_list, apply=False, dry_run=False):
    """
    Process a single recipe file. Returns list of change records.
    """
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    changes = []
    new_lines = []
    in_header = True  # skip header/separator rows

    for line_num, line in enumerate(lines, 1):
        if not is_table_row(line):
            new_lines.append(line)
            in_header = True
            continue

        cells = split_row(line)

        # Skip header row, separator row, and rows with too few columns
        if len(cells) < 3:
            new_lines.append(line)
            continue

        ingredient = cells[0]
        notes = cells[2] if len(cells) > 2 else ""

        # Skip header/separator rows
        if (not ingredient or ingredient == "Ingredient"
                or ALL_DASHES.match(ingredient)):
            new_lines.append(line)
            continue

        # Try to extract a modifier from the notes
        modifier, remaining_notes = extract_modifier_from_notes(
            notes, modifier_list)

        if modifier is None:
            new_lines.append(line)
            continue

        # Skip if ingredient already starts with this modifier
        if ingredient.lower().startswith(modifier.lower()):
            new_lines.append(line)
            continue

        # Build new ingredient with modifier prepended
        new_ingredient = f"{modifier} {ingredient}"
        new_notes = remaining_notes

        change = {
            "file": str(path),
            "line": line_num,
            "ingredient_before": ingredient,
            "ingredient_after": new_ingredient,
            "notes_before": notes,
            "notes_after": new_notes,
            "type": "simple" if not remaining_notes else "mixed",
        }
        changes.append(change)

        # Rebuild the line with updated cells
        cells[0] = new_ingredient
        if len(cells) > 2:
            cells[2] = new_notes

        # Rebuild as pipe-separated row preserving spacing style
        new_line = "| " + " | ".join(cells) + " |\n"
        # Collapse trailing empty cell to single space
        if new_line.endswith("|  |\n"):
            new_line = new_line[:-4] + "|\n"
        new_lines.append(new_line)

    if changes and apply and not dry_run:
        path.write_text("".join(new_lines), encoding="utf-8")

    return changes


def run(recipe_dir, mode, dry_run=False):
    """Main entry point."""
    modifier_list = load_modifiers()
    recipe_path = Path(recipe_dir).resolve()
    apply = mode == "apply"

    all_changes = []
    changed_files = set()

    for path in sorted(recipe_path.rglob("*.md")):
        changes = process_file(path, modifier_list, apply=apply,
                               dry_run=dry_run)
        if changes:
            all_changes.extend(changes)
            changed_files.add(str(path))

    # Categorize
    simple = [c for c in all_changes if c["type"] == "simple"]
    mixed = [c for c in all_changes if c["type"] == "mixed"]

    # Write report
    STATS_DIR.mkdir(exist_ok=True)
    report = {
        "total_changes": len(all_changes),
        "simple_moves": len(simple),
        "mixed_moves": len(mixed),
        "files_affected": len(changed_files),
        "changes": all_changes,
    }
    report_path = STATS_DIR / "move_modifiers_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    action = "Would move" if mode == "report" or dry_run else "Moved"
    print(f"{action} {len(all_changes)} modifiers "
          f"({len(simple)} simple, {len(mixed)} mixed) "
          f"across {len(changed_files)} files")
    print(f"Report: {report_path}")

    if apply and not dry_run and changed_files:
        print(f"\nChanged files (run format_recipes.py on these):")
        for f in sorted(changed_files):
            print(f"  {f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Move ingredient modifiers from Notes to Ingredient column."
    )
    parser.add_argument(
        "recipe_dir",
        help="Path to the recipe directory (e.g. _book_recipes/)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--report", action="store_true",
                       help="Report what would change (no modifications)")
    group.add_argument("--apply", action="store_true",
                       help="Apply the changes to recipe files")
    parser.add_argument("--dry-run", action="store_true",
                        help="With --apply, preview without writing")

    args = parser.parse_args()

    if args.report:
        run(args.recipe_dir, "report")
    elif args.apply:
        run(args.recipe_dir, "apply", dry_run=args.dry_run)


if __name__ == "__main__":
    main()
