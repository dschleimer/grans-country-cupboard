#!/usr/bin/env bash
# run_transcribe.sh — Automated machine transcription for Gran's Country Cupboard recipes.
#
# Spawns fresh `claude -p` sessions for each batch to avoid context limits.
# Saves progress after each recipe, so it can be safely interrupted and resumed.
#
# Usage:
#   bash _tools/run_transcribe.sh
#
# Environment variables (all optional):
#   TRANSCRIBE_BATCH=10  — pages per batch (default 10)

set -euo pipefail

BATCH_SIZE="${TRANSCRIBE_BATCH:-10}"

# Must be run from repo root
if [[ ! -d "_book_recipes" ]]; then
  echo "Error: run this script from the repo root (where _book_recipes/ lives)." >&2
  exit 1
fi

echo "=== Gran's Country Cupboard — Machine Transcription ==="
python _tools/transcribe.py status
echo ""

while true; do
  # Get next batch of pages with untranscribed recipes
  BATCH_OUTPUT=$(python _tools/transcribe.py next-batch -n "$BATCH_SIZE")

  if [[ -z "$BATCH_OUTPUT" ]]; then
    echo ""
    echo "=== All recipes have been processed. ==="
    python _tools/transcribe.py status
    echo ""
    echo "Skipped recipes:"
    python _tools/transcribe.py skipped
    exit 0
  fi

  # Extract page range for display
  FIRST_PAGE=$(echo "$BATCH_OUTPUT" | head -1 | cut -d' ' -f1)
  LAST_PAGE=$(echo "$BATCH_OUTPUT" | tail -1 | cut -d' ' -f1)
  PAGE_COUNT=$(echo "$BATCH_OUTPUT" | wc -l)

  echo "--- Batch: $PAGE_COUNT pages ($FIRST_PAGE–$LAST_PAGE) ---"
  echo "$BATCH_OUTPUT"
  echo ""

  # Build the prompt
  read -r -d '' PROMPT << 'PROMPT_EOF' || true
You are machine-transcribing handwritten recipes from Gran's Country Cupboard, a 1975
cookbook. The enhanced page scans are in assets/enhanced/NNN.jpg.

TRANSCRIPTION GUIDELINES:
- **Interpret**, don't literally transcribe — make Gran's terse instructions accessible
- Ingredients: 3-column table (Ingredient | Amount | Notes), capitalize like existing recipes
- Method: numbered list (1. for each step), expand terse instructions into clear directions
- Notes From Gran: tips/variations visible in the handwriting (bullet list with *)
- Modern Notes: explain 1970s terms, suggest modern substitutes, note anything uncertain (*)
- If a name/location is visible after the recipe, capture it in the from: front-matter field
- Add `  - Machine Transcribed` to the categories list

Reference these for tone/style:
  _book_recipes/007/party_meat_balls.md
  _book_recipes/008/cheese_puffs.md

SKIP any recipe where you are NOT confident — do not guess. Mark skipped:
  python _tools/transcribe.py skip <filepath> "reason"

PROCESS:
For each page line below (format: NNN file1.md file2.md):
1. Read assets/enhanced/NNN.jpg (the page scan image)
2. Read each recipe template file listed
3. Transcribe confidently or skip with reason
4. Mark completed: python _tools/transcribe.py mark-done <files...>

After all pages, run:
  python _tools/fix_categories.py _book_recipes/

Pages to transcribe:
PROMPT_EOF

  FULL_PROMPT="${PROMPT}${BATCH_OUTPUT}

After all pages are processed, briefly summarize: how many transcribed, how many skipped and why."

  # Run Claude in non-interactive mode
  if claude --dangerously-skip-permissions -p "$FULL_PROMPT"; then
    echo ""
    # Format any files that were changed
    CHANGED=$(git diff --name-only HEAD | grep '\.md$' || true)
    if [[ -n "$CHANGED" ]]; then
      echo "Formatting changed files..."
      # shellcheck disable=SC2086
      python _tools/format_recipes.py $CHANGED

      git add _book_recipes/
      git commit -m "[transcribe] machine transcribe pages ${FIRST_PAGE}–${LAST_PAGE}"
    fi
    echo ""
    python _tools/transcribe.py status
    echo ""
  else
    EXIT_CODE=$?
    echo ""
    echo "Claude exited with code $EXIT_CODE. Progress is saved — re-run to resume."
    exit 1
  fi
done
