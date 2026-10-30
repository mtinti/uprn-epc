"""The source registry: what is pinned, where it comes from, and how to verify it."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from .checks import Report

PACKAGE = Path(__file__).resolve().parent.parent
ROOT = PACKAGE.parent
REGISTRY = PACKAGE / "sources.yaml"
SOURCE_ROOT = ROOT / "data" / "sources"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Registry:
    path: Path
    sha256: str
    root: Path
    publisher: str
    licence: str
    attribution: list
    redistribution: str
    publisher_pages: dict
    release: dict
    datazone_lists: dict

    @property
    def epc_release(self) -> str:
        return self.release["epc_release"]

    @property
    def members(self) -> tuple:
        return tuple(self.release["members"])


def load_registry(path: Path = REGISTRY, root: Path = SOURCE_ROOT) -> Registry:
    raw = yaml.safe_load(Path(path).read_text())
    if raw.get("version") != 1:
        raise ValueError(f"Unsupported registry version {raw.get('version')!r}")
    if raw["redistribution"] not in ("upload", "cite", "restricted"):
        raise ValueError(f"Unknown redistribution setting {raw['redistribution']!r}")
    years = [m["year"] for m in raw["release"]["members"]]
    if len(set(years)) != len(years):
        raise ValueError("duplicate member year in the registry")
    if years != sorted(years):
        raise ValueError("members must be listed in year order")
    return Registry(Path(path), sha256(path), Path(root), raw["publisher"], raw["licence"],
                    list(raw["attribution"]), raw["redistribution"], dict(raw["publisher_pages"]),
                    dict(raw["release"]), {int(k): dict(v) for k, v in raw["datazone_lists"].items()})


def verify(registry: Registry, report: Report, archive: bool = False) -> None:
    """Every member the build reads is present with its pinned hash. A changed byte stops the
    build. The archive and the note are hashed only on request (`archive=True`): the archive
    is 535 MB and the build never reads it."""
    pins = [(m["file"], m["sha256"]) for m in registry.members]
    for spec in registry.datazone_lists.values():
        pins.append((spec["file"], spec["sha256"]))
    if archive:
        pins += [(registry.release["archive"]["file"], registry.release["archive"]["sha256"]),
                 (registry.release["note"]["file"], registry.release["note"]["sha256"])]
    for rel, expected in pins:
        path = registry.root / rel
        if not path.is_file():
            report.add(f"source.{rel}", False, "missing")
            continue
        actual = sha256(path)
        report.equal(f"source.{rel}", actual, expected,
                     detail="sha256 matches" if actual == expected else f"sha256 {actual[:16]} differs from pin")
    report.require()
