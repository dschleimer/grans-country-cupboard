# Proofread Recipes

Proofread all remaining transcribed recipes for typos and spelling errors, processing them in batches. Progress is tracked in `.recipe_stats/proofread_progress.json` — safe to interrupt and resume.

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

If already complete (0 remaining), report "Done!" and stop.

### 2. Loop: process batches until done

Repeat the following until `next-batch` returns empty output:

#### 2a. Get next batch

```bash
python _tools/proofread.py next-batch -n 15
```

If empty, break out of the loop — all done.

#### 2b. Proofread each file

Process **one file at a time**:

1. Read the file.
2. Check for errors in scope (title, ingredient names, notes column, method, Notes From Gran, Modern Notes).
3. Fix errors with the Edit tool. If no errors, skip to step 4.
4. Record progress immediately:
   ```bash
   python _tools/proofread.py mark-done <filepath>
   ```
5. Move to the next file.

#### 2c. Format and commit this batch

Format any changed files:
```bash
python _tools/format_recipes.py $(git diff --name-only HEAD | grep '\.md$' | tr '\n' ' ')
```
Skip if no files were changed.

If any files were changed, commit:
```bash
git add _book_recipes/
git commit -m "[proofread] fix typos in pages NNN–NNN"
```
Replace `NNN–NNN` with the actual page range of files processed in this batch.

#### 2d. Continue to next batch

Print a brief batch summary (files checked, fixes made), then loop back to step 2a.

### 3. Final report

After the loop completes:
- Total recipes checked across all batches
- Summary of all fixes made
- Any ambiguous cases left unchanged (and why)
- Final status: `python _tools/proofread.py status`
