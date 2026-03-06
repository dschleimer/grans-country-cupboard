#!/usr/bin/env bash
# run_proofread.sh — Fully automated proofreading for Gran's Country Cupboard recipes.
#
# Spawns fresh `claude -p` sessions for each batch to avoid context limits.
# Saves progress after each file, so it can be safely interrupted and resumed.
# Sleeps and retries on failure (e.g. usage limit hits).
#
# Usage:
#   bash _tools/run_proofread.sh
#
# Environment variables (all optional):
#   PROOFREAD_BATCH=15       — files per batch (default 15)
#   PROOFREAD_RETRY_SLEEP=300 — seconds to sleep on failure (default 300 = 5 min)

set -euo pipefail

BATCH_SIZE="${PROOFREAD_BATCH:-15}"
RETRY_SLEEP="${PROOFREAD_RETRY_SLEEP:-300}"

# Must be run from repo root
if [[ ! -d "_book_recipes" ]]; then
  echo "Error: run this script from the repo root (where _book_recipes/ lives)." >&2
  exit 1
fi

echo "=== Gran's Country Cupboard — Proofreading ==="
python _tools/proofread.py status
echo ""

while true; do
  # Get next batch of unprocessed files
  mapfile -t BATCH < <(python _tools/proofread.py next-batch -n "$BATCH_SIZE")

  if [[ ${#BATCH[@]} -eq 0 ]]; then
    echo ""
    echo "=== All recipes have been proofread. Done! ==="
    python _tools/proofread.py status
    exit 0
  fi

  FILE_COUNT="${#BATCH[@]}"
  echo "--- Batch of $FILE_COUNT files ---"
  printf '  %s\n' "${BATCH[@]}"
  echo ""

  # Build file list as newline-separated string for the prompt
  FILES_LIST=$(printf '%s\n' "${BATCH[@]}")

  # The prompt sent to each fresh Claude session
  read -r -d '' PROMPT << 'PROMPT_EOF' || true
You are proofreading recipe files from Gran's Country Cupboard, a handwritten cookbook
from 1975 that was transcribed by a human typist. Your job is to find and fix clear
transcription errors — typos, dropped letters, doubled letters, repeated words.

SCOPE — only check these sections:
- H1 recipe title
- Ingredient names (first column of the ingredients table)
- Notes column in the ingredients table
- Method steps (numbered list)
- Notes From Gran section
- Modern Notes section

DO NOT CHANGE:
- YAML front-matter (everything between the --- delimiters at the top)
- Table column alignment or padding (format_recipes.py handles this)
- Amounts, fractions, or measurements (format_recipes.py handles these)
- Gran's voice, phrasing, or style in Notes From Gran — preserve original wording
  even if grammatically loose or old-fashioned
- Intentional abbreviations: Tbsp, tsp, pkg, oz, lb, qt, pt, sm, lg, etc.
- Archaic or old-fashioned spellings where the "incorrect" form appears intentional

WHAT TO FIX:
- Clear misspellings from transcription: dropped letters, transposed letters,
  doubled letters (e.g. "occassionally" → "occasionally", "seafod" → "seafood")
- Repeated words ("and and", "the the")
- Obvious incomplete words

WHEN UNCERTAIN: leave it unchanged and mention it in your summary.

PROCESS ONE FILE AT A TIME in this exact order:
1. Read the file using the Read tool
2. Identify any errors in scope
3. Fix errors with the Edit tool (skip if no errors found)
4. Run this shell command to record progress:
     python _tools/proofread.py mark-done <filepath>
   (replace <filepath> with the actual path you just processed)
5. Move to the next file

Files to proofread:
PROMPT_EOF

  # Append the file list to the prompt
  FULL_PROMPT="${PROMPT}${FILES_LIST}

After all files are processed, briefly summarize: how many had changes and what was fixed."

  # Run Claude in non-interactive mode
  if claude --dangerously-skip-permissions -p "$FULL_PROMPT"; then
    echo ""
    # Format any files that were changed
    CHANGED=$(git diff --name-only HEAD | grep '\.md$' || true)
    if [[ -n "$CHANGED" ]]; then
      echo "Formatting changed files..."
      # shellcheck disable=SC2086
      python _tools/format_recipes.py $CHANGED

      # Determine page range for commit message
      FIRST_PAGE=$(echo "$CHANGED" | head -1 | grep -oP '(?<=_book_recipes/)\d+' | head -1)
      LAST_PAGE=$(echo "$CHANGED" | tail -1 | grep -oP '(?<=_book_recipes/)\d+' | head -1)
      git add _book_recipes/
      git commit -m "[proofread] fix typos in pages ${FIRST_PAGE}–${LAST_PAGE}"
    fi
    echo ""
  else
    EXIT_CODE=$?
    echo ""
    echo "Claude exited with code $EXIT_CODE."
    echo "This may be a usage limit. Sleeping ${RETRY_SLEEP}s before retrying..."
    echo "(Interrupt with Ctrl+C to stop. Progress is saved — resume by re-running this script.)"
    sleep "$RETRY_SLEEP"
    echo "Retrying..."
    echo ""
  fi
done
