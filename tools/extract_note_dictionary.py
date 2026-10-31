"""Draft epc_ingest/column_descriptions.yaml from the pinned publication note.

    python3 -P tools/extract_note_dictionary.py <publication_note.pdf> <out.yaml>

The note's data dictionary (pages 7 to 17 of the Q2 2026 note) defines 106 of the 107 published
fields, each as a group label, the machine name (`*` marks a Scotland-only field) and a
description. This script finds each machine name in published order, takes the text up to the
next entry as its description, strips the next entry's group label and the page numbers, and
writes one YAML entry per published column with attribution `note`, the page and the note's
hash. Three cases are handled by name: `ADDRESS3` is `POST_TOWN` in the note,
`3_YR_ENERGY_SAVINGS_POTENTIAL` is spelled without the S, and `DATA_ZONE_2011` has no entry and
gets attribution `project`. The key and derived columns get their schema description with
attribution `project`. The draft is reviewed by eye against the PDF before it is committed; the
review is recorded in docs/reviews/. Run with -P: the PDF is a download.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from epc_ingest import columns as col  # noqa: E402

NOTE_NAMES = {"ADDRESS3": "POST_TOWN", "3_YR_ENERGY_SAVINGS_POTENTIAL": "3_YR_ENERGY_SAVING_POTENTIAL"}
NOT_IN_NOTE = {"DATA_ZONE_2011": "Not defined in the publication note, which lists 106 data elements and omits this one. "
                                 "A 2011 data zone code (S01 and six digits) assigned by the register, checked by the build against the pinned 2011 data zone lookup."}
SHARED = re.compile(r"^(.*?)_(ENERGY_EFF|ENV_EFF)$")   # the element trios share one entry with their _DESCRIPTION


def pages_text(pdf: Path) -> list:
    return [(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]


# The note's own group label for each entry, typed from the PDF (pages 7 to 17). A label marks the
# first field of a group; the fields that follow it in the group have none. The layout puts a label
# before its field, or after it across a page break, so the text is stripped of these exact phrases
# at the seams between entries rather than guessed.
NOTE_LABELS = {
    "HISTORIC": "Historical", "BUILDING_REFERENCE_NUMBER": "Property UPRN", "OSG_REFERENCE_NUMBER": "OSG UPRN",
    "ADDRESS1": "Property Address", "POSTCODE": "Postcode", "INSPECTION_DATE": "Date of Assessment",
    "TYPE_OF_ASSESSMENT": "Type of Assessment", "LODGEMENT_DATE": "Date of Certificate",
    "ENERGY_CONSUMPTION_CURRENT": "Primary Energy Indicator", "TOTAL_FLOOR_AREA": "Total floor area",
    "3_YR_ENERGY_COST_CURRENT": "Total current energy costs over 3 years",
    "3_YR_ENERGY_SAVINGS_POTENTIAL": "Potential future savings over 3 years",
    "CURRENT_ENERGY_EFFICIENCY": "Current Energy Efficiency Rating", "CURRENT_ENERGY_RATING": "Current Energy Efficiency Band",
    "POTENTIAL_ENERGY_EFFICIENCY": "Potential Energy Efficiency Rating", "POTENTIAL_ENERGY_RATING": "Potential Energy Efficiency Band",
    "ENVIRONMENT_IMPACT_CURRENT": "Current Environmental Impact Rating", "CURRENT_ENVIRONMENTAL_RATING": "Current Environmental Impact Band",
    "ENVIRONMENT_IMPACT_POTENTIAL": "Potential Environmental Impact Rating", "POTENTIAL_ENVIRONMENTAL_RATING": "Potential Environmental Impact Band",
    "CO2_EMISS_CURR_PER_FLOOR_AREA": "CO2 Emissions Current Per Floor Area", "IMPROVEMENTS": "Improvements",
    "WALL_DESCRIPTION": "Element performance summary – Walls", "ROOF_DESCRIPTION": "Element performance summary – Roof",
    "FLOOR_DESCRIPTION": "Element performance summary – Floor", "WINDOWS_DESCRIPTION": "Element performance summary – Windows",
    "MAINHEAT_DESCRIPTION": "Element performance summary – Main heating",
    "MAINHEATCONT_DESCRIPTION": "Element performance summary – Main heating controls",
    "SECONDHEAT_DESCRIPTION": "Element performance summary – Secondary heating",
    "HOTWATER_DESCRIPTION": "Element performance summary – Hot water", "LIGHTING_DESCRIPTION": "Element performance summary – Lighting",
    "AIR_TIGHTNESS_DESCRIPTION": "Element performance summary – Air tightness",
    "CO2_EMISSIONS_CURRENT": "Carbon dioxide emissions – Current", "CO2_EMISSIONS_POTENTIAL": "Carbon dioxide emissions – Potential Reduction",
    "HEATING_COST_CURRENT": "Current heating cost over 3 years", "HEATING_COST_POTENTIAL": "Potential heating cost over 3 years",
    "HOT_WATER_COST_CURRENT": "Current hot water cost over 3 years", "HOT_WATER_COST_POTENTIAL": "Potential hot water cost over 3 years",
    "LIGHTING_COST_CURRENT": "Current lighting cost over 3 years", "LIGHTING_COST_POTENTIAL": "Potential lighting cost over 3 years",
    "ALTERNATIVE_IMPROVEMENTS": "Alternative Measures 2", "LZC_ENERGY_SOURCES": "Low and zero carbon energy sources",
    "SPACE_HEATING_DEMAND": "Heat demand – Space heating, existing dwelling",
    "WATER_HEATING_DEMAND": "Heat demand – Water heating, existing dwelling",
    "IMPACT_LOFT_INSULATION": "Heat demand – Space heating, impact of loft insulation",
    "IMPACT_CAVITY_WALL_INSULATION": "Heat demand – Space heating, impact of cavity wall insulation",
    "IMPACT_SOLID_WALL_INSULATION": "Heat demand – Space heating, impact of solid wall insulation",
    "ADDENDUM_TEXT": "Addendum text", "CONSTRUCTION_AGE_BAND": "Part 1 Construction Age Band", "FLOOR_HEIGHT": "Part 1 Floor 0 Room Height",
    "DATA_ZONE": "Data Zone", "ENERGY_CONSUMPTION_POTENTIAL": "Energy Consumption Potential", "EXTENSION_COUNT": "Extensions Count",
    "FIXED_LIGHTING_OUTLETS_COUNT": "Fixed Lighting Outlets Count", "LOW_ENERGY_FIXED_LIGHT_COUNT": "Low Energy Lighting Outlets Count",
    "LOW_ENERGY_LIGHTING": "Low Energy Lighting %", "FLOOR_LEVEL": "Flat Level", "FLAT_TOP_STOREY": "Flat Location", "GLAZED_AREA": "Glazed Area",
    "NUMBER_HABITABLE_ROOMS": "Habitable Room Count", "HEAT_LOSS_CORRIDOOR": "Heat Loss Corridor", "NUMBER_HEATED_ROOMS": "Heated Room Count",
    "LOCAL_AUTHORITY_LABEL": "Local Authority", "MAINS_GAS_FLAG": "Mains Gas", "MAIN_HEATING_CATEGORY": "Main heating",
    "MAIN_FUEL": "Main heating fuel type", "MAIN_HEATING_CONTROLS": "Main Heating 1 Control", "MECHANICAL_VENTILATION": "Mechanical Ventilation",
    "ENERGY_TARIFF": "Meter Type", "MULTI_GLAZE_PROPORTION": "Multiple Glazed Proportion", "GLAZED_TYPE": "Multiple Glazing Type",
    "NUMBER_OPEN_FIREPLACES": "Open Fireplaces Count", "PHOTO_SUPPLY": "Photovoltaic Supply", "SOLAR_WATER_HEATING_FLAG": "Solar Water Heating",
    "TENURE": "Tenure", "TRANSACTION_TYPE": "Transaction Type", "UNHEATED_CORRIDOR_LENGTH": "Unheated Corridor Length",
    "CONSTITUENCY": "Ward Code", "CONSTITUENCY_LABEL": "Ward Name", "WIND_TURBINE_COUNT": "Wind Turbines Count",
    "BUILT_FORM": "Built Form", "PROPERTY_TYPE": "Property Type", "CREATED_AT": "Created At", "REPORT_REFERENCE_NUMBER": "RRN",
}


def _tokens(text: str) -> list:
    return text.replace("**", " ").split()


def _norm(tok: str) -> str:
    return tok.strip("*–-:,.()").lower()


def tidy(segment: str) -> list:
    """Tokens of a segment without page numbers and the repeated table header."""
    lines = [l.rstrip() for l in segment.split("\n")]
    lines = [l for l in lines if l.strip() and not re.fullmatch(r"\d{1,2}", l.strip()) and not l.startswith("Data element")]
    return _tokens(" ".join(lines))


def strip_label(prev: list, cur: list, label: str) -> tuple:
    """Remove `label` where it sits across the seam between two consecutive segments: its first
    j tokens at the end of `prev`, the rest at the start of `cur`, for the j that fits. Returns
    the two token lists and whether the label was found."""
    want = [_norm(t) for t in label.split()]
    for j in range(len(want), -1, -1):
        head, tail = want[:j], want[j:]
        if (not head or [_norm(t) for t in prev[len(prev) - len(head):]] == head) and \
           (not tail or [_norm(t) for t in cur[:len(tail)]] == tail):
            return (prev[:len(prev) - len(head)] if head else prev), cur[len(tail):], True
    return prev, cur, False


def main(argv) -> int:
    pdf, out = Path(argv[1]), Path(argv[2])
    pages = pages_text(pdf)
    text = "\n".join(pages)
    offsets, pos = [], 0
    for p in pages:
        offsets.append(pos); pos += len(p) + 1
    start = text.find("Data dictionary")
    end = text.find("Further information", start)
    published = col.load_published()
    names = [c["name"] for c in published]
    labels = {c["name"]: c["label"] for c in published}
    matches, cursor = [], start
    for name in names:
        if name in NOT_IN_NOTE:
            matches.append((name, None, None)); continue
        note_name = NOTE_NAMES.get(name, name)
        m = re.compile(r"(?<![A-Z0-9_])" + re.escape(note_name) + r"\*?(?![A-Z0-9_])").search(text, cursor, end)
        if not m:
            raise SystemExit(f"{name} ({note_name}) not found in the note after offset {cursor}")
        matches.append((name, m.start(), m.end())); cursor = m.end()
    # Segments: the text after each name up to the next name. Labels are then stripped at the seams.
    segs = []
    for k, (name, s_, e) in enumerate(matches):
        if s_ is None:
            segs.append(None); continue
        nxt_start = next((ss for _, ss, _ in matches[k + 1:] if ss is not None), end)
        segs.append(tidy(text[e:nxt_start]))
    lead = tidy(text[start:matches[0][1]].split("Description", 1)[-1])
    found = {}
    for k, (name, s_, e) in enumerate(matches):
        if s_ is None or name not in NOTE_LABELS:
            continue
        label = NOTE_LABELS[name]
        prev_k = next((i for i in range(k - 1, -1, -1) if segs[i] is not None), None)
        prev = segs[prev_k] if prev_k is not None else lead
        prev, cur, ok = strip_label(prev, segs[k], label)
        if not ok:      # a page break put the label after the field: look at the end of its own segment
            cur2, _, ok = strip_label(segs[k], [], label)
            if ok:
                cur = cur2
        if prev_k is not None:
            segs[prev_k] = prev
        else:
            lead = prev
        segs[k] = cur
        found[name] = ok
    missing = [n for n, ok in found.items() if not ok]
    if missing:
        raise SystemExit(f"labels not found at a seam: {missing}")
    entries = []
    for k, (name, s_, e) in enumerate(matches):
        if s_ is None:
            entries.append({"name": name, "attribution": "project", "text": NOT_IN_NOTE[name]}); continue
        page = max(i for i, o in enumerate(offsets) if o <= s_) + 1
        entry = {"name": name, "attribution": "note", "note_name": text[s_:e].rstrip("*"), "scotland_only": text[s_:e].endswith("*"),
                 "page": page, "text": " ".join(segs[k]).strip()}
        if name in NOTE_LABELS:
            entry["note_label"] = NOTE_LABELS[name]
        entries.append(entry)
    # Element trios: a blank _ENERGY_EFF or _ENV_EFF entry shares the _DESCRIPTION entry.
    by_name = {e["name"]: e for e in entries}
    for e in entries:
        m = SHARED.match(e["name"])
        if m and not e.get("text"):
            desc_name = m.group(1) + "_DESCRIPTION"
            if desc_name not in by_name and m.group(1) in ("MAINHEATC", "SHEATING", "HOT_WATER"):
                desc_name = {"MAINHEATC": "MAINHEATCONT_DESCRIPTION", "SHEATING": "SECONDHEAT_DESCRIPTION", "HOT_WATER": "HOTWATER_DESCRIPTION"}[m.group(1)]
            e["shared_entry"] = desc_name
            e["text"] = by_name[desc_name]["text"]
            e["page"] = by_name[desc_name]["page"]
            e.pop("note_label", None)
    schema = yaml.safe_load((ROOT / "epc_ingest" / "output_schema.yaml").read_text())
    for f in schema["fields"]:
        if f["group"] != "published":
            entries.append({"name": f["name"], "attribution": "project", "text": f["description"]})
    doc = {"version": 1,
           "note": {"file": "epc_2026Q2/publication_note.pdf", "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    "title": "Domestic EPC extended historic data publication note, Q2 2026 extract, Scottish Government",
                    "licence": "Open Government Licence v3.0; quoted with attribution"},
           "review": None,
           "columns": entries}
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=110))
    print(f"wrote {out}: {len(entries)} entries, {sum(1 for e in entries if e['attribution'] == 'note')} from the note")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
