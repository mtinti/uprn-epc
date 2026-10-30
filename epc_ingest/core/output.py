"""Write the frozen schema to Parquet, one row group per part, with table-level metadata, and
read it back to verify."""

from __future__ import annotations

import datetime as dt
import json
import os
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from .checks import Report
from .sources import sha256
from .text_output import DECIMAL_PRECISION, DECIMAL_SCALE, INTEGER_KINDS, _is_null

ARROW = {"string": pa.string(), "int16": pa.int16(), "int32": pa.int32(), "int64": pa.int64(),
         "decimal": pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE), "date": pa.date32(),
         "datetime": pa.timestamp("ms"), "bool": pa.bool_()}

GRAIN = ("One row per published certificate, superseded certificates included (HISTORIC = True). "
         "The 107 published columns are text exactly as published; the derived columns are typed "
         "copies by documented rules. Join by uprn_osg as an integer, never as text.")


def load_schema(path: Path) -> dict:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw["key"], list) or not raw["key"]:
        raise ValueError(f"{path}: key must be a non-empty list")
    names = [f["name"] for f in raw["fields"]]
    folded = {}
    for name in names:
        folded.setdefault(name.lower(), []).append(name)
    clashes = {k: v for k, v in folded.items() if len(v) > 1}
    if clashes:
        raise ValueError(f"{path}: column names that differ only by case, which SQL Server treats as one name: {clashes}")
    for f in raw["fields"]:
        if f["type"] not in ARROW:
            raise ValueError(f"{path}: {f['name']} has unsupported type {f['type']!r}")
        if f["type"] == "string" and not isinstance(f.get("width"), int):
            raise ValueError(f"{path}: {f['name']} is a string without a width")
    for k in raw["key"]:
        if k not in names:
            raise ValueError(f"{path}: key column {k} is not a field")
    return {"version": raw["version"], "table": raw["table"], "key": list(raw["key"]),
            "fields": raw["fields"], "sha256": sha256(path)}


def table_metadata(registry, schema: dict, decisions_sha256: str) -> dict:
    return {"grain": GRAIN, "schema_version": schema["version"], "key": schema["key"],
            "epc_release": registry.epc_release, "decisions_sha256": decisions_sha256,
            "registry_sha256": registry.sha256,
            "sources": [{"year": m["year"], "file": m["file"], "sha256": m["sha256"]} for m in registry.members]}


def arrow_schema(schema: dict, metadata: dict) -> pa.Schema:
    fields = [pa.field(f["name"], ARROW[f["type"]], nullable=bool(f["nullable"])) for f in schema["fields"]]
    return pa.schema(fields, metadata={k: (v if isinstance(v, str) else json.dumps(v)) for k, v in metadata.items()})


def _column(series: pd.Series, field: dict) -> pa.Array:
    kind = field["type"]
    values = series.tolist()
    if kind == "string":
        return pa.array([None if _is_null(v) else str(v) for v in values], type=pa.string())
    if kind == "decimal":
        for v in values:
            if not (_is_null(v) or isinstance(v, Decimal)):
                raise TypeError(f"{field['name']}: not a Decimal: {v!r}")
        return pa.array([None if _is_null(v) else v for v in values], type=ARROW[kind])
    if kind in INTEGER_KINDS:
        return pa.array([None if _is_null(v) else int(v) for v in values], type=ARROW[kind])
    if kind == "date":
        return pa.array([None if _is_null(v) else v for v in values], type=ARROW[kind])
    if kind == "datetime":
        return pa.array([None if _is_null(v) else v for v in values], type=ARROW[kind])
    if kind == "bool":
        return pa.array([None if _is_null(v) else bool(v) for v in values], type=ARROW[kind])
    raise ValueError(f"unsupported type {kind!r}")


def to_arrow(table: pd.DataFrame, schema: dict, arrow: pa.Schema) -> pa.Table:
    arrays = [_column(table[f["name"]], f) for f in schema["fields"]]
    return pa.Table.from_arrays(arrays, schema=arrow)


class ParquetWriter:
    """One Parquet file written one row group per part."""

    def __init__(self, schema: dict, path: Path, metadata: dict):
        self.schema, self.path = schema, Path(path)
        self.arrow = arrow_schema(schema, metadata)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.part = self.path.with_name(self.path.name + ".part")
        self._writer = pq.ParquetWriter(self.part, self.arrow, compression="zstd", write_statistics=True)
        self.rows = 0

    def write(self, table: pd.DataFrame) -> None:
        self._writer.write_table(to_arrow(table, self.schema, self.arrow))
        self.rows += len(table)

    def abort(self) -> None:
        """Close the writer and remove the part file after a failure."""
        self._writer.close()
        if self.part.exists():
            self.part.unlink()

    def close(self) -> str:
        self._writer.close()
        os.replace(self.part, self.path)
        return sha256(self.path)


def write_table(table: pd.DataFrame, schema: dict, path: Path, metadata: dict) -> str:
    writer = ParquetWriter(schema, path, metadata)
    writer.write(table)
    return writer.close()


def read_table(path: Path, row_group: int | None = None, columns: list | None = None) -> pd.DataFrame:
    """The saved Parquet as pandas with the build's own types: decimals as Decimal, integers
    nullable, dates as date, timestamps as datetime, strings as string."""
    file = pq.ParquetFile(path)
    table = file.read_row_group(row_group, columns=columns) if row_group is not None else file.read(columns=columns)
    frame = {}
    for field in table.schema:
        column = table.column(field.name)
        if pa.types.is_decimal(field.type):
            frame[field.name] = pd.Series(column.to_pylist(), dtype=object)
        elif pa.types.is_integer(field.type):
            frame[field.name] = pd.Series(column.to_pylist(), dtype="Int64")
        elif pa.types.is_boolean(field.type):
            frame[field.name] = pd.Series(column.to_pylist(), dtype="boolean")
        elif pa.types.is_date(field.type) or pa.types.is_timestamp(field.type):
            frame[field.name] = pd.Series(column.to_pylist(), dtype=object)
        else:
            frame[field.name] = pd.Series(column.to_pylist(), dtype="string")
    return pd.DataFrame(frame)


def readback_structure(path: Path, schema: dict, metadata: dict, report: Report, label: str = "readback.parquet") -> dict:
    """Reopen the saved file and compare its structure and metadata with the schema."""
    file = pq.ParquetFile(path)
    saved_schema = file.schema_arrow
    report.equal(f"{label}.column_names", saved_schema.names, [f["name"] for f in schema["fields"]])
    report.equal(f"{label}.column_types", [str(t) for t in saved_schema.types], [str(ARROW[f["type"]]) for f in schema["fields"]])
    report.equal(f"{label}.nullability", [f.nullable for f in saved_schema], [bool(f["nullable"]) for f in schema["fields"]])
    report.require()
    meta = saved_schema.metadata or {}
    expected_meta = arrow_schema(schema, metadata).metadata
    for key, expected in expected_meta.items():
        actual = meta.get(key)
        report.equal(f"{label}.metadata.{key.decode()}",
                     actual.decode("utf-8", errors="replace") if actual is not None else None, expected.decode())
    return {"table": schema["table"], "schema_version": schema["version"], "schema_sha256": schema["sha256"],
            "key": schema["key"], "rows": file.metadata.num_rows, "row_groups": file.metadata.num_row_groups,
            "columns": len(saved_schema.names), "sha256": sha256(path)}


def cells_equal(a, b) -> bool:
    if _is_null(a) and _is_null(b):
        return True
    if _is_null(a) or _is_null(b):
        return False
    if isinstance(a, dt.datetime) and isinstance(b, dt.datetime):
        return a == b
    return a == b


def compare_frames(saved: pd.DataFrame, accepted: pd.DataFrame, schema: dict) -> dict:
    """Per column, the number of cells that differ."""
    differences = {}
    for f in schema["fields"]:
        name = f["name"]
        a, b = saved[name].tolist(), accepted[name].tolist()
        n = sum(1 for x, y in zip(a, b) if not cells_equal(x, y))
        if n or len(a) != len(b):
            differences[name] = n if len(a) == len(b) else f"{len(a)} vs {len(b)} rows"
    return differences
