#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_from.py

Find and fix inconsistencies in the `from:` front-matter field across recipe files.

Usage:
    # Report similarity clusters (does not modify files)
    python _tools/fix_from.py _book_recipes/ --report

    # Apply a canonicalization mappings file
    python _tools/fix_from.py _book_recipes/ --apply
    python _tools/fix_from.py _book_recipes/ --apply --dry-run

    # Override defaults
    python _tools/fix_from.py _book_recipes/ --report --threshold 0.75
    python _tools/fix_from.py _book_recipes/ --apply --mappings-file path/to/mappings.json
"""

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import yaml

# Default paths (relative to cwd, which should be repo root)
DEFAULT_MAPPINGS_FILE = Path("_tools/from_canonical.json")
DEFAULT_REPORT_DIR = Path(".recipe_stats")
DEFAULT_REPORT_FILE = DEFAULT_REPORT_DIR / "from_report.json"

# Similarity threshold: pairs scoring >= this are flagged as potentially the same
DEFAULT_THRESHOLD = 0.80


# ---------------------------------------------------------------------------
# Front-matter parsing (mirrors fix_categories.py)
# ---------------------------------------------------------------------------

def parse_recipe(path):
    """
    Return (fm_dict, fm_lines, body_lines).
    fm_lines: raw lines inside the first --- block (NOT including the --- lines).
    body_lines: everything after the closing ---.
    Returns (None, [], all_lines) if no valid front-matter found.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    if not lines or lines[0].strip() != "---":
        return None, [], lines

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, lines[1:], []

    fm_lines = lines[1:end_idx]
    body_lines = lines[end_idx + 1:]

    try:
        fm_dict = yaml.safe_load("".join(fm_lines)) or {}
        if not isinstance(fm_dict, dict):
            fm_dict = {}
    except yaml.YAMLError:
        fm_dict = {}

    return fm_dict, fm_lines, body_lines


def _yaml_scalar(value):
    """
    Return a YAML-safe inline representation of a string scalar.
    Wraps in double-quotes only if necessary (colon-space, leading special chars, etc.).
    """
    # Characters that force quoting when they appear at the start or in certain positions
    needs_quoting = (
        ": " in value
        or value.startswith(":")
        or value.startswith("#")
        or value.startswith("&")
        or value.startswith("*")
        or value.startswith("!")
        or value.startswith("|")
        or value.startswith(">")
        or value.startswith("'")
        or value.startswith('"')
        or value.startswith("{")
        or value.startswith("[")
    )
    if needs_quoting:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def rewrite_from_in_fm(fm_lines, new_value):
    """
    Replace the `from:` line in fm_lines with the new value.
    Returns a new list of lines.
    Preserves all other front-matter lines unchanged.
    """
    new_lines = []
    replaced = False
    for line in fm_lines:
        if re.match(r'^from\s*:', line) and not replaced:
            new_lines.append(f"from: {_yaml_scalar(new_value)}\n")
            replaced = True
        else:
            new_lines.append(line)
    return new_lines


def write_recipe_from(path, fm_lines, body_lines, new_value):
    content = "---\n" + "".join(rewrite_from_in_fm(fm_lines, new_value)) + "---\n" + "".join(body_lines)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def collect_from_values(directories):
    """
    Scan all .md files in the given directories.
    Returns {from_value: [path, ...]} for files that have a `from:` field.
    Also returns a list of paths with no `from:` field (for informational purposes).
    """
    value_map = {}  # str -> list[Path]
    no_from = []

    for directory in directories:
        for path in sorted(Path(directory).rglob("*.md")):
            fm_dict, fm_lines, body_lines = parse_recipe(path)
            if fm_dict is None:
                continue
            raw = fm_dict.get("from")
            if raw is None:
                no_from.append(path)
                continue
            value = str(raw).strip()
            if not value:
                no_from.append(path)
                continue
            value_map.setdefault(value, []).append(path)

    return value_map, no_from


# ---------------------------------------------------------------------------
# Similarity clustering
# ---------------------------------------------------------------------------

def _similarity(a, b):
    """SequenceMatcher ratio on lowercased, stripped values."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _is_prefix_abbreviation(a, b):
    """
    Return True if the shorter value looks like a prefix/abbreviation of the longer.
    e.g. "Mary Jane K" vs "Mary Jane Kowalchek", or "Joby" vs "Joby McGinley".

    Two cases are handled:
    1. Short ends at a word boundary in the long form: "Joby" vs "Joby McGinley"
       (next char in long is space, comma, dash, or end)
    2. Short ends with a single initial letter that begins the next word in long:
       "Mary Jane K" vs "Mary Jane Kowalchek"
       (next char in long is a letter continuing the word started by short's last char)

    The shorter must be at least 4 chars to avoid spurious short-prefix matches.
    """
    a_norm = re.sub(r'\s+', ' ', a.lower().strip())
    b_norm = re.sub(r'\s+', ' ', b.lower().strip())
    short, long_ = (a_norm, b_norm) if len(a_norm) <= len(b_norm) else (b_norm, a_norm)
    if len(short) < 4:
        return False
    if not long_.startswith(short):
        return False
    if len(long_) == len(short):
        return True
    next_char = long_[len(short)]
    # Case 1: separator — short ends at a word boundary
    if next_char in (' ', ',', '-', '.'):
        return True
    # Case 2: short's last char is a single-letter initial (preceded by a space),
    # and the long form continues that word with more letters.
    # e.g. short = "mary jane k", next_char = "o" (continuing "kowalchek")
    last_word_start = short.rfind(' ')
    if last_word_start >= 0:
        last_word = short[last_word_start + 1:]
        if len(last_word) == 1 and next_char.isalpha():
            return True
    return False


def compute_clusters(value_map, threshold=DEFAULT_THRESHOLD):
    """
    Group `from:` values into clusters where any pair exceeds the similarity
    threshold OR one is a prefix/abbreviation of the other.

    Returns a list of cluster dicts:
        {
            "values": [str, ...],        # all values in cluster, most-frequent first
            "max_similarity": float,     # highest pairwise score in cluster
            "match_reason": str,         # "similarity" | "prefix" | "mixed"
            "recipe_counts": {str: int}, # how many recipes use each value
        }
    Clusters with only one distinct value are omitted.
    """
    values = list(value_map.keys())
    n = len(values)

    # Build adjacency: edges[(i,j)] = (score, reason)
    edges = {}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = values[i], values[j]
            score = _similarity(a, b)
            prefix = _is_prefix_abbreviation(a, b)
            if score >= threshold or prefix:
                reason = "prefix" if (prefix and score < threshold) else (
                    "mixed" if prefix else "similarity"
                )
                edges[(i, j)] = (score, reason)

    # Union-Find to build connected components
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for (i, j) in edges:
        union(i, j)

    # Group by root
    from collections import defaultdict
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    clusters = []
    for members in groups.values():
        if len(members) < 2:
            continue

        # Compute max similarity within group and collect reasons
        max_score = 0.0
        reasons = set()
        for k in range(len(members)):
            for l in range(k + 1, len(members)):
                i, j = members[k], members[l]
                key = (min(i, j), max(i, j))
                if key in edges:
                    score, reason = edges[key]
                    if score > max_score:
                        max_score = score
                    reasons.add(reason)
                else:
                    # Transitive connection — compute directly
                    score = _similarity(values[i], values[j])
                    if score > max_score:
                        max_score = score

        if len(reasons) == 1:
            match_reason = next(iter(reasons))
        elif reasons:
            match_reason = "mixed"
        else:
            match_reason = "similarity"

        # Sort members: most-frequent first, then alphabetical
        member_values = [values[i] for i in members]
        member_values.sort(key=lambda v: (-len(value_map[v]), v))

        clusters.append({
            "values": member_values,
            "max_similarity": round(max_score, 4),
            "match_reason": match_reason,
            "recipe_counts": {v: len(value_map[v]) for v in member_values},
        })

    # Sort clusters: highest similarity first
    clusters.sort(key=lambda c: -c["max_similarity"])
    return clusters


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(clusters, value_map, threshold):
    all_values_sorted = sorted(value_map.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    total_recipes = sum(len(paths) for paths in value_map.values())

    print(f"\n=== from: field report (threshold={threshold:.2f}) ===")
    print(f"Unique values: {len(value_map)}  |  Recipes with from: {total_recipes}\n")

    if not clusters:
        print("No similarity clusters found above threshold.\n")
    else:
        print(f"--- Similarity clusters ({len(clusters)}) ---\n")
        for i, cluster in enumerate(clusters, 1):
            reason_label = {
                "similarity": f"similarity={cluster['max_similarity']:.2f}",
                "prefix":     "prefix/abbreviation match",
                "mixed":      f"similarity={cluster['max_similarity']:.2f} + prefix match",
            }.get(cluster["match_reason"], cluster["match_reason"])
            print(f"  Cluster {i}  [{reason_label}]")
            for v in cluster["values"]:
                count = cluster["recipe_counts"][v]
                print(f"    • {v!r}  ({count} recipe{'s' if count != 1 else ''})")
            print()

    print("--- All from: values ---\n")
    for value, paths in all_values_sorted:
        print(f"  {len(paths):3d}  {value!r}")
    print()


def write_report(clusters, value_map, threshold):
    DEFAULT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "threshold": threshold,
        "unique_value_count": len(value_map),
        "total_recipes_with_from": sum(len(p) for p in value_map.values()),
        "clusters": clusters,
        "all_values": {v: len(paths) for v, paths in
                       sorted(value_map.items(), key=lambda kv: (-len(kv[1]), kv[0]))},
    }
    DEFAULT_REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {DEFAULT_REPORT_FILE}")


# ---------------------------------------------------------------------------
# Applying mappings
# ---------------------------------------------------------------------------

def load_mappings(mappings_file):
    p = Path(mappings_file)
    if not p.exists():
        print(f"Mappings file not found: {p}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print(f"Mappings file must be a JSON object (dict): {p}", file=sys.stderr)
        sys.exit(1)
    return data


def apply_mappings(directories, mappings, dry_run=False):
    """
    For each recipe file whose `from:` value appears as a key in mappings,
    rewrite it to the canonical value.

    Returns list of (path, old_value, new_value) for all changed files.
    """
    changes = []

    for directory in directories:
        for path in sorted(Path(directory).rglob("*.md")):
            fm_dict, fm_lines, body_lines = parse_recipe(path)
            if fm_dict is None:
                continue
            raw = fm_dict.get("from")
            if raw is None:
                continue
            old_value = str(raw).strip()
            if old_value not in mappings:
                continue
            new_value = mappings[old_value]
            if old_value == new_value:
                continue

            changes.append((path, old_value, new_value))
            if not dry_run:
                write_recipe_from(path, fm_lines, body_lines, new_value)

    return changes


def print_apply_summary(changes, dry_run):
    label = "[DRY RUN] " if dry_run else ""
    if not changes:
        print(f"{label}No files needed updating.")
        return

    print(f"\n{label}Updated {len(changes)} file(s):\n")
    for path, old, new in changes:
        print(f"  {path}")
        print(f"    {old!r}  →  {new!r}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Find and fix inconsistencies in `from:` front-matter fields."
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["_book_recipes/"],
        help="Recipe directories to scan (default: _book_recipes/)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Report similarity clusters and write from_report.json (does not modify files)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply canonicalization mappings to recipe files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --apply, show what would change without writing files",
    )
    parser.add_argument(
        "--mappings-file",
        default=str(DEFAULT_MAPPINGS_FILE),
        metavar="PATH",
        help=f"JSON mappings file (default: {DEFAULT_MAPPINGS_FILE})",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        metavar="FLOAT",
        help=f"Similarity threshold for clustering (default: {DEFAULT_THRESHOLD})",
    )

    args = parser.parse_args()

    if not args.report and not args.apply:
        # Default: run report
        args.report = True

    value_map, no_from = collect_from_values(args.directories)

    if args.report:
        clusters = compute_clusters(value_map, args.threshold)
        print_report(clusters, value_map, args.threshold)
        write_report(clusters, value_map, args.threshold)

    if args.apply:
        mappings = load_mappings(args.mappings_file)
        changes = apply_mappings(args.directories, mappings, dry_run=args.dry_run)
        print_apply_summary(changes, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
