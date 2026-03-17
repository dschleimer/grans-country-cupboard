#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_categories.py

Fix up recipe categories in _book_recipes/:
1. Normalize tag variants to canonical forms (e.g. "Mains" → "Main")
2. Correct Needs Transcription status based on content detection
3. Add rule-based categories to Needs Front Matter recipes
4. Remove Needs Front Matter when recipe has 4+ proper category tags
5. Detect oxymoronic category pairs (Vegetarian + animal ingredients)
6. Optionally write a JSON report

Usage:
    python _tools/fix_categories.py _book_recipes/ [--dry-run] [--report]
    python _tools/fix_categories.py _book_recipes/ --validate
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Tag normalization map  (old variant → canonical)
# ---------------------------------------------------------------------------
TAG_REPLACEMENTS = {
    "Appetizer": "Appetizers",
    "Mains": "Main",
    "Desserts": "Dessert",
    "Finger Foods": "Finger Food",
    "Party Foods": "Party Food",
    "Spreads": "Spread",
    "Breakfast foods": "Breakfast",
    "Notes from Gran": "Notes",
    "Meat Balls": "Meatballs",
    "Double Boiled": "Double Boiler",
    "Sauted": "Sautéed",
    "Overnigth Recipe": "Overnight Recipe",
    "Sandwiches": "Sandwich",
    "Cup Cakes": "Cupcakes",
    "Snack": "Snacks",
    "Pan Cooked": "Pan Fried",
    "Oven": "Baked",
    "Grill": "Grilled",
    "Uncooked": "No Cook",
    "Barbeque": "Grilled",
}

# Tags to drop entirely (no canonical replacement)
TAGS_TO_REMOVE = {"Fried Foods", "Served Hot"}

# Status tags (never treated as "proper" category tags for the threshold check)
STATUS_TAGS = {"Needs Transcription", "Needs Front Matter", "Machine Transcribed", "Human Transcribed"}

# Minimum number of proper (non-status) category tags a transcribed recipe must
# have before Needs Front Matter is cleared.
MIN_PROPER_TAGS = 4

# Notes entries are not recipes — exempt from the MIN_PROPER_TAGS threshold.
# They only need the "Notes" tag to be considered complete.
NOTES_EXEMPT = True

# Canonical course-level tags (used to check if a recipe has a course)
CANONICAL_COURSE_TAGS = {
    "Appetizers", "Main", "Side Dish", "Soup", "Salad",
    "Dessert", "Beverages", "Bread",
}

# ---------------------------------------------------------------------------
# Conflict detection constants
# ---------------------------------------------------------------------------

# Animal protein tags that conflict with all vegetarian designations
_MEAT_PROTEIN_TAGS = {
    "Beef", "Pork", "Chicken", "Turkey", "Seafood",
    "Lamb", "Veal", "Elk", "Rabbit", "Venison", "Duck",
}
# Tags incompatible with strict Vegetarian (includes Eggs)
VEGETARIAN_CONFLICTS = _MEAT_PROTEIN_TAGS | {"Eggs"}
# Tags incompatible with Ovo-Lacto Vegetarian (excludes Eggs)
OVO_LACTO_CONFLICTS = _MEAT_PROTEIN_TAGS

# ---------------------------------------------------------------------------
# File parsing / writing
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


def rewrite_categories_in_fm(fm_lines, new_categories, indent="  "):
    """
    Replace the `categories:` block in fm_lines with new_categories.
    If no `categories:` key exists, append it at the end.
    Returns a new list of lines.
    """
    cat_start = None
    cat_end = None

    for i, line in enumerate(fm_lines):
        if re.match(r'^categories\s*:', line):
            cat_start = i
            j = i + 1
            while j < len(fm_lines) and re.match(r'^\s*-', fm_lines[j]):
                j += 1
            cat_end = j
            break

    if not new_categories:
        new_block = ["categories: []\n"]
    else:
        new_block = ["categories:\n"] + [f"{indent}- {tag}\n" for tag in new_categories]

    if cat_start is not None:
        return list(fm_lines[:cat_start]) + new_block + list(fm_lines[cat_end:])
    else:
        return list(fm_lines) + new_block


def write_recipe(path, fm_lines, body_lines, new_categories):
    content = "---\n" + "".join(rewrite_categories_in_fm(fm_lines, new_categories)) + "---\n" + "".join(body_lines)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Transcription detection
# ---------------------------------------------------------------------------

_ALL_DASHES = re.compile(r'^\s*-+\s*$')


def _extract_section_lines(body_text, section_name):
    """Return lines belonging to the named ## section."""
    lines = body_text.splitlines()
    pattern = re.compile(rf'^##\s+{re.escape(section_name)}\s*$')
    in_sec = False
    result = []
    for line in lines:
        if pattern.match(line):
            in_sec = True
            continue
        if in_sec and re.match(r'^##\s+', line):
            break
        if in_sec:
            result.append(line)
    return result


def count_ingredient_rows(body_text):
    """Count non-header, non-separator table rows in the Ingredients section."""
    count = 0
    for line in _extract_section_lines(body_text, "Ingredients"):
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        if len(cells) < 2:
            continue
        first = cells[1].strip()
        if not first or first.lower() == "ingredient" or _ALL_DASHES.match(first):
            continue
        count += 1
    return count


def count_method_steps(body_text):
    """Count numbered list items in the Method section."""
    count = 0
    for line in _extract_section_lines(body_text, "Method"):
        if re.match(r'^\d+[.)]\s', line):
            count += 1
    return count


def detect_transcription_status(body_text):
    """
    Returns one of:
        'transcribed'              – has ≥1 ingredient row AND ≥1 method step
        'untranscribed'            – missing both
        'gray_ingredients_only'   – has ingredients but no numbered method steps
        'gray_method_only'        – has method steps but no ingredient rows
    """
    ing = count_ingredient_rows(body_text)
    mth = count_method_steps(body_text)

    if ing >= 1 and mth >= 1:
        return "transcribed"
    if ing == 0 and mth == 0:
        return "untranscribed"
    if ing >= 1:
        return "gray_ingredients_only"
    return "gray_method_only"


# ---------------------------------------------------------------------------
# Tag normalization
# ---------------------------------------------------------------------------

def normalize_tags(categories):
    """Apply replacement map, deduplicate, drop removed tags."""
    result = []
    seen = set()
    for tag in categories:
        if tag in TAGS_TO_REMOVE:
            continue
        canonical = TAG_REPLACEMENTS.get(tag, tag)
        if canonical not in seen:
            result.append(canonical)
            seen.add(canonical)
    # Enforce Beverages/Alcohol mutual exclusivity: alcoholic drinks must not
    # carry Beverages (which is reserved for non-alcoholic drinks).
    if "Alcohol" in seen:
        result = [t for t in result if t != "Beverages"]
        seen.discard("Beverages")
    # Add protein umbrella tags: every recipe with a specific protein sub-type
    # gets the appropriate coarse umbrella tag.
    _POULTRY_SUBTYPES = {"Chicken", "Turkey", "Duck"}
    _MEAT_SUBTYPES = {"Beef", "Pork", "Lamb", "Veal", "Elk", "Rabbit", "Venison"}
    _SEAFOOD_SUBTYPES = {"Shrimp", "Crab", "Oysters", "Lobster", "Fish", "Clams"}
    if seen & _POULTRY_SUBTYPES and "Poultry" not in seen:
        result.append("Poultry")
        seen.add("Poultry")
    if seen & _MEAT_SUBTYPES and "Meat" not in seen:
        result.append("Meat")
        seen.add("Meat")
    if seen & _SEAFOOD_SUBTYPES and "Seafood" not in seen:
        result.append("Seafood")
        seen.add("Seafood")
    return result


# ---------------------------------------------------------------------------
# Rule-based categorization (for Needs Front Matter recipes)
# ---------------------------------------------------------------------------

# (filename stem pattern, tags to add)
_FILENAME_RULES = [
    (r'cup_?cake|cupcake',                       ["Dessert", "Cupcakes"]),
    (r'(?:^|_)cake$|(?:^|_)cakes$|torte',        ["Dessert", "Cakes"]),
    (r'cookie|brownie|bar_cookie',               ["Dessert", "Cookies"]),
    (r'pie|cobbler|(?:^|_)tart$|_crisp$',                    ["Dessert", "Pie"]),
    (r'bread|muffin|biscuit|roll|bun|loaf',      ["Bread"]),
    (r'soup|chowder|bisque|gazpacho|potage',      ["Soup"]),
    (r'stew|ragout|ragù',                        ["Stew"]),
    (r'salad',                                   ["Salad"]),
    (r'sandwich|sub|hoagie|burger|panini',       ["Sandwich"]),
    (r'punch',                                   ["Punch"]),
    (r'cocktail|daiquiri|julep|colada|martini',  ["Cocktail"]),
    (r'eggnog|lemonade',                         ["Beverages"]),
    (r'(?:^|_)coffee$|(?:^|_)tea$',             ["Beverages", "Caffeinated"]),
    (r'iced',                                    ["Chilled"]),
    (r'\bdip\b|_dip$|^dip_',                     ["Dip"]),
    (r'spread',                                  ["Spread"]),
    (r'gravy',                                   ["Gravy", "Side Dish"]),
    (r'sauce',                                   ["Sauce", "Condiment"]),
    (r'coleslaw|slaw',                           ["Salad", "Chilled"]),
    (r'cheese.*ball|ball.*cheese',               ["Appetizers", "Finger Food"]),
    (r'applejack|whiskey|whisky|bourbon|scotch|vodka|brandy', ["Cocktail"]),
    (r'scrambl',                                 ["Breakfast", "Eggs"]),
    (r'omelet|omelette',                         ["Breakfast", "Eggs"]),
    (r'fritter',                                 ["Finger Food", "Snacks"]),
    (r'shrimp',                                  ["Shrimp"]),
    (r'crab',                                    ["Crab"]),
    (r'oyster',                                  ["Oysters"]),
    (r'lobster',                                 ["Lobster"]),
    (r'fish',                                    ["Fish"]),
    (r'casserole|gratin|au_gratin|scalloped',    ["Casserole"]),
    (r'pasta|spaghetti|macaroni|noodle|lasagna', ["Pasta"]),
    (r'pudding|custard',                         ["Dessert"]),
    (r'aspic',                                    ["Aspic", "Chilled"]),
    (r'gelatin|jello|mold',                       ["Chilled"]),
    (r'ice_cream|sherbet|sorbet',                ["Dessert", "Frozen"]),
    (r'relish|chutney|pickle|jam|jelly|marmalade|marmelade|preserv',["Condiment"]),
    (r'pate|terrine',                            ["Pate"]),
    (r'fudge|candy|toffee|taffy|brittle|praline',["Dessert"]),
    (r'waffle|pancake|griddle_cake|french_toast', ["Breakfast"]),
    (r'omelet|omelette',                         ["Breakfast"]),
    (r'canape|appetizer|hors',                   ["Appetizers"]),
    (r'finger|snack|nibble|bite',                ["Finger Food"]),
    (r'frosting|icing|filling',                  ["Dessert", "Cakes"]),
    (r'sherbert',                                ["Dessert", "Frozen"]),
    (r'dumpling',                                ["Side Dish", "Boiled"]),
    (r'wine',                                    ["Alcohol"]),
    (r'(?:^|_)freezing$|(?:^|_)frozen_',         ["Frozen"]),
    (r'(?:^|_)canned$|(?:^|_)canning$',          ["Condiment"]),
    (r'shortcake',                               ["Dessert"]),
    (r'cream_puff',                              ["Dessert"]),
    (r'johnny_cake',                             ["Bread"]),
    (r'(?:^|_)ice$',                             ["Dessert", "Frozen"]),
    (r'parfait|mousse(?!.*ham)',                  ["Dessert", "Chilled"]),
    (r'fluff',                                   ["Dessert", "Chilled"]),
    (r'tapioca',                                 ["Dessert"]),
    (r'snap|hermit|cry_bab',                     ["Cookies"]),
    (r'squares|bars(?:$|_)',                      ["Cookies"]),
]

# (pattern against ingredient text, tag)
_PROTEIN_RULES = [
    (r'\bchicken\b',                                                              "Chicken"),
    (r'\bturkey\b',                                                               "Turkey"),
    (r'\b(beef|ground\s+chuck|ground\s+beef|sirloin|brisket|flank)\b',           "Beef"),
    (r'\b(pork|ham|bacon|sausage|prosciutto|salami|pepperoni|pig)\b',            "Pork"),
    (r'\blamb\b|\bmutton\b',                                                      "Lamb"),
    (r'\bveal\b',                                                                 "Veal"),
    (r'\belk\b',                                                                  "Elk"),
    (r'\brabbit\b',                                                               "Rabbit"),
    (r'\bvenison\b',                                                              "Venison"),
    (r'\bduck\b',                                                                 "Duck"),
    (r'\b(shrimp|crab|lobster|clam|oyster|scallop|tuna|salmon|cod|flounder'
     r'|fish|seafood|anchov|halibut|mahi|swordfish)\b',                           "Seafood"),
]

# Egg pattern for content-level Vegetarian conflict checks (eggs aren't in _PROTEIN_RULES
# because they're allowed for Ovo-Lacto Vegetarian but not strict Vegetarian).
_EGG_PATTERN = re.compile(r'\begg(s)?\b', re.IGNORECASE)

# Gelatin pattern: commercial gelatin and Jello are derived from animal collagen,
# disqualifying both Vegetarian and Ovo-Lacto Vegetarian.
_GELATIN_PATTERN = re.compile(r'\b(gelatin|jell-?o)\b', re.IGNORECASE)

# All animal ingredient patterns: meat/seafood + eggs + gelatin (used for Vegetarian content check).
_ANIMAL_INGREDIENT_PATTERNS = [
    (re.compile(p, re.IGNORECASE), label) for p, label in _PROTEIN_RULES
] + [(_EGG_PATTERN, "Eggs"), (_GELATIN_PATTERN, "Gelatin")]

# (pattern against method text, tag)
_TECHNIQUE_RULES = [
    (r'\bdeep[\s-]?fr(y|ied|ying)\b',                                            "Deep Fried"),
    (r'\bbak(e|ed|ing)(?!\s+(?:powder|soda))\b|\boven\b|\bpreheat\b',             "Baked"),
    (r'\bbroil(ed|ing)?\b',                                                       "Broiled"),
    (r'\bgrill(ed|ing)?\b|\bbbq\b|\bbarbeque\b',                                 "Grilled"),
    (r'\broast(ed|ing)?\b',                                                       "Roast"),
    (r'\bboil(ed|ing)?\b|\bsimmer(ed|ing)?\b',                                  "Boiled"),
    (r'\bsaut[eé](ed|ing)?\b',                                                   "Sautéed"),
    (r'\bdouble\s+boiler\b',                                                      "Double Boiler"),
    # Pan Fried: mention of fry/skillet but only if Deep Fried not matched
    (r'\b(pan[\s-]?fr(y|ied|ying)|skillet|fry|frying)\b',                        "Pan Fried"),
]

# (pattern against full body, tag)
_CONTEXT_RULES = [
    (r'\bchristmas\b|\bholiday\b|\bxmas\b',      "Christmas"),
    (r'\bthanksgiving\b',                         "Thanksgiving"),
    (r'\bleftover\b',                             "Leftovers"),
    (r'\bovernight\b',                            "Overnight Recipe"),
    (r'\ball[\s-]day\b|\bslow[\s-]cook\b',        "All Day Recipe"),
]


def detect_conflicts(path, categories, body_text):
    """
    Check for oxymoronic category combinations.

    Returns a list of human-readable conflict strings (empty = clean).
    An auto-fixable issue is prefixed with "AUTO: ".
    """
    cats = set(categories)
    conflicts = []

    ingredient_text = "\n".join(_extract_section_lines(body_text, "Ingredients"))

    has_veg = "Vegetarian" in cats
    has_ovo = "Ovo-Lacto Vegetarian" in cats

    if has_veg:
        # Tag-level conflicts
        for tag in VEGETARIAN_CONFLICTS & cats:
            conflicts.append(f"Vegetarian + {tag} tag")
        # Content-level conflicts
        for pattern, label in _ANIMAL_INGREDIENT_PATTERNS:
            if pattern.search(ingredient_text):
                conflicts.append(f"Vegetarian + '{label}' in ingredients")
        # Missing Ovo-Lacto Vegetarian (auto-fixable only when no other conflicts)
        if not has_ovo and not conflicts:
            conflicts.append("AUTO: Vegetarian without Ovo-Lacto Vegetarian (should carry both)")

    if has_ovo:
        # Tag-level conflicts (meat only, not eggs)
        for tag in OVO_LACTO_CONFLICTS & cats:
            conflicts.append(f"Ovo-Lacto Vegetarian + {tag} tag")
        # Content-level conflicts (meat only, not eggs)
        for pattern, label in [(re.compile(p, re.IGNORECASE), lbl) for p, lbl in _PROTEIN_RULES]:
            if pattern.search(ingredient_text):
                conflicts.append(f"Ovo-Lacto Vegetarian + '{label}' in ingredients")
        # Gelatin disqualifies Ovo-Lacto Vegetarian too (animal-derived collagen)
        if _GELATIN_PATTERN.search(ingredient_text):
            conflicts.append("Ovo-Lacto Vegetarian + 'Gelatin' in ingredients")

    return conflicts


# When a recipe already carries one of these tags, infer the listed additional
# tags.  Applied after all filename/ingredient/technique rules so that newly
# inferred tags are also eligible as source tags.
_TAG_IMPLIES_TAGS = [
    ("Salad Dressing", ["Salad", "Condiment"]),
    ("Pate",           ["Appetizers", "Chilled"]),
    ("Jello Salad",    ["Salad", "Chilled"]),
    ("Gelatin Dessert",["Dessert", "Chilled"]),
    ("Soufflé",        ["Side Dish"]),
    ("Boiled Eggs",    ["Eggs", "Breakfast"]),
    ("Gravy",          ["Side Dish"]),
    ("Cocktail",       ["Alcohol"]),
    ("Cookies",        ["Dessert"]),
    ("Punch",          ["Beverages"]),
    # Protein sub-type → umbrella (mirrors normalize_tags umbrella logic for NFM inference)
    ("Chicken",        ["Poultry"]),
    ("Turkey",         ["Poultry"]),
    ("Duck",           ["Poultry"]),
    ("Beef",           ["Meat"]),
    ("Pork",           ["Meat"]),
    ("Lamb",           ["Meat"]),
    ("Veal",           ["Meat"]),
    ("Elk",            ["Meat"]),
    ("Rabbit",         ["Meat"]),
    ("Venison",        ["Meat"]),
    ("Shrimp",         ["Seafood"]),
    ("Crab",           ["Seafood"]),
    ("Oysters",        ["Seafood"]),
    ("Lobster",        ["Seafood"]),
    ("Fish",           ["Seafood"]),
    ("Clams",          ["Seafood"]),
]


def infer_categories(filename_stem, body_text, existing_categories):
    """
    Return list of additional tags to add (not already in existing_categories).
    Conservative: only high-confidence, unambiguous inferences.
    """
    existing = set(existing_categories)
    additions = []

    def add(tag):
        if tag not in existing and tag not in additions:
            additions.append(tag)

    stem = filename_stem.lower()
    ingredient_text = "\n".join(_extract_section_lines(body_text, "Ingredients"))
    method_text = "\n".join(_extract_section_lines(body_text, "Method"))

    # Filename-based course/type rules
    for pattern, tags in _FILENAME_RULES:
        if re.search(pattern, stem):
            for t in tags:
                add(t)

    # Protein tags from ingredient list — skip for vegetarian-tagged recipes to
    # avoid creating tag-level conflicts.
    if "Vegetarian" not in existing and "Ovo-Lacto Vegetarian" not in existing:
        for pattern, tag in _PROTEIN_RULES:
            if re.search(pattern, ingredient_text, re.IGNORECASE):
                add(tag)

    # Technique tags from method text
    matched_techniques = []
    for pattern, tag in _TECHNIQUE_RULES:
        if re.search(pattern, method_text, re.IGNORECASE):
            matched_techniques.append(tag)

    # If Deep Fried matched, skip Pan Fried to avoid redundancy
    if "Deep Fried" in matched_techniques and "Pan Fried" in matched_techniques:
        matched_techniques.remove("Pan Fried")

    for tag in matched_techniques:
        add(tag)

    # Context tags from full body
    for pattern, tag in _CONTEXT_RULES:
        if re.search(pattern, body_text, re.IGNORECASE):
            add(tag)

    # Tag-implies-tag: some type tags imply course or additional tags.
    # Re-check combined set so newly inferred tags also act as sources.
    all_so_far = existing | set(additions)
    for source_tag, implied_tags in _TAG_IMPLIES_TAGS:
        if source_tag in all_so_far:
            for t in implied_tags:
                add(t)

    # Egg-based dietary inference: if no meat/seafood proteins are present but
    # eggs appear in the ingredient list, this recipe is at least Ovo-Lacto
    # Vegetarian.  Safe to infer because we only reach this when no animal
    # protein tag was added or already existed.
    all_so_far = existing | set(additions)
    has_meat = bool(_MEAT_PROTEIN_TAGS & all_so_far)
    if (not has_meat
            and _EGG_PATTERN.search(ingredient_text)
            and "Vegetarian" not in all_so_far
            and "Ovo-Lacto Vegetarian" not in all_so_far):
        add("Ovo-Lacto Vegetarian")

    return additions


def count_proper_tags(categories):
    """Count non-status tags."""
    return sum(1 for t in categories if t not in STATUS_TAGS)


# ---------------------------------------------------------------------------
# Main file processing
# ---------------------------------------------------------------------------

def process_file(path, dry_run=False):
    """
    Process one recipe file. Returns a change record dict or None if unchanged.
    """
    fm_dict, fm_lines, body_lines = parse_recipe(path)
    if fm_dict is None:
        return None

    body_text = "".join(body_lines)
    categories = [str(c) for c in (fm_dict.get("categories") or [])]
    original = list(categories)
    changes = {}

    # --- 1. Normalize tag variants ---
    normalized = normalize_tags(categories)
    if normalized != categories:
        removed = [t for t in categories if t not in normalized]
        added = [t for t in normalized if t not in categories]
        changes["normalized"] = {"removed": removed, "added": added}
        categories = normalized

    # --- 2. Transcription status correction ---
    status = detect_transcription_status(body_text)
    has_nt = "Needs Transcription" in categories

    has_nfm = "Needs Front Matter" in categories

    if status == "transcribed" and has_nt:
        categories.remove("Needs Transcription")
        changes["removed_needs_transcription"] = True
        # If no proper tags remain, add NFM so next pass infers categories
        if count_proper_tags(categories) == 0 and "Needs Front Matter" not in categories:
            categories.append("Needs Front Matter")
            changes["added_needs_front_matter"] = True
    elif status == "untranscribed" and not has_nt and not has_nfm and "Notes" not in categories:
        # Don't add Needs Transcription to Needs Front Matter files (acknowledged stubs)
        # or Notes files (glossary/info entries that have no recipe structure by design).
        categories.insert(0, "Needs Transcription")
        changes["added_needs_transcription"] = True
    elif status in ("gray_ingredients_only", "gray_method_only"):
        changes["gray_area"] = status
        # Do not auto-change; flag only

    # --- 2b. Strip unverified tags from confirmed un-transcribed recipes ---
    if "Needs Transcription" in categories:
        stripped = [t for t in categories if t not in STATUS_TAGS]
        if stripped:
            categories = [t for t in categories if t in STATUS_TAGS]
            changes["stripped_unverified"] = stripped

    # --- 2c. Re-flag under-categorized transcribed recipes ---
    # Raise Needs Front Matter on any transcribed recipe that has fewer than
    # MIN_PROPER_TAGS proper tags, regardless of whether it previously cleared
    # the threshold (e.g. after the threshold is raised).
    is_notes = "Notes" in categories
    if (status in ("transcribed", "gray_method_only")
            and "Needs Transcription" not in categories
            and "Needs Front Matter" not in categories
            and not is_notes
            and count_proper_tags(categories) < MIN_PROPER_TAGS):
        categories.append("Needs Front Matter")
        changes["added_needs_front_matter"] = True

    # --- 3. Rule-based categorization for Needs Front Matter ---
    if "Needs Front Matter" in categories and "Needs Transcription" not in categories:
        inferred = infer_categories(path.stem, body_text, categories)
        if inferred:
            categories.extend(inferred)
            changes["inferred_categories"] = inferred

        # Remove Needs Front Matter once ≥MIN_PROPER_TAGS proper tags exist,
        # or immediately for Notes entries (which are exempt from the threshold).
        if "Needs Transcription" not in categories and (
                count_proper_tags(categories) >= MIN_PROPER_TAGS or is_notes):
            categories.remove("Needs Front Matter")
            changes["removed_needs_front_matter"] = True

    # --- 4. Conflict detection ---
    found_conflicts = detect_conflicts(path, categories, body_text)
    auto_conflicts = [c for c in found_conflicts if c.startswith("AUTO: ")]
    real_conflicts = [c for c in found_conflicts if not c.startswith("AUTO: ")]

    # Auto-fix: add Ovo-Lacto Vegetarian to clean Vegetarian recipes
    for c in auto_conflicts:
        if "Vegetarian without Ovo-Lacto Vegetarian" in c:
            categories.append("Ovo-Lacto Vegetarian")
            changes["ovo_lacto_added"] = True

    if real_conflicts:
        changes["conflicts"] = real_conflicts

    if categories == original and not changes.get("conflicts"):
        return None

    if not dry_run and categories != original:
        write_recipe(path, fm_lines, body_lines, categories)

    return {
        "file": str(path),
        "original": original,
        "updated": categories,
        "changes": changes,
    }


def validate_mode(all_paths):
    """Scan all recipes for conflicts without making any changes. Returns exit code."""
    all_conflicts = []
    errors = []

    for path in all_paths:
        try:
            fm_dict, fm_lines, body_lines = parse_recipe(path)
        except Exception as exc:
            errors.append({"file": str(path), "error": str(exc)})
            continue
        if fm_dict is None:
            continue

        body_text = "".join(body_lines)
        categories = [str(c) for c in (fm_dict.get("categories") or [])]
        conflicts = detect_conflicts(path, categories, body_text)
        real = [c for c in conflicts if not c.startswith("AUTO: ")]
        auto = [c for c in conflicts if c.startswith("AUTO: ")]
        if real or auto:
            all_conflicts.append({
                "file": str(path),
                "categories": categories,
                "conflicts": real,
                "auto_fixable": [c[len("AUTO: "):] for c in auto],
            })

    print(f"\nValidation results: {len(all_conflicts)} recipe(s) with issues\n")
    has_real = False
    for entry in all_conflicts:
        if entry["conflicts"]:
            has_real = True
            print(f"  CONFLICT  {entry['file']}")
            for c in entry["conflicts"]:
                print(f"            ! {c}")
        if entry["auto_fixable"]:
            print(f"  AUTO-FIX  {entry['file']}")
            for c in entry["auto_fixable"]:
                print(f"            + {c}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e['file']}: {e['error']}", file=sys.stderr)

    report_dir = Path.cwd() / ".recipe_stats"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "validate_report.json"
    report_path.write_text(
        json.dumps({"conflicts": all_conflicts, "errors": errors}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nReport written to {report_path}")

    return 1 if has_real else 0


def main():
    parser = argparse.ArgumentParser(description="Fix recipe categories in _book_recipes/")
    parser.add_argument("directories", nargs="+", help="Directories to scan")
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't write files")
    parser.add_argument("--report", action="store_true", help="Write .recipe_stats/fix_report.json")
    parser.add_argument("--validate", action="store_true",
                        help="Check for oxymoronic category pairs without making changes")
    args = parser.parse_args()

    all_paths = []
    for d in args.directories:
        all_paths.extend(sorted(Path(d).resolve().rglob("*.md")))

    if args.validate:
        sys.exit(validate_mode(all_paths))

    results = []
    gray_areas = []
    errors = []
    stats = {
        "files_changed": 0,
        "needs_transcription_added": 0,
        "needs_transcription_removed": 0,
        "needs_front_matter_removed": 0,
        "tags_normalized": 0,
        "inferred_category_files": 0,
        "gray_areas": 0,
        "conflicts_detected": 0,
        "ovo_lacto_added": 0,
        "stripped_unverified_files": 0,
        "added_needs_front_matter": 0,
    }

    for path in all_paths:
        try:
            result = process_file(path, dry_run=args.dry_run)
        except Exception as exc:
            errors.append({"file": str(path), "error": str(exc)})
            continue

        if result is None:
            continue

        results.append(result)
        stats["files_changed"] += 1
        c = result["changes"]
        if c.get("added_needs_transcription"):
            stats["needs_transcription_added"] += 1
        if c.get("removed_needs_transcription"):
            stats["needs_transcription_removed"] += 1
        if c.get("removed_needs_front_matter"):
            stats["needs_front_matter_removed"] += 1
        if c.get("normalized"):
            stats["tags_normalized"] += 1
        if c.get("inferred_categories"):
            stats["inferred_category_files"] += 1
        if c.get("gray_area"):
            stats["gray_areas"] += 1
            gray_areas.append({
                "file": result["file"],
                "status": c["gray_area"],
                "categories": result["original"],
            })
        if c.get("conflicts"):
            stats["conflicts_detected"] += 1
            print(f"\n  WARNING — conflicts in {result['file']}:")
            for conflict in c["conflicts"]:
                print(f"    ! {conflict}")
        if c.get("ovo_lacto_added"):
            stats["ovo_lacto_added"] += 1
        if c.get("stripped_unverified"):
            stats["stripped_unverified_files"] += 1
        if c.get("added_needs_front_matter"):
            stats["added_needs_front_matter"] += 1

    # --- Print summary ---
    print(f"\nSummary ({'dry run' if args.dry_run else 'applied'}):")
    print(f"  Files changed:                {stats['files_changed']}")
    print(f"  Needs Transcription added:    {stats['needs_transcription_added']}")
    print(f"  Needs Transcription removed:  {stats['needs_transcription_removed']}")
    print(f"  Needs Front Matter removed:   {stats['needs_front_matter_removed']}")
    print(f"  Tag variants normalized:      {stats['tags_normalized']}")
    print(f"  Categories inferred:          {stats['inferred_category_files']}")
    print(f"  Gray areas flagged:           {stats['gray_areas']}")
    print(f"  Conflicts detected:           {stats['conflicts_detected']}")
    print(f"  Ovo-Lacto Vegetarian added:   {stats['ovo_lacto_added']}")
    print(f"  Unverified tags stripped:     {stats['stripped_unverified_files']}")
    print(f"  Needs Front Matter added:     {stats['added_needs_front_matter']}")

    if gray_areas:
        print("\nGray areas (manual review needed):")
        for g in gray_areas:
            print(f"  [{g['status']}] {g['file']}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e['file']}: {e['error']}", file=sys.stderr)

    if args.report:
        report = {
            "stats": stats,
            "changes": results,
            "gray_areas": gray_areas,
            "errors": errors,
        }
        report_dir = Path.cwd() / ".recipe_stats"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "fix_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport written to {report_path}")

    if args.dry_run:
        print("\n(Dry run — no files were modified.)")


if __name__ == "__main__":
    main()
