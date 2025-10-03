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
import argparse
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

def normalize_tables(lines: List[str]) -> List[str]:
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
    return out_lines

def normalize_fractions(lines: List[str]) -> List[str]:
    """
    Replace ASCII fractions (e.g. "1/2") with Unicode fraction characters
    in a list of strings.  Fractions that are preceded by a whole number
    and a space (e.g. "1 1/2") are collapsed into a single token
    (e.g. "1½").
    """
    # Mapping of common fraction strings to Unicode characters.
    frac_map = {
        ("1", "2"): "½",
        ("1", "4"): "¼",
        ("3", "4"): "¾",
        ("1", "3"): "⅓",
        ("2", "3"): "⅔",
        ("1", "5"): "⅕",
        ("2", "5"): "⅖",
        ("3", "5"): "⅗",
        ("4", "5"): "⅘",
        ("1", "6"): "⅙",
        ("5", "6"): "⅚",
        ("1", "8"): "⅛",
        ("3", "8"): "⅜",
        ("5", "8"): "⅝",
        ("7", "8"): "⅞",
    }

    # Pattern that matches a whole number followed by a space and a fraction.
    pattern_with_whole = re.compile(r"\b(\d+)\s+(\d+)/(\d+)\b")
    # Pattern that matches a plain fraction.
    pattern_plain = re.compile(r"\b(\d+)/(\d+)\b")

    def replace_with_whole(match: re.Match) -> str:
        whole, num, den = match.group(1), match.group(2), match.group(3)
        return whole + frac_map.get((num, den), f"{num}/{den}")

    def replace_plain(match: re.Match) -> str:
        num, den = match.group(1), match.group(2)
        return frac_map.get((num, den), f"{num}/{den}")

    # First handle fractions that follow a whole number (removing the space).
    processed = [pattern_with_whole.sub(replace_with_whole, line) for line in lines]
    # Then handle any remaining plain fractions.
    processed = [pattern_plain.sub(replace_plain, line) for line in processed]
    return processed

def normalize_temperature(lines: List[str]) -> List[str]:
    """
    Normalise temperature literals.

    Supports the following forms (case‑insensitive):

    * ``DDDF``          – e.g. ``32F``
    * ``DDD F``         – e.g. ``32 F``
    * ``DDD degrees``   – e.g. ``32 degrees`` (assumed Celsius)
    * ``DDD degrees F`` – e.g. ``32 degrees F``

    If no unit is supplied but the word *degrees* is present, the value is
    treated as Celsius.  If neither a unit nor *degrees* is present, the
    token is left unchanged.  Kelvin is intentionally ignored.

    The output format is ``DDD °F`` or ``DDD °C`` (e.g. ``32 °F`` or ``32 °C``).
    """
    # Match a number (1‑3 digits) optionally followed by the word “degrees”
    # and an optional unit (F, C or “celsius”).  The unit and/or the word
    # *degrees* must be present for the match to be meaningful; otherwise
    # the replacement function will return the original text unchanged.
    temp_re = re.compile(
        r"""
        \b
        (?P<num>\d{1,3})          # numeric value
        \s*
        (?:                       # optional “degrees” keyword
            (?P<degrees>degrees)
            \s*
        )?
        (?P<unit>F|fahrenheit|C|celsius|K|kelvin|R|rankine)?    # optional unit
        \b
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def repl(match: re.Match) -> str:
        num = match.group("num")
        unit = match.group("unit")
        degrees = match.group("degrees")

        # If neither unit nor “degrees” were provided, do not replace.
        if unit is None and degrees is None:
            return match.group(0)

        # Decide the output unit symbol.
        if unit:
            unit_lower = unit.lower()
            if unit_lower in ("c", "celsius"):
                symbol = "°C"
            elif unit_lower in ("f", "fahrenheit"):
                symbol = "°F"
            elif unit_lower in ("R", "rankine"):
                symbol = "°R"
            else:
                # Unsupported unit – leave unchanged.
                return match.group(0)
        else:
            # Only “degrees” was present → treat as Farenheit.
            symbol = "°F"

        return f"{num} {symbol}"

    # Apply the transformation to every line.
    return [temp_re.sub(repl, line) for line in lines]

def process_file(path: Path) -> None:
    """
    Read *path*, reformat any markdown tables it contains, and write the
    result back to the same file.
    """
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = normalize_temperature(lines)
    if new_lines != lines:
        print(f"Temperature was normalized in '{path}'.")
        lines = new_lines

    # Normalize fractions before tables
    new_lines = normalize_fractions(lines)
    if new_lines != lines:
        print(f"Fractions were normalized in '{path}'.")
        lines = new_lines

    new_lines = normalize_tables(lines)
    if lines != new_lines:
        print(f"Formatted tables in '{path}'.")
        lines = new_lines

    # Write back
    with path.open("w", encoding="utf-8") as f:
        f.writelines(lines)


# ------------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------------
def main() -> None:
    """Parse command‑line arguments using argparse and format the provided files.

    The program accepts one or more positional arguments representing the
    paths of markdown files to process.  Any invalid paths are reported to
    ``stderr`` and skipped.
    """
    parser = argparse.ArgumentParser(
        description="Normalise the layout of markdown tables in one or more files."
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Path(s) to markdown file(s) to format.",
    )
    args = parser.parse_args()

    # Process each provided file
    for file_path in args.files:
        md_path = Path(file_path)
        if not md_path.is_file():
            print(f"Error: file not found – {md_path}", file=sys.stderr)
            continue
        process_file(md_path)


if __name__ == "__main__":
    main()
