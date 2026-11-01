"""Reading a bank's CSV export into a header and rows, whatever its dialect."""

import csv
import io
from collections import Counter
from dataclasses import dataclass

from ..errors import ImportFileError

# Swedish bank exports are UTF-8 or, from older systems, Windows-1252.
ENCODINGS = ("utf-8-sig", "cp1252")
DELIMITERS = ",;\t"
# How many rows are looked at to find the header and the delimiter.
SNIFF_ROWS = 30


@dataclass(frozen=True)
class Row:
    line: int  # 1-based line in the file, for error messages
    cells: list[str]


@dataclass(frozen=True)
class Table:
    header: list[str]
    rows: list[Row]  # data rows, each padded or cut to the header's width

    def column(self, name: str) -> int:
        try:
            return self.header.index(name)
        except ValueError:
            raise ImportFileError(f"Column {name!r} not found; the file has {self.header}") from None

    def values(self, name: str) -> list[str]:
        i = self.column(name)
        return [r.cells[i] for r in self.rows]


def decode(content: str | bytes) -> str:
    if isinstance(content, str):
        return content.lstrip("﻿")
    for encoding in ENCODINGS:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportFileError("Could not read the file's text encoding")  # cp1252 decodes almost anything


def read_table(content: str | bytes) -> Table:
    """Decode, find the delimiter and the header row, and return the rows below it.

    Lines above the header (account name, export date...) and blank lines are skipped.
    """
    text = decode(content)
    if not text.strip():
        raise ImportFileError("The file is empty")
    delimiter = _sniff_delimiter(text)

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = []
    for cells in reader:
        cells = [c.strip() for c in cells]
        if any(cells):
            rows.append(Row(reader.line_num, cells))

    header_at = _header_index(rows)
    header = rows[header_at].cells
    while header and not header[-1]:  # trailing delimiters
        header = header[:-1]
    width = len(header)
    data = [Row(r.line, (r.cells + [""] * width)[:width]) for r in rows[header_at + 1 :]]
    return Table(header=header, rows=data)


def _sniff_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:SNIFF_ROWS])
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        # Fall back to whichever candidate appears most often.
        return max(DELIMITERS, key=sample.count)


def _header_index(rows: list[Row]) -> int:
    """The first row as wide as the table's most common row width, with no blank cells.

    Preamble lines are narrower than the data, so they're skipped.
    """
    head = rows[:SNIFF_ROWS]
    widths = Counter(sum(1 for c in r.cells if c) for r in head)
    width = max(widths, key=lambda w: (widths[w], w))
    for i, r in enumerate(head):
        if sum(1 for c in r.cells if c) >= width:
            return i
    return 0
