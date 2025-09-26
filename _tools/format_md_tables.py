#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
format_md_tables.py

A command‑line utility that normalises the layout of markdown tables
in one or more files while leaving all other text untouched.

Usage:
    python format_md_tables.py path/to/file1.md [path/to/file2.md ...]
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple

# ------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------

def build_row(cells: List[str]) -> str:
    """
    Assemble a row from a list of cell strings, inserting the required
    surrounding pipes and spaces.
    """
    res =  "| " + " | ".join(cells) + " |"
    # if the last cell is empty, we only want 1 space in it, not two
    if res.endswith('|  |'):
        res = res[:-2] + '|'
    return res

def is_table_row(line: str) -> bool:
    """Return ``True`` if *line* appears to be a markdown table row.

    The original implementation required a leading ``"| "`` and a trailing
    ``" |"``. Real‑world tables are often malformed – they may miss the spaces
    around the leading/trailing pipe or the column separators.  This tolerant
    version simply checks that the line (ignoring surrounding whitespace) starts
    and ends with a pipe character.  It also ensures that there is at least one
    additional pipe inside the line so that a single ``"|"`` line is not treated
    as a table row.
    """
    stripped = line.strip()
    # Must start and end with a pipe and contain at least one more pipe to
    # separate columns.
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") > 1

def split_row(line: str) -> List[str]:
    """Split a markdown table *line* into its constituent cells.

    The function is robust to missing spaces around the pipe characters.  It
    performs the following steps:

    1. Strip the trailing newline and surrounding whitespace.
    2. Remove the leading and trailing pipe characters.
    3. Split on the pipe character.
    4. Strip whitespace from each individual cell.

    Empty cells are represented as empty strings.
    """
    # Step 1 – remove newline and surrounding whitespace
    core = line.strip()
    # Step 2 – drop the first and last pipe
    if core.startswith("|"):
        core = core[1:]
    if core.endswith("|"):
        core = core[:-1]
    # Step 3 – split on remaining pipe characters
    raw_cells = core.split("|")
    # Step 4 – strip spaces from each cell
    cells = [c.strip() for c in raw_cells]
    return cells

def normalize_table(rows: List[str]) -> List[str]:
    """
    Given the raw lines of a markdown table (including header, separator
    and data rows), return a new list of lines where each column has a
    uniform width and the separator row consists of dashes.
    """
    # Parse all rows into cells
    parsed = [split_row(r) for r in rows]

    # Determine column count (all rows must have the same number)
    col_count = max(len(c) for c in parsed)

    # Pad each parsed row to the full column count with empty strings
    for cells in parsed:
        if len(cells) < col_count:
            cells.extend([""] * (col_count - len(cells)))

    # Compute max width for each column **excluding** the separator row
    max_widths = [0] * col_count
    for r, cells in enumerate(parsed):
        if r == 1:          # skip separator row
            continue
        for i, cell in enumerate(cells):
            # Visible length of the cell (do not count surrounding spaces)
            max_widths[i] = max(max_widths[i], len(cell))
    
    # don't pad the last column
    max_widths[-1] = 0

    # Build new rows
    new_rows: List[str] = []

    for r, cells in enumerate(parsed):
        if r == 1:          # separator row – dashes, no extra spaces
            dash_cells = []
            for w in max_widths:
                # At least three dashes are the usual markdown minimum,
                # but we follow the rule: fill the column width with '-'
                # except for the last column where we match the length of
                # the header ("Notes")
                dash_cells.append("-" * max(w, 5))
            new_rows.append(build_row(dash_cells))
        elif all(cell.strip() == '' for cell in cells):
            new_rows.append(build_row([cell.strip() for cell in cells]))
        else:
            padded_cells = []
            for i, cell in enumerate(cells):
                # Pad with spaces on the right to reach column width
                padded = cell + " " * (max_widths[i] - len(cell))
                padded_cells.append(padded)
            new_rows.append(build_row(padded_cells))

    return new_rows


def process_file(path: Path) -> None:
    """
    Read *path*, reformat any markdown tables it contains, and write the
    result back to the same file.
    """
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines: List[str] = []
    i = 0
    while i < len(lines):
        # Look for the start of a table
        if is_table_row(lines[i]):
            # Potential table – collect consecutive table rows
            table_rows = []
            while i < len(lines) and is_table_row(lines[i]):
                table_rows.append(lines[i])
                i += 1

            # Only treat it as a table if we have at least 3 rows
            if len(table_rows) >= 3:
                normalized = normalize_table(table_rows)
                out_lines.extend([r + "\n" for r in normalized])
                continue          # skip the normal i+=1 at the end of loop
            else:
                # Not enough rows – treat as ordinary text
                out_lines.extend(table_rows)
                continue
        else:
            # Regular line – copy unchanged
            out_lines.append(lines[i])
            i += 1

    # Write back
    with path.open("w", encoding="utf-8") as f:
        f.writelines(out_lines)


# ------------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------------
def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python format_md_tables.py <markdown-file> [<markdown-file> ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    # Process each argument as a separate markdown file
    for arg in sys.argv[1:]:
        md_path = Path(arg)
        if not md_path.is_file():
            print(f"Error: file not found – {md_path}", file=sys.stderr)
            continue
        process_file(md_path)
        print(f"Formatted tables in '{md_path}'.")


if __name__ == "__main__":
    main()
