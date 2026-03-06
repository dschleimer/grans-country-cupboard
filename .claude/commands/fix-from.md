# Fix `from:` Attributions

Run this command to audit and fix inconsistencies in the `from:` front-matter field across recipe files. The field records the original handwritten attribution — a person's name, family name, media outlet, or location. Typos and case variants accumulate over transcription sessions; this workflow normalizes them.

**Critical rule:** Never assume two similar-looking values are the same person. Always ask the user explicitly. Some family members have very similar names.

---

## Steps

### 1. Run the report

```bash
python _tools/fix_from.py _book_recipes/ --report
```

This prints all similarity clusters and writes `.recipe_stats/from_report.json`.

### 2. Review each cluster

Read the JSON report:

```bash
cat .recipe_stats/from_report.json
```

For each cluster in `clusters`, present it to the user clearly. For values with multiple recipes show the count; for values with only one recipe, show the filename instead:

> These `from:` values look similar — could they be the same person or source?
>
> - `"Elizabeth McGinley Barmeyer"` — 11 recipes
> - `"Elizabeth Mcginley Barmeyer"` — harpoon.md
> - `"Elizabeth mcGinley Barmeyer"` — eye_roast_beef.md
>
> Are these the same person? If yes, which spelling is canonical?

To find filenames for single-recipe values, use `grep -rl "^from: VALUE" _book_recipes/`.

Wait for the user's answer before proceeding to the next cluster. Do not batch questions.

**Guidance for common patterns:**

- **Case-only differences** (e.g. `McGinley` vs `Mcginley`) — almost certainly typos; still ask
- **Apparent typos** (e.g. `Garnd` vs `Grand`) — clearly typos; still confirm the canonical form
- **Short vs long form** (e.g. `Joby` vs `Joby McGinley`, `Mary Jane K` vs `Mary Jane Kowalchek`) — may be the same person or may be distinct; always ask
- **Name + location** (e.g. `Tom McGinley` vs `Tom McGinley - Honolulu`) — may be intentionally distinct (preserving attribution context); ask whether to merge or keep separate
- **Entirely different names** that happened to score similar — unlikely to be the same; mention it but lean toward keeping them separate unless the user confirms

After reviewing all clusters, also scan the full `all_values` list from the report for **unclustered values that look like standalone typos** — values that didn't pair with anything but contain obvious errors (transpositions, lowercase proper nouns, plausible misspellings). Present each to the user with its filename before adding to the mappings. Common patterns to look for:
- Transposition errors (e.g. `Grabdnother` → `Grandmother`)
- Lowercase first letters in proper names (e.g. `Mrs. gilbert` → `Mrs. Gilbert`)
- Plausible misspellings where the likely correct form is clear (e.g. a surname spelled two ways across different people in the same family)

Note: old-fashioned spellings (e.g. `Mable` for `Mabel`) are common in this 1975 handwritten cookbook and should be left as-is unless you're certain they're errors.

### 3. Collect confirmed mappings

For each cluster the user confirms as a single person/source, record the mapping of each non-canonical variant → the canonical form they specified.

Collect all confirmed mappings across all clusters before writing anything.

### 4. Update the mappings file

Load the existing mappings file (if it exists):

```bash
cat _tools/from_canonical.json
```

Merge the newly confirmed mappings into it. If the file doesn't exist, create it.

The format is a flat JSON object: `{ "variant": "canonical", ... }`

Write the updated file to `_tools/from_canonical.json`.

### 5. Preview changes

```bash
python _tools/fix_from.py _book_recipes/ --apply --dry-run
```

Show the user which files will be updated and what the changes are.

### 6. Apply

```bash
python _tools/fix_from.py _book_recipes/ --apply
```

### 7. Format changed files

```bash
git diff --name-only HEAD
python _tools/format_recipes.py $(git diff --name-only HEAD | grep '\.md$' | tr '\n' ' ')
```

### 8. Summarize and commit

Summarize the changes: how many clusters were reviewed, how many mappings were confirmed, how many files were updated. Ask the user if they want to commit.

Commit both `_tools/from_canonical.json` and any changed recipe files together.
