# Fix Recipe Categories

Run this command after new recipes have been transcribed to clean up category metadata across all `_book_recipes/` files. It normalizes tag variants, corrects `Needs Transcription` status, and adds rule-based categories to stubs.

## Steps

### 1. Run the fix script

```bash
python _tools/fix_categories.py _book_recipes/ --report
```

Read the summary printed to stdout. Note:
- **Needs Transcription removed** — recipes that are now fully transcribed
- **Needs Front Matter removed** — recipes that now have enough category tags
- **Unverified tags stripped** — un-transcribed recipes that had stale category tags removed (expected after new transcriptions or first-time runs; these recipes are left with only status tags)
- **Gray areas** — recipes with ingredients but no method (or vice versa); review these manually

> **Policy:** Un-transcribed recipes (`Needs Transcription` present) are automatically kept tag-free — the script strips any non-status tags and skips category inference for them. Category tags must not be assigned until the recipe is actually read.

### 2. Review gray areas

For each file flagged as a gray area, read the file and decide:
- If the recipe is genuinely transcribed (e.g. uses non-standard section headers like `## Prepare in Advance`), verify its `Needs Transcription` tag is not present.
- If the recipe is genuinely incomplete, confirm `Needs Transcription` is present.

### 3. Manual AI-assisted pass for remaining `Needs Front Matter`

Read the report to identify any recipes that are:
- **Transcribed** (no `Needs Transcription` tag), AND
- **Still have** `Needs Front Matter` (< 3 proper category tags after the script ran)

For each such recipe, read the file and add appropriate categories using the canonical taxonomy below. Then remove `Needs Front Matter`.

**Canonical taxonomy:**
- **Course:** `Appetizers`, `Main`, `Side Dish`, `Soup`, `Salad`, `Dessert`, `Beverages`, `Bread`
  - `Beverages` = **non-alcoholic, non-water drinks only** (tea, coffee, lemonade, eggnog, etc.). Alcoholic drinks use `Alcohol` instead, never both.
- **Type:** `Casserole`, `Cookies`, `Cakes`, `Pie`, `Sandwich`, `Pasta`, `Sauce`, `Gravy`, `Dip`, `Spread`, `Condiment`, `Punch`, `Cocktail`, `Stew`, `Soufflé`, `Pate`, `Aspic`, `Meatballs`, `Cupcakes`
- **Drinks:** `Alcohol` (alcoholic drinks — mutually exclusive with `Beverages`), `Caffeinated` (coffee, tea, and other caffeinated drinks; applies alongside `Beverages` or `Alcohol`)
- **Protein:** `Beef`, `Pork`, `Chicken`, `Turkey`, `Seafood`, `Lamb`, `Veal`, `Elk`, `Rabbit`, `Venison`, `Duck`, `Eggs`
- **Dietary:** `Vegetarian` (no meat/seafood/eggs; dairy ok), `Ovo-Lacto Vegetarian` (no meat/seafood; eggs ok). Strictly vegetarian recipes carry **both** tags. Egg-containing meatless recipes carry only `Ovo-Lacto Vegetarian`.
- **Technique:** `Baked`, `Pan Fried`, `Deep Fried`, `Broiled`, `Grilled`, `Boiled`, `Roast`, `No Cook`, `Stovetop`, `Double Boiler`, `Sautéed`
- **Context:** `Party Food`, `Finger Food`, `Snacks`, `Breakfast`, `Christmas`, `Thanksgiving`, `Leftovers`
- **Serving:** `Chilled`, `Frozen`
- **Effort:** `All Day Recipe`, `Overnight Recipe`
- **Other:** `Notes`, `Vegetables`

A recipe needs ≥ 3 proper category tags (excluding `Needs Transcription` and `Needs Front Matter`) to have `Needs Front Matter` removed.

### 4. Spot-check recently transcribed recipes for thin category sets

When `Needs Transcription` is removed from a recipe, the script automatically adds `Needs Front Matter` if the recipe has no proper category tags. On the next fix run, rule-based inference will fire. However, some recipes that had proper tags before transcription may end up with only 1–2 tags after the transcription tag is removed.

Read the fix report and find all recipes where `removed_needs_transcription` is true. For each, check whether the resulting category list has a course-level tag (`Main`, `Side Dish`, `Soup`, `Salad`, `Dessert`, `Appetizers`, `Beverages`, `Bread`) and at least one other tag. If a recipe has fewer than 3 proper tags or is missing a course, read the file and add the appropriate categories from the canonical taxonomy in step 3.

### 5. Check for oxymoronic category pairs

```bash
python _tools/fix_categories.py _book_recipes/ --validate
```

The normal fix pass (step 1) already auto-adds `Ovo-Lacto Vegetarian` to clean `Vegetarian` recipes. Use `--validate` to find any remaining real conflicts requiring human judgment:

- **`Vegetarian` + animal protein tag or animal ingredient found**: read the recipe. If the animal ingredient is genuinely present, remove `Vegetarian`; add `Ovo-Lacto Vegetarian` if the recipe otherwise qualifies (no meat/seafood). If the match is a false positive (e.g. "egg substitute"), leave `Vegetarian` unchanged.
- **`Ovo-Lacto Vegetarian` + meat/seafood tag or ingredient**: remove the incorrect tag — read the recipe to decide whether the protein tag or the dietary tag is wrong.

Re-run `--validate` until it reports zero conflicts before proceeding.

### 6. Verify with recipe_stats.py

```bash
python _tools/recipe_stats.py _book_recipes/
```

Inspect `.recipe_stats/categories_counts.json` and confirm:
- `Needs Transcription` count matches expected untranscribed recipes
- `Needs Front Matter` count is near zero (only untranscribed stubs)
- No old variant tags remain (e.g. `Mains`, `Appetizer`, `Desserts`)

### 7. Format changed files

```bash
# Get list of changed files from git
git diff --name-only HEAD

# Format them
python _tools/format_recipes.py $(git diff --name-only HEAD | grep '\.md$' | tr '\n' ' ')
```

### 8. Summarize and commit

Summarize the changes made and ask the user if they want to commit.
