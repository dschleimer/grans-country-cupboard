# Proofread Recipes

Run this command to proofread a single batch of transcribed recipes for typos and spelling errors. For fully automated unattended proofreading of all recipes, use `bash _tools/run_proofread.sh` from the terminal instead.

Progress is tracked in `.recipe_stats/proofread_progress.json` and shared between this skill and the shell script — you can mix both as needed.

---

## Scope

**Check these sections:**
- H1 recipe title
- Ingredient names (first column of the ingredients table)
- Notes column in the ingredients table
- Method steps (numbered list)
- Notes From Gran
- Modern Notes

**Out of scope** (handled by other tools):
- YAML front-matter → `/fix-categories`, `/fix-from`
- Table alignment and amount formatting → `format_recipes.py`

---

## Proofreading rules

**Fix:**
- Clear misspellings from transcription: dropped/transposed/doubled letters
- Repeated words ("the the", "and and")
- Obvious incomplete words

**Do NOT change:**
- Gran's voice, phrasing, or style in Notes From Gran — preserve original wording even if grammatically loose
- Intentional abbreviations: Tbsp, tsp, pkg, oz, lb, qt, pt, sm, lg, etc.
- Archaic or old-fashioned spellings where the "incorrect" form appears intentional
- YAML front-matter (everything between the `---` delimiters)
- Table column alignment (format_recipes.py handles this)
- Amounts, fractions, or temperatures (format_recipes.py handles these)

**When uncertain:** leave unchanged and note it in the summary.

---

## Steps

### 1. Check status

```bash
python _tools/proofread.py status
```

### 2. Get next batch

```bash
python _tools/proofread.py next-batch -n 15
```

If the output is empty, all recipes have been proofread — report "Done!" and stop.

### 3. Proofread each file

Process **one file at a time**:

1. Read the file.
2. Check for errors in scope (title, ingredient names, notes column, method, Notes From Gran, Modern Notes).
3. Fix errors with the Edit tool. If no errors, skip to step 4.
4. Record progress immediately:
   ```bash
   python _tools/proofread.py mark-done <filepath>
   ```
5. Move to the next file.

### 4. Format changed files

```bash
git diff --name-only HEAD
python _tools/format_recipes.py $(git diff --name-only HEAD | grep '\.md$' | tr '\n' ' ')
```

Skip if no files were changed.

### 5. Commit and summarize

If any files were changed, commit them:

```bash
git add _book_recipes/
git commit -m "[proofread] fix typos in pages NNN–NNN"
```

Replace `NNN–NNN` with the actual page range of files processed in this batch.

Then report:
- How many recipes were checked
- Each fix made (file + what changed)
- Any ambiguous cases left unchanged (and why)
- Current overall progress (`python _tools/proofread.py status`)
