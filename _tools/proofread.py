#!/usr/bin/env python3
"""Proofreading progress tracker for Gran's Country Cupboard recipes.

Usage:
  python _tools/proofread.py status            # show progress
  python _tools/proofread.py next-batch [-n N] # print next N unprocessed paths
  python _tools/proofread.py mark-done <files> # record files as proofread
  python _tools/proofread.py reset             # clear all progress
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROGRESS_FILE = Path(".recipe_stats/proofread_progress.json")
RECIPES_DIR = Path("_book_recipes")


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"version": 1, "completed": []}


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.parent.mkdir(exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2) + "\n")


def get_all_transcribed() -> list[str]:
    """Return sorted list of transcribed recipe file paths."""
    result = subprocess.run(
        ["grep", "-rL", "Needs Transcription", str(RECIPES_DIR)],
        capture_output=True,
        text=True,
    )
    files = sorted(
        f for f in result.stdout.strip().splitlines() if f.endswith(".md")
    )
    return files


def cmd_status(args) -> None:
    progress = load_progress()
    all_files = get_all_transcribed()
    done = set(progress["completed"])
    remaining = [f for f in all_files if f not in done]
    total = len(all_files)
    n_done = len(done)
    pct = (100 * n_done // total) if total else 0
    print(f"Proofreading progress: {n_done}/{total} ({pct}%)")
    print(f"Remaining: {len(remaining)}")
    if remaining:
        print(f"Next file: {remaining[0]}")


def cmd_next_batch(args) -> None:
    progress = load_progress()
    all_files = get_all_transcribed()
    done = set(progress["completed"])
    remaining = [f for f in all_files if f not in done]
    batch = remaining[: args.n]
    for f in batch:
        print(f)


def cmd_mark_done(args) -> None:
    progress = load_progress()
    done = set(progress["completed"])
    newly_done = []
    for f in args.files:
        f = f.strip()
        if f and f not in done:
            done.add(f)
            newly_done.append(f)
    progress["completed"] = sorted(done)
    save_progress(progress)
    if newly_done:
        print(f"Marked {len(newly_done)} file(s) as done.")
    else:
        print("No new files to mark (all already done).")


def cmd_reset(args) -> None:
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
    print("Progress reset.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")
    sub.required = True

    sub.add_parser("status", help="Show progress summary")

    nb = sub.add_parser("next-batch", help="Print next N unprocessed file paths")
    nb.add_argument("-n", type=int, default=15, metavar="N", help="Batch size (default 15)")

    md = sub.add_parser("mark-done", help="Record files as proofread")
    md.add_argument("files", nargs="+", metavar="FILE")

    sub.add_parser("reset", help="Clear all progress")

    args = parser.parse_args()
    dispatch = {
        "status": cmd_status,
        "next-batch": cmd_next_batch,
        "mark-done": cmd_mark_done,
        "reset": cmd_reset,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
