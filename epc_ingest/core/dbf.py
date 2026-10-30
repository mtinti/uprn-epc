"""Read the records of a dBASE III/IV table (the .dbf of a shapefile) with the standard library.

Only character and numeric fields are decoded, as text; that is all the data zone list needs.
"""

from __future__ import annotations

import struct
from pathlib import Path


def read_dbf(path: Path, encoding: str = "latin-1") -> list[dict]:
    """Every live record as a dict of field name to stripped text. A deleted record (marker
    `*`) is skipped. The header's record count must match the records present."""
    data = Path(path).read_bytes()
    record_count, header_length, record_length = struct.unpack("<IHH", data[4:12])
    fields = []
    offset = 32
    while data[offset] != 0x0D:
        name = data[offset:offset + 11].split(b"\0", 1)[0].decode("ascii")
        length = data[offset + 16]
        fields.append((name, length))
        offset += 32
    if sum(length for _, length in fields) + 1 != record_length:
        raise ValueError(f"{path}: field widths do not add up to the record length")
    records = []
    position = header_length
    for _ in range(record_count):
        record = data[position:position + record_length]
        if len(record) < record_length:
            raise ValueError(f"{path}: file ends before the header's record count")
        position += record_length
        if record[0:1] == b"*":
            continue
        row, at = {}, 1
        for name, length in fields:
            row[name] = record[at:at + length].decode(encoding).strip()
            at += length
        records.append(row)
    return records
