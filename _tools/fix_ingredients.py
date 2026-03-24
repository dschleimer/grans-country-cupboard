#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_ingredients.py

Ingredient taxonomy bootstrap, validation, and reporting tool.

Modes:
    --bootstrap   Scan recipes, auto-generate draft ingredient_mappings.yml
    --report      Report unmapped strings, orphans, taxonomy gaps, typo candidates
    --validate    CI-friendly: exit 1 if unmapped or canonical missing from taxonomy

Usage:
    python _tools/fix_ingredients.py _book_recipes/ --bootstrap
    python _tools/fix_ingredients.py _book_recipes/ --report
    python _tools/fix_ingredients.py _book_recipes/ --validate
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).parent
REPO_ROOT = TOOLS_DIR.parent
TAXONOMY_PATH = REPO_ROOT / "_data" / "ingredient_taxonomy.yml"
MAPPINGS_PATH = TOOLS_DIR / "ingredient_mappings.yml"
STATS_DIR = REPO_ROOT / ".recipe_stats"

ALL_DASHES = re.compile(r"^\s*-+\s*$")

# Modifier prefixes — preparation words that don't change the identity.
# Explicit mappings always win over modifier stripping.
# This is the single source of truth for modifier lists.
MODIFIER_PREFIXES = [
    "Melted", "Softened", "Grated", "Chopped", "Sliced", "Crushed",
    "Dried", "Fresh", "Cooked", "Roasted", "Minced", "Slivered",
    "Diced", "Shredded", "Mashed", "Candied", "Flaked", "Boiling",
    "Hot", "Cold", "Warm", "Scalded", "Sifted", "Blanched",
    "Finely Chopped", "Thinly Sliced", "Frozen", "Instant",
    "Large", "Small", "Tiny", "Raw", "Peeled",
]
# Sort longest first so multi-word modifiers match before single-word ones
MODIFIER_PREFIXES.sort(key=lambda m: -len(m))

# Modifier suffixes — preparation words appearing after the ingredient,
# typically separated by " - " (e.g., "Cheese - Grated").
MODIFIER_SUFFIXES = [
    "Melted", "Softened", "Grated", "Chopped", "Sliced", "Crushed",
    "Dried", "Cooked", "Roasted", "Minced", "Slivered", "Diced",
    "Shredded", "Mashed", "Candied", "Flaked", "Sifted", "Blanched",
]


# ---------------------------------------------------------------------------
# Ingredient extraction (mirrors _plugins/ingredients.rb logic)
# ---------------------------------------------------------------------------

def extract_ingredients_from_file(path):
    """
    Extract raw ingredient strings from a recipe file's markdown tables.
    Returns a list of (raw_string, line_number) tuples.
    """
    results = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_num, line in enumerate(lines, 1):
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        if len(cells) < 2:
            continue
        cell = cells[1].strip()
        if not cell or cell == "Ingredient" or ALL_DASHES.match(cell):
            continue
        # Special case: danish_style_sandwiches has multi-column ingredients
        if path.name == "danish_style_sandwiches.md":
            if cell == "Bread":
                continue
            ingredient_cells = cells[1:-1]  # all columns except outer empties
        else:
            ingredient_cells = cells[1:2]

        for raw_cell in ingredient_cells:
            raw = raw_cell.strip()
            if raw and not ALL_DASHES.match(raw):
                results.append((raw, line_num))
    return results


def scan_all_ingredients(recipe_dir):
    """
    Scan all recipe files and return:
    - ingredient_counts: {raw_string: count}
    - ingredient_files: {raw_string: [filepath, ...]}
    """
    recipe_path = Path(recipe_dir).resolve()
    counts = defaultdict(int)
    files = defaultdict(list)
    for path in sorted(recipe_path.rglob("*.md")):
        for raw, _line in extract_ingredients_from_file(path):
            counts[raw] += 1
            if str(path) not in files[raw]:
                files[raw].append(str(path))
    return dict(counts), dict(files)


# ---------------------------------------------------------------------------
# Title-case normalization (mirrors ingredients.rb logic)
# ---------------------------------------------------------------------------

def title_case_ingredient(raw):
    """Title-case an ingredient string, matching the Ruby plugin's logic."""
    # Split on non-alphanumeric, non-apostrophe characters
    parts = re.split(r"[^a-zA-Z0-9_']", raw)
    result = raw
    for part in parts:
        if not part:
            continue
        capitalized = part[0].upper() + part[1:] if part else part
        # Replace only the exact word (not substrings)
        pattern = re.compile(
            r"(?<![a-zA-Z0-9_'])" + re.escape(part) + r"(?![a-zA-Z0-9_'])"
        )
        result = pattern.sub(capitalized, result, count=1)
    return result


def strip_parentheticals(s):
    """Remove parenthetical notes like (grated), (melted)."""
    return re.sub(r"\([^)]+\)", "", s).strip()


def normalize_raw(raw):
    """Apply the same normalization as the Ruby plugin: title-case + strip parens."""
    return strip_parentheticals(title_case_ingredient(raw))


# ---------------------------------------------------------------------------
# Taxonomy helpers
# ---------------------------------------------------------------------------

def load_taxonomy():
    """Load and parse the taxonomy YAML. Returns the raw dict."""
    if not TAXONOMY_PATH.exists():
        return {}
    return yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8")) or {}


def flatten_taxonomy(taxonomy):
    """
    Walk the taxonomy tree and return:
    - all_canonical: set of all canonical ingredient names
    - canonical_to_aisle: {canonical_name: aisle_name}
    - canonical_to_parent: {canonical_name: parent_name or None}
    - see_also_map: {canonical_name: [related_names]}
    """
    all_canonical = set()
    canonical_to_aisle = {}
    canonical_to_parent = {}
    see_also_map = {}

    def walk_members(members, aisle, parent=None):
        for member in members:
            if isinstance(member, str):
                name = member
                variations = []
                see_also = []
            else:
                name = member["name"]
                variations = member.get("variations", [])
                see_also = member.get("see_also", [])

            all_canonical.add(name)
            canonical_to_aisle[name] = aisle
            canonical_to_parent[name] = parent
            if see_also:
                see_also_map[name] = see_also

            if variations:
                walk_members(variations, aisle, parent=name)

    for aisle_name, aisle_data in taxonomy.items():
        members = aisle_data.get("members", [])
        walk_members(members, aisle_name)

    return all_canonical, canonical_to_aisle, canonical_to_parent, see_also_map


# ---------------------------------------------------------------------------
# Mappings helpers
# ---------------------------------------------------------------------------

def load_mappings():
    """Load the mappings YAML. Returns {raw_lower: canonical_name}."""
    if not MAPPINGS_PATH.exists():
        return {}
    raw = yaml.safe_load(MAPPINGS_PATH.read_text(encoding="utf-8")) or {}
    # Build case-insensitive lookup
    return {k.lower(): v for k, v in raw.items() if v is not None}


def resolve_ingredient(raw, mappings, canonical_set):
    """
    Resolve a raw ingredient string to its canonical name.
    Returns (canonical_name, resolution_method) where method is one of:
    'exact', 'mapping', 'modifier', 'self', 'unknown'
    """
    normalized = normalize_raw(raw)
    key = normalized.lower()

    # 1. Check mappings (case-insensitive)
    if key in mappings:
        return mappings[key], "mapping"

    # 2. Check if normalized form is already a canonical name
    for canon in canonical_set:
        if canon.lower() == key:
            return canon, "self"

    # 3. Try modifier prefix stripping
    for mod in MODIFIER_PREFIXES:
        mod_lower = mod.lower()
        if key.startswith(mod_lower + " "):
            remainder = normalized[len(mod) + 1:].strip()
            remainder_key = remainder.lower()
            # Check mappings for remainder
            if remainder_key in mappings:
                return mappings[remainder_key], "modifier"
            # Check if remainder is a canonical name
            for canon in canonical_set:
                if canon.lower() == remainder_key:
                    return canon, "modifier"

    # 4. Try modifier suffix stripping (e.g., "Cheese - Grated")
    for mod in MODIFIER_SUFFIXES:
        mod_lower = mod.lower()
        # Pattern: "Ingredient - Modifier" or "Ingredient, Modifier"
        for sep in [" - ", ", "]:
            if key.endswith(sep.lower() + mod_lower):
                remainder = normalized[:-(len(sep) + len(mod))].strip()
                remainder_key = remainder.lower()
                if remainder_key in mappings:
                    return mappings[remainder_key], "modifier"
                for canon in canonical_set:
                    if canon.lower() == remainder_key:
                        return canon, "modifier"

    # 5. Unknown
    return normalized, "unknown"


# ---------------------------------------------------------------------------
# Bootstrap mode
# ---------------------------------------------------------------------------

def find_typo_candidates(ingredients):
    """Find pairs of ingredient strings that are suspiciously similar."""
    names = sorted(set(ingredients.keys()))
    candidates = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            # Skip if they're the same when lowercased
            if a.lower() == b.lower():
                candidates.append((a, b, 1.0, "case"))
                continue
            ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio()
            if ratio >= 0.85:
                candidates.append((a, b, ratio, "similar"))
    return candidates


def find_plural_pairs(ingredients):
    """Find singular/plural pairs."""
    names = sorted(set(ingredients.keys()))
    lower_map = {n.lower(): n for n in names}
    pairs = []
    for name in names:
        low = name.lower()
        # Check common plural patterns
        if low.endswith("s") and low[:-1] in lower_map:
            pairs.append((lower_map[low[:-1]], name))
        elif low.endswith("es") and low[:-2] in lower_map:
            pairs.append((lower_map[low[:-2]], name))
    return pairs


def bootstrap(recipe_dir):
    """Generate a draft ingredient_mappings.yml from all recipe files."""
    counts, files = scan_all_ingredients(recipe_dir)

    # Normalize all raw strings
    normalized_groups = defaultdict(list)  # {normalized_lower: [(raw, count)]}
    for raw, count in counts.items():
        norm = normalize_raw(raw)
        normalized_groups[norm.lower()].append((raw, count))

    # Build draft mappings
    mappings = {}  # {raw: canonical_or_None}

    # 1. Group case variants — pick the most frequent or best-cased form
    case_mappings = 0
    for norm_lower, variants in normalized_groups.items():
        if len(variants) == 1:
            continue
        # Pick the variant with highest count as canonical
        variants.sort(key=lambda x: -x[1])
        canonical = normalize_raw(variants[0][0])
        for raw, _ in variants:
            norm = normalize_raw(raw)
            if norm != canonical:
                mappings[raw] = canonical
                case_mappings += 1

    # 2. Find plural pairs
    norm_counts = {}
    for norm_lower, variants in normalized_groups.items():
        total = sum(c for _, c in variants)
        canonical = normalize_raw(variants[0][0]) if variants else norm_lower
        norm_counts[canonical] = total

    plural_pairs = find_plural_pairs(norm_counts)
    plural_mappings = 0
    for singular, plural in plural_pairs:
        s_count = norm_counts.get(singular, 0)
        p_count = norm_counts.get(plural, 0)
        # Keep the more common form
        if s_count >= p_count:
            mappings[plural] = singular
        else:
            mappings[singular] = plural
        plural_mappings += 1

    # 3. Find typo candidates
    typo_candidates = find_typo_candidates(norm_counts)

    # 4. Identify unmapped entries (everything not yet in mappings)
    all_raw = set(counts.keys())
    mapped_raw = set(mappings.keys())
    unmapped = all_raw - mapped_raw

    # Write draft mappings
    STATS_DIR.mkdir(exist_ok=True)

    # Write as YAML
    output = {}
    sections = {
        "case_variants": {},
        "plural_normalization": {},
        "needs_review": {},
    }

    for raw, canonical in sorted(mappings.items()):
        output[raw] = canonical

    # Add unmapped entries as null (needs review)
    for raw in sorted(unmapped):
        norm = normalize_raw(raw)
        # Don't add self-mappings or empty/dash-only entries
        if ALL_DASHES.match(raw) or not raw.strip():
            continue
        # Self-mapping entries don't need explicit mapping
        # but we include them commented for review
        output[raw] = None

    # Write the full draft
    draft_path = STATS_DIR / "ingredient_mappings_draft.yml"
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write("# Draft ingredient mappings — auto-generated by fix_ingredients.py --bootstrap\n")
        f.write("# Review and move to _tools/ingredient_mappings.yml\n")
        f.write("#\n")
        f.write("# Format: \"raw string\": Canonical Name\n")
        f.write("# null entries need manual review\n")
        f.write(f"# Total entries: {len(output)}\n")
        f.write(f"# Auto-mapped: {len(mappings)}\n")
        f.write(f"# Needs review (null): {len(output) - len(mappings)}\n\n")

        # Write auto-mapped entries first
        if mappings:
            f.write("# --- Auto-mapped entries ---\n")
            for raw in sorted(mappings.keys(), key=str.lower):
                canonical = mappings[raw]
                f.write(f"{yaml.dump({raw: canonical}, default_flow_style=False, allow_unicode=True)}")
            f.write("\n")

        # Write unmapped entries
        unmapped_list = [raw for raw in sorted(unmapped, key=str.lower)
                        if raw.strip() and not ALL_DASHES.match(raw)]
        if unmapped_list:
            f.write("# --- Needs review (currently self-mapping) ---\n")
            for raw in unmapped_list:
                norm = normalize_raw(raw)
                count = counts[raw]
                f.write(f"# appears {count}x\n")
                f.write(f"{yaml.dump({raw: None}, default_flow_style=False, allow_unicode=True)}")

    # Write typo candidates report
    typo_path = STATS_DIR / "ingredient_typo_candidates.json"
    typo_data = [
        {"a": a, "b": b, "ratio": round(r, 3), "type": t}
        for a, b, r, t in typo_candidates
    ]
    with open(typo_path, "w", encoding="utf-8") as f:
        json.dump(typo_data, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"Scanned {len(counts)} unique raw ingredient strings")
    print(f"Auto-mapped: {len(mappings)} ({case_mappings} case, {plural_mappings} plural)")
    print(f"Needs review: {len(unmapped_list)}")
    print(f"Typo candidates: {len(typo_candidates)}")
    print(f"\nDraft written to: {draft_path}")
    print(f"Typo candidates: {typo_path}")


# ---------------------------------------------------------------------------
# Report mode
# ---------------------------------------------------------------------------

def report(recipe_dir):
    """Generate a comprehensive ingredient report."""
    taxonomy = load_taxonomy()
    mappings = load_mappings()
    counts, files = scan_all_ingredients(recipe_dir)

    if not taxonomy:
        print("WARNING: No taxonomy file found at", TAXONOMY_PATH)
        print("Run --bootstrap first, then create the taxonomy.\n")

    canonical_set, canonical_to_aisle, canonical_to_parent, see_also_map = \
        flatten_taxonomy(taxonomy)

    # Resolve all ingredients
    resolved = {}  # {raw: (canonical, method)}
    unmapped = []
    for raw in counts:
        norm = normalize_raw(raw)
        if ALL_DASHES.match(raw) or not raw.strip():
            continue
        canonical, method = resolve_ingredient(raw, mappings, canonical_set)
        resolved[raw] = (canonical, method)
        if method == "unknown":
            unmapped.append(raw)

    # Find orphaned mappings (in mappings file but not in any recipe)
    # Compare case-insensitively against both raw strings AND their normalized forms
    raw_lower_set = {r.lower() for r in counts}
    raw_lower_set |= {normalize_raw(r).lower() for r in counts}
    orphaned = []
    all_mappings = yaml.safe_load(MAPPINGS_PATH.read_text(encoding="utf-8")) or {} \
        if MAPPINGS_PATH.exists() else {}
    for raw_key in all_mappings:
        if raw_key.lower() not in raw_lower_set:
            orphaned.append(raw_key)

    # Find taxonomy gaps (canonical names in mappings not in taxonomy)
    taxonomy_gaps = []
    for raw, (canonical, method) in resolved.items():
        if method != "unknown" and canonical not in canonical_set and canonical_set:
            taxonomy_gaps.append(canonical)
    taxonomy_gaps = sorted(set(taxonomy_gaps))

    # Canonical frequency
    canonical_counts = defaultdict(int)
    for raw, (canonical, method) in resolved.items():
        if method != "unknown":
            canonical_counts[canonical] += counts[raw]

    # Typo candidates among unmapped
    if len(unmapped) > 1:
        typo_candidates = find_typo_candidates(
            {r: counts[r] for r in unmapped})
    else:
        typo_candidates = []

    # Write report
    STATS_DIR.mkdir(exist_ok=True)
    report_data = {
        "total_raw_strings": len([r for r in counts if r.strip() and not ALL_DASHES.match(r)]),
        "mapped": len(resolved) - len(unmapped),
        "unmapped": len(unmapped),
        "orphaned_mappings": len(orphaned),
        "taxonomy_gaps": len(taxonomy_gaps),
        "unmapped_strings": sorted(unmapped, key=str.lower),
        "orphaned_mapping_keys": sorted(orphaned, key=str.lower),
        "taxonomy_gap_names": taxonomy_gaps,
        "canonical_frequency": dict(sorted(
            canonical_counts.items(), key=lambda x: -x[1])),
    }
    report_path = STATS_DIR / "ingredients_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"Total raw ingredient strings: {report_data['total_raw_strings']}")
    print(f"Mapped: {report_data['mapped']}")
    print(f"Unmapped: {report_data['unmapped']}")
    print(f"Orphaned mappings: {report_data['orphaned_mappings']}")
    print(f"Taxonomy gaps: {report_data['taxonomy_gaps']}")

    if unmapped:
        print(f"\nUnmapped strings ({len(unmapped)}):")
        for raw in sorted(unmapped, key=str.lower)[:30]:
            print(f"  {counts[raw]:3d}x  {raw}")
        if len(unmapped) > 30:
            print(f"  ... and {len(unmapped) - 30} more")

    if orphaned:
        print(f"\nOrphaned mappings ({len(orphaned)}):")
        for key in sorted(orphaned, key=str.lower)[:20]:
            print(f"  {key}")

    if taxonomy_gaps:
        print(f"\nTaxonomy gaps ({len(taxonomy_gaps)}):")
        for name in taxonomy_gaps[:20]:
            print(f"  {name}")

    if typo_candidates:
        print(f"\nPossible typos among unmapped ({len(typo_candidates)}):")
        for a, b, ratio, typ in typo_candidates[:20]:
            print(f"  {a} <-> {b}  ({ratio:.2f}, {typ})")

    print(f"\nFull report: {report_path}")


# ---------------------------------------------------------------------------
# Validate mode
# ---------------------------------------------------------------------------

def validate(recipe_dir):
    """CI-friendly validation. Exit 1 if any issues found."""
    taxonomy = load_taxonomy()
    mappings = load_mappings()
    counts, _ = scan_all_ingredients(recipe_dir)

    if not taxonomy:
        print("ERROR: No taxonomy file at", TAXONOMY_PATH)
        sys.exit(1)

    if not mappings and not MAPPINGS_PATH.exists():
        print("ERROR: No mappings file at", MAPPINGS_PATH)
        sys.exit(1)

    canonical_set, canonical_to_aisle, _, _ = flatten_taxonomy(taxonomy)

    errors = []

    # Check for duplicate canonical names in taxonomy
    all_names = []

    def walk_for_dupes(members, aisle, parent=None):
        for m in members:
            if isinstance(m, str):
                all_names.append((m, aisle))
            else:
                all_names.append((m["name"], aisle))
                if "variations" in m:
                    walk_for_dupes(m["variations"], aisle, m["name"])

    for aisle_name, aisle_data in taxonomy.items():
        walk_for_dupes(aisle_data.get("members", []), aisle_name)

    from collections import Counter
    name_counts = Counter(n for n, a in all_names)
    for name, count in name_counts.items():
        if count > 1:
            locations = [a for nm, a in all_names if nm == name]
            errors.append(
                f"DUPLICATE: {name!r} appears {count}x in taxonomy "
                f"(aisles: {', '.join(locations)})"
            )

    # Check all raw strings are mapped
    for raw in counts:
        if not raw.strip() or ALL_DASHES.match(raw):
            continue
        canonical, method = resolve_ingredient(raw, mappings, canonical_set)
        if method == "unknown":
            errors.append(f"UNMAPPED: {raw!r} (appears {counts[raw]}x)")

    # Check all mapping targets exist in taxonomy
    all_mappings = yaml.safe_load(MAPPINGS_PATH.read_text(encoding="utf-8")) or {}
    for raw_key, canonical in all_mappings.items():
        if canonical is None:
            continue
        if canonical not in canonical_set:
            errors.append(f"TAXONOMY GAP: mapping {raw_key!r} -> {canonical!r} "
                         f"but {canonical!r} not in taxonomy")

    if errors:
        print(f"Validation FAILED with {len(errors)} error(s):\n")
        for err in sorted(errors):
            print(f"  {err}")
        sys.exit(1)
    else:
        print(f"Validation passed. {len(counts)} raw strings, "
              f"{len(canonical_set)} canonical ingredients in taxonomy.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ingredient taxonomy tools: bootstrap, report, validate."
    )
    parser.add_argument(
        "recipe_dir",
        help="Path to the recipe directory (e.g. _book_recipes/)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bootstrap", action="store_true",
                       help="Generate draft ingredient mappings")
    group.add_argument("--report", action="store_true",
                       help="Report on mapping/taxonomy coverage")
    group.add_argument("--validate", action="store_true",
                       help="Validate all ingredients are mapped and in taxonomy")

    args = parser.parse_args()

    if args.bootstrap:
        bootstrap(args.recipe_dir)
    elif args.report:
        report(args.recipe_dir)
    elif args.validate:
        validate(args.recipe_dir)


if __name__ == "__main__":
    main()
