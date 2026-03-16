# Transcribe Recipes

Machine-transcribe untranscribed recipes from page scan images. Progress is tracked per recipe file in `.recipe_stats/transcribe_progress.json`. For fully automated unattended transcription of all recipes, use `bash _tools/run_transcribe.sh` from the terminal instead.

---

## Transcription Guidelines

**Interpret**, don't literally transcribe — make Gran's terse 1970s instructions accessible to modern cooks.

- **Ingredients**: 3-column table (`Ingredient | Amount | Notes`), capitalize ingredient names like existing recipes
- **Method**: numbered list (`1.` for each step), expand terse instructions into clear directions
- **Notes From Gran**: tips/variations visible in the handwriting (bullet list with `*`)
- **Modern Notes**: explain 1970s terms, suggest modern substitutes, note anything uncertain (bullet list with `*`)
- **Attribution**: if a name/location is visible after the recipe (e.g. "1950 Mrs Murray, Kimball W.Va."), capture it in the `from:` front-matter field
- Add `  - Machine Transcribed` to the categories list

**Reference** these transcribed recipes for tone and style:
- `_book_recipes/007/party_meat_balls.md`
- `_book_recipes/008/cheese_puffs.md`

**Skip** any recipe where you are not confident in the transcription — do not guess. Mark it skipped with a reason.

### Edge cases
- **Already-transcribed recipes on a page**: the batch only lists untranscribed files; ignore others
- **Recipes spanning two pages**: transcribe what's visible; note continuation in Modern Notes
- **Illegible sections**: skip the entire recipe rather than guessing

---

## Steps

### 1. Check status

```bash
python _tools/transcribe.py status
```

### 2. Get next batch

```bash
python _tools/transcribe.py next-batch -n 10
```

If the output is empty, all recipes have been transcribed — report "Done!" and stop.

The output format is one line per page: `NNN file1.md file2.md ...`

### 3. Transcribe each page

For each page in the batch:

1. **Read the page scan image**: `assets/enhanced/NNN.jpg`
2. **For each untranscribed recipe file listed for that page**:
   - Read the template file
   - Look at the page scan and find the recipe
   - If **confident** in the transcription:
     - Fill in the Ingredients table, Method, Notes From Gran, Modern Notes
     - Add `  - Machine Transcribed` to the categories list (keep existing status tags — `fix_categories.py` will clean them up)
     - If a `from:` attribution is visible, add it to the front matter
   - If **not confident** (illegible handwriting, ambiguous content):
     ```bash
     python _tools/transcribe.py skip <filepath> "reason for skipping"
     ```
3. **Mark completed recipes** (only the ones you actually transcribed):
   ```bash
   python _tools/transcribe.py mark-done <filepath1> <filepath2> ...
   ```

### 4. Fix categories

```bash
python _tools/fix_categories.py _book_recipes/
```

This removes `Needs Transcription`, infers categories, etc.

### 5. Format changed files

```bash
python _tools/format_recipes.py $(git diff --name-only HEAD | grep '\.md$' | tr '\n' ' ')
```

Skip if no files were changed.

### 6. Commit and summarize

If any files were changed, commit them:

```bash
git add _book_recipes/
git commit -m "[transcribe] machine transcribe pages NNN–NNN"
```

Replace `NNN–NNN` with the actual page range of files processed in this batch.

Then report:
- How many recipes were transcribed
- Any recipes skipped in this batch and why
- Current overall progress (`python _tools/transcribe.py status`)
