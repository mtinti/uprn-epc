"""Write every distinct non-empty UPRN from the EPC files with length, post town and local authority."""
import csv, glob, sys
csv.field_size_limit(10_000_000)
src, out = sys.argv[1], sys.argv[2]
seen = {}
for f in sorted(glob.glob(src + "/*.csv")):
    with open(f, encoding="utf-8-sig", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r); next(r)
        iu, it, ila, ipc = hdr.index("OSG_REFERENCE_NUMBER"), hdr.index("ADDRESS3"), hdr.index("LOCAL_AUTHORITY_LABEL"), hdr.index("POSTCODE")
        for row in r:
            u = row[iu].strip()
            if u and u not in seen:
                seen[u] = (row[it].strip(), row[ila].strip(), row[ipc].strip())
with open(out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["uprn", "len", "town", "la", "postcode"])
    for u, (t, la, pc) in seen.items():
        w.writerow([u, len(u), t, la, pc])
print(len(seen))
