"""For each UPRN length in the EPC set, count how many exist in OS Open UPRN, and whether the
padded 12-digit reading would exist instead. Also report the coordinate bounding box of the
8-digit matches."""
import csv, sys
epc_file, os_file = sys.argv[1], sys.argv[2]
epc = {}
for r in csv.DictReader(open(epc_file)):
    epc[int(r["uprn"])] = r["len"]
found = {}; bbox = {}
with open(os_file, newline="", encoding="utf-8-sig") as fh:
    r = csv.reader(fh); hdr = next(r)
    iu, ix, iy = hdr.index("UPRN"), hdr.index("X_COORDINATE"), hdr.index("Y_COORDINATE")
    for row in r:
        u = int(row[iu])
        L = epc.get(u)
        if L is not None:
            found[L] = found.get(L, 0) + 1
            if L == "8":
                x, y = float(row[ix]), float(row[iy])
                b = bbox.setdefault("8", [x, x, y, y])
                b[0] = min(b[0], x); b[1] = max(b[1], x); b[2] = min(b[2], y); b[3] = max(b[3], y)
total = {}
for L in epc.values(): total[L] = total.get(L, 0) + 1
for L in sorted(total, key=int):
    print(f"len {L}: {found.get(L,0)} of {total[L]} found in OS Open UPRN ({100*found.get(L,0)/total[L]:.2f}%)")
print("8-digit matches bbox (easting min,max, northing min,max):", bbox.get("8"))
