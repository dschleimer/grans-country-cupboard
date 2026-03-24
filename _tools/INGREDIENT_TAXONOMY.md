# Ingredient Taxonomy — Maintenance Guide

## Overview

The ingredient taxonomy maps raw ingredient strings from recipe tables to canonical names organized in a browsable hierarchy:

**Aisle** → **Ingredient** → **Variation**

- **Aisle**: Top-level browsing category (Dairy, Meat, Vegetables, etc.)
- **Ingredient**: Fundamental ingredient (Beef, Cheese, Onion)
- **Variation**: Specific variety, cut, or form (Ground Beef, Cheddar Cheese, Red Onion)

Variations can nest (Meat → Beef → Chuck → Ground Chuck).

## Files

| File | Purpose |
|------|---------|
| `_data/ingredient_taxonomy.yml` | Hierarchy: aisles, ingredients, variations, see_also |
| `_tools/ingredient_mappings.yml` | Maps raw recipe strings → canonical names |
| `_tools/fix_ingredients.py` | Bootstrap, report, and validate tool |

## How Ingredient Resolution Works

When the Jekyll plugin encounters a raw ingredient string in a recipe table:

1. Strip parentheticals: `Butter (melted)` → `Butter`
2. Title-case the result
3. Look up in mappings (case-insensitive) — **explicit mappings always win**
4. If not found, try stripping modifier prefixes (Melted, Grated, etc.) and look up remainder
5. If not found, try stripping modifier suffixes (`Cheese - Grated` → `Cheese`) and look up remainder
6. If still not found, use the title-cased string as-is (validation tool flags these)

Recipe text is never modified. The raw text stays as written; only the link target changes.

## Rules for Primary Parent vs. See-Also

The primary parent should be the **most fundamental/immutable property**. Priority:

1. **What animal/plant is it from?** → Primary parent (Beef, Pork, Chicken)
2. **What part of the animal?** → Variation of the animal (Chuck, Round, Breast)
3. **What preparation/form?** → Further variation OR `see_also` cross-reference

### When both a cut and preparation are present

Example: Ground Chuck

- **Primary parent** = Chuck (the cut), because the cut is an inherent property of the meat
- **see_also** = Ground Beef, because "ground" describes processing

**Rationale**: You can turn a Chuck Roast into Ground Chuck (change the preparation), but you can't turn Chuck into Round (the cut is fixed). The more permanent attribute is primary.

### See-also creates cross-references

When ingredient A has `see_also: [B]`, recipes using A also appear on B's page. This is bidirectional by convention — if Ground Chuck has `see_also: [Ground Beef]`, then Ground Beef should have `see_also: [Ground Chuck]`.

## How to Add a New Ingredient

1. **Add to taxonomy** (`_data/ingredient_taxonomy.yml`):
   - Find the right aisle
   - Add as ingredient or variation of an existing ingredient
   - Add `see_also` if it spans categories

2. **Add mapping** (`_tools/ingredient_mappings.yml`) if the raw text differs from the canonical name:
   - Synonyms, plural forms, brand names, accent variants

3. **Validate**: `python _tools/fix_ingredients.py _book_recipes/ --validate`

The planned `/fix-ingredients` skill will guide this process interactively.

## When to Create a New Aisle vs. Ingredient vs. Variation

- **New aisle**: When a group of ingredients is fundamentally different from all existing aisles (rare — the ~23 aisles cover most cases)
- **New ingredient**: When a food item is a distinct thing, not a variety of something already in the taxonomy (e.g., Quinoa is a new grain, not a rice variation)
- **New variation**: When the item is clearly a sub-type of an existing ingredient (e.g., Dark Chocolate is a variation of Chocolate)

## Brand Names

Brand names are kept as their own entries when they represent distinct products (Velveeta, Liederkranz). When a brand is interchangeable with a generic, it maps to the generic:

| Brand | Maps to |
|-------|---------|
| Crisco | Shortening |
| Mazola Oil | Cooking Oil |
| Creamettes | Macaroni |
| Karo Syrup | Corn Syrup |
| Duncan Hines Cake Mix | Cake Mix |
| Bisquick | Prepared Biscuit Mix |

The recipe text still displays the brand name; the link points to the generic page.

## Modifier Stripping

The authoritative list of modifier prefixes and suffixes is in `_tools/fix_ingredients.py` (`MODIFIER_PREFIXES` and `MODIFIER_SUFFIXES` constants). These preparation words are stripped during resolution when no explicit mapping exists.

### Prefix examples
`Melted Butter` → `Butter`, `Chopped Pecans` → `Pecans`

### Suffix examples
`Cheese - Grated` → `Cheese`, `Onion, Diced` → `Onion`

**Important**: Some modifiers are part of the ingredient's identity:
- "Ground Beef" — not just "modified Beef"
- "Dry Mustard" — different product from "Mustard"
- "Dried Beef" — preserved product, not just dried regular beef

These must have explicit mappings that take priority over modifier stripping.

## Running the Tools

```bash
# Full validation (CI-friendly, exits 1 on failure)
python _tools/fix_ingredients.py _book_recipes/ --validate

# Detailed report (unmapped, orphans, gaps, typo candidates)
python _tools/fix_ingredients.py _book_recipes/ --report

# Bootstrap (one-time, generates draft mappings)
python _tools/fix_ingredients.py _book_recipes/ --bootstrap
```
