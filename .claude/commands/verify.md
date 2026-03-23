# Verify Transcriptions

Verify all recipe transcriptions against page scan images, processing them in batches. Progress is tracked per recipe file in `.recipe_stats/verify_progress.json` — safe to interrupt and resume.

---

## Verification Rules

**Check (in priority order):**

1. **Ingredient names** — Is every ingredient what actually appears in the handwriting? Watch for brand-name substitutions (Bisquick transcribed as Flour), similar-looking words, AI "improvements"
2. **Ingredient amounts** — Does every amount match? Watch for fraction misreads (1/4 vs 1/2), unit confusion (tsp vs Tbsp)
3. **Missing or extra ingredients** — Count ingredients in image vs file
4. **Method accuracy** — Interpretive expansion is fine; check the *meaning* is preserved (correct temperatures, techniques, sequence)
5. **Notes From Gran** — Should match what's visible in the handwriting
6. **`from:` attribution** — Verify against what's visible after the recipe in the image

**Do NOT:**
- Rewrite method steps that are correct but paraphrased
- Change formatting or spelling (that's the proofread pass)
- Add Modern Notes commentary or changelog entries — just fix the file
- Modify categories or other front-matter

**When fixing errors:** silently correct the file. Do not add notes about what was changed.

**All files get checked** — recipes, household tips, remedy notes, everything. No skipping based on content type. Only use `skip` for files where the page scan is genuinely unreadable.

---

## Steps

### 1. Check status

```bash
python _tools/verify.py status
```

If already complete (0 remaining), report "Done!" and stop.

### 2. Loop: process batches until done

Repeat the following until `next-batch` returns empty output:

#### 2a. Get next batch

```bash
python _tools/verify.py next-batch -n 10
```

If empty, break out of the loop — all done.

The output format is one line per page: `NNN file1.md file2.md ...`

#### 2b. Verify each page

For each page in the batch:

1. **Read the page scan image**: `assets/enhanced/NNN.jpg`
2. **For each recipe file listed for that page**:
   - Read the recipe file
   - Compare every ingredient name, amount, and note against what's visible in the scan
   - Compare method steps against what's visible
   - Check `from:` attribution if visible
   - If errors are found: silently fix the file
   - If the page scan is genuinely unreadable:
     ```bash
     python _tools/verify.py skip <filepath> "reason for skipping"
     ```
3. **Mark verified recipes** (all checked files, whether corrected or not):
   ```bash
   python _tools/verify.py mark-done <filepath1> <filepath2> ...
   ```

#### 2c. Format and commit this batch

Format changed files:
```bash
python _tools/format_recipes.py $(git diff --name-only HEAD | grep '\.md$' | tr '\n' ' ')
```
Skip if no files were changed.

If any files were changed, commit:
```bash
git add _book_recipes/
git commit -m "[verify] check transcriptions for pages NNN-NNN"
```
Replace `NNN-NNN` with the actual page range of files processed in this batch.

If no files were changed (all correct), still commit the progress file is not needed — just continue to the next batch.

#### 2d. Continue to next batch

Print a brief batch summary (recipes verified, corrections made, recipes skipped and why), then loop back to step 2a.

### 3. Final report

After the loop completes:
- Total recipes verified across all batches
- All recipes skipped and why: `python _tools/verify.py skipped`
- Final status: `python _tools/verify.py status`
