#!/usr/bin/env python3
"""Verification progress tracker for Gran's Country Cupboard recipes.

Tracks progress for verifying ALL recipe files against page scan images.
Pages are the batching unit (which image to read), but completion is per-file.

Usage:
  python _tools/verify.py status               # show progress
  python _tools/verify.py next-batch [-n N]    # next N pages of recipes
  python _tools/verify.py mark-done <files>    # record files as completed
  python _tools/verify.py skip <file> <reason> # skip a recipe with reason
  python _tools/verify.py skipped              # list all skipped recipes
  python _tools/verify.py reset                # clear all progress
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROGRESS_FILE = Path(".recipe_stats/verify_progress.json")
RECIPES_DIR = Path("_book_recipes")


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text())
        data.setdefault("skipped", {})
        return data
    return {"version": 1, "completed": [], "skipped": {}}


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.parent.mkdir(exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2) + "\n")


def get_all_recipes() -> list[str]:
    """Return sorted list of ALL recipe .md files under _book_recipes/."""
    files = sorted(
        str(f) for f in RECIPES_DIR.rglob("*.md")
    )
    return files


def page_from_path(filepath: str) -> str:
    """Extract 3-digit page number from path like _book_recipes/121/foo.md."""
    m = re.search(r"_book_recipes/(\d+)/", filepath)
    return m.group(1) if m else "000"


def group_by_page(files: list[str]) -> dict[str, list[str]]:
    """Group file paths by page number, sorted numerically."""
    groups = defaultdict(list)
    for f in files:
        groups[page_from_path(f)].append(f)
    return dict(sorted(groups.items(), key=lambda kv: int(kv[0])))


def cmd_status(args) -> None:
    progress = load_progress()
    all_files = get_all_recipes()
    done = set(progress["completed"])
    skipped = set(progress["skipped"])
    remaining = [f for f in all_files if f not in done and f not in skipped]
    total = len(all_files)
    n_done = len(done)
    n_skipped = len(skipped)
    pct = (100 * n_done // total) if total else 0

    print(f"Verification progress: {n_done}/{total} ({pct}%)")
    print(f"Remaining: {len(remaining)}")
    print(f"Skipped:   {n_skipped}")

    if remaining:
        pages = group_by_page(remaining)
        page_list = list(pages.keys())
        print(f"Page range: {page_list[0]}-{page_list[-1]} ({len(pages)} pages)")


def cmd_next_batch(args) -> None:
    progress = load_progress()
    all_files = get_all_recipes()
    done = set(progress["completed"])
    skipped = set(progress["skipped"])
    remaining = [f for f in all_files if f not in done and f not in skipped]

    pages = group_by_page(remaining)
    batch_pages = list(pages.items())[: args.n]

    for page_num, files in batch_pages:
        print(f"{page_num} " + " ".join(files))


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
        print(f"Marked {len(newly_done)} recipe(s) as verified.")
    else:
        print("No new files to mark (all already done).")


def cmd_skip(args) -> None:
    progress = load_progress()
    filepath = args.file.strip()
    reason = args.reason.strip()
    progress["skipped"][filepath] = reason
    save_progress(progress)
    print(f"Skipped: {filepath} -- {reason}")


def cmd_skipped(args) -> None:
    progress = load_progress()
    skipped = progress.get("skipped", {})
    if not skipped:
        print("No skipped recipes.")
        return
    print(f"{len(skipped)} skipped recipe(s):\n")
    for filepath, reason in sorted(skipped.items()):
        print(f"  {filepath}")
        print(f"    Reason: {reason}")


def cmd_reset(args) -> None:
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
    print("Progress reset.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")
    sub.required = True

    sub.add_parser("status", help="Show progress summary")

    nb = sub.add_parser("next-batch", help="Print next N pages of recipes")
    nb.add_argument(
        "-n", type=int, default=10, metavar="N",
        help="Number of pages (default 10)"
    )

    md = sub.add_parser("mark-done", help="Record recipe files as verified")
    md.add_argument("files", nargs="+", metavar="FILE")

    sk = sub.add_parser("skip", help="Skip a recipe with a reason")
    sk.add_argument("file", metavar="FILE")
    sk.add_argument("reason", metavar="REASON")

    sub.add_parser("skipped", help="List all skipped recipes")

    sub.add_parser("reset", help="Clear all progress")

    args = parser.parse_args()
    dispatch = {
        "status": cmd_status,
        "next-batch": cmd_next_batch,
        "mark-done": cmd_mark_done,
        "skip": cmd_skip,
        "skipped": cmd_skipped,
        "reset": cmd_reset,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
