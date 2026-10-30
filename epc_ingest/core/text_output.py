"""The CSV rendering of the table, and the row digest a database load is checked against.

Copied from datazone-ahah's core/text_output.py, which copied postcode-simd's, and extended with
the kinds EPC needs: int64, date, datetime and bool. The digest framing is unchanged (definition
version 1): a null is a marker, fields are joined with a separator, each row is hashed, the
signed eight-byte prefixes are summed.

Empty is not null. A string column renders the empty string as nothing and NULL as the marker,
so a published empty cell and a derived NULL hash differently on both sides.
"""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
from decimal import Decimal, localcontext
from pathlib import Path

import pandas as pd
import yaml

from .checks import Report
from .sources import sha256

INTEGER_KINDS = ("int16", "int32", "int64")
KINDS = ("string", "decimal", "date", "datetime", "bool") + INTEGER_KINDS
# decimal(19,4) on SQL Server: 15 integer digits at most.
DECIMAL_PRECISION, DECIMAL_SCALE = 19, 4
DATE_FORMAT, DATETIME_FORMAT = "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"


class ReservedCharacter(ValueError):
    """Source text contains a character the digest framing needs. Never stripped."""


class DecimalDoesNotFit(ValueError):
    """A value has more fractional digits than the column's scale, or too many digits in all."""


def load_contract(path: Path) -> dict:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if raw.get("version") != 1:
        raise ValueError(f"Unsupported export contract version {raw.get('version')!r}")
    if raw["digest"]["version"] != 1 or raw["digest"]["hash"] != "sha256":
        raise ValueError("Unsupported digest definition")
    if raw["values"]["decimal_places"] != DECIMAL_SCALE:
        raise ValueError("The decimal rendering must match the SQL scale")
    raw["sha256"] = sha256(path)
    return raw


def exported_columns(schema: dict, contract: dict, table: str) -> list:
    spec = contract["tables"][table]
    excluded = set(spec["exclude"])
    names = [f["name"] for f in schema["fields"]]
    missing = excluded - set(names)
    if missing:
        raise ValueError(f"{table}: excluded columns are not in the schema: {sorted(missing)}")
    return [name for name in names if name not in excluded]


def render_decimal(value: Decimal, places: int = DECIMAL_SCALE) -> str:
    """Fixed notation with exactly `places` fractional digits. Refuses to round: a value with
    more digits than the scale does not fit the column and must stop the build, not be trimmed.
    Zero is never written with a sign, as SQL Server never writes one."""
    if not isinstance(value, Decimal):
        raise TypeError(f"not a Decimal: {value!r}")
    if not value.is_finite():
        raise DecimalDoesNotFit(f"{value} is not finite")
    if value == 0:
        value = Decimal(0)
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION + places
        quantised = value.quantize(Decimal(1).scaleb(-places))
    if quantised != value:
        raise DecimalDoesNotFit(f"{value} has more than {places} fractional digits")
    text = f"{quantised:f}"
    digits = text.replace("-", "").replace(".", "")
    if len(digits.lstrip("0") or "0") > DECIMAL_PRECISION:
        raise DecimalDoesNotFit(f"{value} has more than {DECIMAL_PRECISION} digits")
    return text


def parse_decimal(text: str) -> Decimal:
    """The file's text as an exact Decimal, never via float."""
    value = Decimal(text.strip())
    if not value.is_finite():
        raise DecimalDoesNotFit(f"{text!r} is not a finite number")
    return value


def parse_date(text: str, fmt: str = DATE_FORMAT) -> dt.date:
    """A calendar date in exactly the given format. `strptime` is strict about the shape; the
    round trip through `strftime` rejects what it would otherwise accept, such as a one-digit
    day."""
    value = dt.datetime.strptime(text, fmt)
    if value.strftime(fmt) != text:
        raise ValueError(f"{text!r} is not a date in the form {fmt}")
    return value.date()


def parse_datetime(text: str, fmt: str) -> dt.datetime:
    value = dt.datetime.strptime(text, fmt)
    if value.strftime(fmt) != text:
        raise ValueError(f"{text!r} is not a timestamp in the form {fmt}")
    return value


def _is_null(v) -> bool:
    return v is None or v is pd.NA or (isinstance(v, float) and v != v)


def render_value(v, kind: str, marker: str, places: int = DECIMAL_SCALE) -> str:
    """One cell as the text the CSV carries and the digest hashes."""
    if _is_null(v):
        return marker
    if kind == "string":
        return str(v)
    if kind == "decimal":
        return render_decimal(v, places)
    if kind in INTEGER_KINDS:
        return str(int(v))
    if kind == "date":
        return v.strftime(DATE_FORMAT)
    if kind == "datetime":
        return v.strftime(DATETIME_FORMAT)
    if kind == "bool":
        return "1" if v else "0"
    raise ValueError(f"unsupported type {kind!r}")


def render(table: pd.DataFrame, schema: dict, columns: list, contract: dict) -> pd.DataFrame:
    """Every exported value as text, with nulls marked."""
    kinds = {f["name"]: f["type"] for f in schema["fields"]}
    nullable = {f["name"]: bool(f["nullable"]) for f in schema["fields"]}
    marker, reserved = contract["digest"]["null_marker"], contract["digest"]["reserved"]
    places = contract["values"]["decimal_places"]
    out = {}
    for name in columns:
        column, kind = table[name], kinds[name]
        if kind == "string":
            values = column.astype("string")
            found = [c for c in reserved if values.str.contains(c, regex=False, na=False).any()]
            if found:
                raise ReservedCharacter(f"{name}: source text contains {found!r}, which the digest framing reserves")
            if nullable[name] and (values == "").any():
                raise ValueError(f"{name}: a nullable text column holds an empty string, which the CSV could not tell from NULL")
            values = values.fillna(marker)
        else:
            values = pd.Series([render_value(v, kind, marker, places) for v in column], index=column.index, dtype="string")
        out[name] = values.astype("string")
    return pd.DataFrame(out, index=table.index)[columns]


class CsvWriter:
    """One gzip CSV written in parts: the header once, then each rendered part as it comes.
    mtime 0, so the same rows give the same bytes."""

    def __init__(self, contract: dict, path: Path):
        self.contract, self.path = contract, Path(path)
        self.dialect = contract["dialect"]
        self.rows = 0
        self.columns = None
        self.uncompressed = 0
        self.hash = hashlib.sha256()
        self._fh = open(self.path, "wb")
        self._gz = gzip.GzipFile(filename="", fileobj=self._fh, mode="wb", mtime=0)

    def write(self, rendered: pd.DataFrame) -> None:
        if self.columns is None:
            self.columns = list(rendered.columns)
        elif list(rendered.columns) != self.columns:
            raise ValueError("a later part has different columns")
        frame = rendered.replace(self.contract["digest"]["null_marker"], self.contract["values"]["empty"])
        text = frame.to_csv(index=False, header=self.rows == 0, sep=self.dialect["delimiter"],
                            lineterminator=self.dialect["line_ending"])
        body = text.encode(self.dialect["encoding"])
        self._gz.write(body)
        self.hash.update(body)
        self.uncompressed += len(body)
        self.rows += len(rendered)

    def close(self) -> dict:
        self._gz.close()
        self._fh.close()
        return {"file": self.path.name, "sha256": sha256(self.path), "bytes": self.path.stat().st_size,
                "uncompressed_bytes": self.uncompressed, "uncompressed_sha256": self.hash.hexdigest(),
                "rows": self.rows, "columns": len(self.columns or []), "compression": self.dialect["compression"]}


def write_csv(rendered: pd.DataFrame, contract: dict, path: Path) -> dict:
    """The rendered table as CSV in one part, nulls written as an empty cell."""
    writer = CsvWriter(contract, path)
    writer.write(rendered)
    return writer.close()


def row_hashes(rendered: pd.DataFrame, contract: dict) -> list:
    """The signed eight-byte prefix of each row's SHA-256 over the marked, separated fields."""
    spec = contract["digest"]
    separator, size, signed = spec["separator"], spec["prefix_bytes"], spec["signed"]
    joined = rendered.iloc[:, 0]
    for name in rendered.columns[1:]:
        joined = joined + separator + rendered[name]
    return [int.from_bytes(hashlib.sha256(line.encode("utf-8")).digest()[:size], "big", signed=signed)
            for line in joined.to_numpy()]


def row_digest(rendered: pd.DataFrame, contract: dict) -> dict:
    """One SHA-256 per row; the prefixes summed exactly, so the total does not depend on row
    order."""
    return digest_record(contract, len(rendered), sum(row_hashes(rendered, contract)))


def digest_record(contract: dict, rows: int, total: int) -> dict:
    return {"version": contract["digest"]["version"], "rows": rows, "total": str(total),
            "note": "compact probabilistic check for accidental load corruption, not a proof of identity"}


def readback_csv_digest(path: Path, columns: list, schema: dict, contract: dict, report: Report, label: str,
                        expected_rows: int, expected_total: int) -> None:
    """Reopen the saved CSV as text, in parts, and recompute the digest from the bytes on disk.
    A published empty string and a NULL both travel as an empty cell, so the schema decides
    what an empty cell was: NULL in a nullable column, the empty string in a NOT NULL one. This
    is the same rule the import script applies (NULLIF against ISNULL), so a digest that
    matches here is the digest SQL Server must reproduce."""
    marker, empty = contract["digest"]["null_marker"], contract["values"]["empty"]
    nullable = [f["name"] for f in schema["fields"] if f["nullable"] and f["name"] in columns]
    rows, total = 0, 0
    with gzip.open(path, "rt", encoding=contract["dialect"]["encoding"], newline="") as fh:
        parts = pd.read_csv(fh, dtype=str, keep_default_na=False, sep=contract["dialect"]["delimiter"], chunksize=200_000)
        header_checked = False
        for part in parts:
            if not header_checked:
                report.equal(f"{label}.header", list(part.columns), list(columns))
                report.require()
                header_checked = True
            part = part.astype("string")
            for name in nullable:
                part[name] = part[name].replace(empty, marker)
            rows += len(part)
            total += sum(row_hashes(part, contract))
    report.equal(f"{label}.rows", rows, expected_rows)
    report.equal(f"{label}.digest_total", str(total), str(expected_total),
                 detail="the digest recomputed from the bytes on disk equals the one computed while writing"
                 if total == expected_total else "the file on disk does not hash to the recorded total")
