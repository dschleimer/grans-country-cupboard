#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
recipe_stats.py

Recursively scan one or more directories for files that contain a YAML
front‑matter block (delimited by lines that contain only '---').  For each
file found, extract selected attributes and build a histogram for each
attribute.  The histograms are written as JSON files into a hidden
`.recipe_stats` directory that lives in the current working directory.

The script is intentionally generic – adding a new attribute to be
summarised only requires inserting its name into the `ATTRIBUTES` list.
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import yaml

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Attributes to summarise.  Add a new attribute name here if you want to
# summarise it as well.  The script will automatically handle missing
# attributes and will work for scalar values or list values.
ATTRIBUTES = ["from", "categories"]

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #

def find_front_matter(path: Path) -> dict | None:
    """
    Return a dict with the parsed YAML front‑matter from *path*.
    If the file does not contain a front‑matter block, return None.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    front_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        front_lines.append(line)

    try:
        data = yaml.safe_load("\n".join(front_lines))
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def update_histograms(histograms: dict, data: dict):
    """
    Update *histograms* with the values found in *data*.
    `histograms` is a dict mapping attribute names to Counter‑like dicts.
    """
    for attr in ATTRIBUTES:
        if attr not in data:
            continue
        value = data[attr]
        if isinstance(value, list):
            for item in value:
                histograms[attr][item] += 1
        else:
            histograms[attr][value] += 1


def write_histograms(histograms: dict, out_dir: Path):
    """
    Write each histogram to a separate JSON file in *out_dir*.
    File names are `<attribute>_counts.json`.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for attr, counts in histograms.items():
        out_path = out_dir / f"{attr}_counts.json"
        # Convert defaultdict to a normal dict for JSON serialisation
        # sorting by count in the process
        counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
        json.dump(counts, out_path.open("w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Main processing routine
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Collect recipe front‑matter statistics."
    )
    parser.add_argument(
        "directories",
        nargs="+",
        help="One or more directories to scan for recipe files.",
    )
    args = parser.parse_args()

    # Output directory – always relative to the current working dir
    stats_dir = Path.cwd() / ".recipe_stats"

    # Initialise a histogram for each attribute
    histograms = {attr: defaultdict(int) for attr in ATTRIBUTES}

    # Walk each supplied directory
    for root_dir in args.directories:
        root_path = Path(root_dir).resolve()
        for file_path in root_path.rglob("*"):
            if not file_path.is_file():
                continue
            front = find_front_matter(file_path)
            if front:
                update_histograms(histograms, front)

    # Write the resulting histograms to disk
    write_histograms(histograms, stats_dir)

    # Simple report
    total_recipes = sum(sum(c.values()) for c in histograms.values())
    print(f"Processed {total_recipes} recipes.")
    print(f"Histograms written to {stats_dir}")


if __name__ == "__main__":
    main()