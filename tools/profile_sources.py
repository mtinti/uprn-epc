"""Profile every annual EPC CSV: rows, widths, key fields, dates, geography shapes, duplicates."""
import csv, sys, collections, re, json, os
csv.field_size_limit(10**9)
root = sys.argv[1]
out = {}
rrn_all = collections.Counter()
uprn_rrn = set()
for name in sorted(os.listdir(root)):
    if not name.endswith('.csv'): continue
    path = os.path.join(root, name)
    stats = dict(file=name, rows=0, widths=collections.Counter(), historic=collections.Counter(), toa=collections.Counter(),
                 dz_shape=collections.Counter(), dz11_shape=collections.Counter(), pc_shape=collections.Counter(),
                 lodg_year=collections.Counter(), created_year=collections.Counter(), insp_shape=collections.Counter(),
                 rrn_empty=0, uprn_empty=0, bad_decode=0, rows_with_replacement_char=0, tfa_out_of_range=0, lodg_before_insp=0, rrn_shape=collections.Counter(), uprn_shape=collections.Counter(), cur_eff_shape=collections.Counter(), rating=collections.Counter(),
                 tenure=collections.Counter(), ptype=collections.Counter(), txn=collections.Counter(), rrn_dup_in_file=0,
                 header_sha=None)
    seen = set()
    raw = open(path, 'rb')
    # decode cp1252 so every byte maps; count bytes >= 0x80 that are not valid utf-8 separately
    import io
    text = io.TextIOWrapper(raw, encoding='utf-8-sig', errors='replace', newline='')
    r = csv.reader(text)
    h = next(r); h[0] = h[0].lstrip('﻿')
    labels = next(r)
    stats['ncols'] = len(h)
    idx = {c: i for i, c in enumerate(h)}
    def shape(s):
        s = s.strip()
        if s == '': return '<empty>'
        s = re.sub(r'[A-Z]', 'A', s); s = re.sub(r'[a-z]', 'a', s); s = re.sub(r'[0-9]', '9', s)
        return s[:40]
    for row in r:
        stats['rows'] += 1
        stats['widths'][len(row)] += 1
        if len(row) != len(h): continue
        g = lambda c: row[idx[c]]
        stats['historic'][g('HISTORIC')] += 1
        stats['toa'][g('TYPE_OF_ASSESSMENT')] += 1
        stats['dz_shape'][shape(g('DATA_ZONE'))] += 1
        stats['dz11_shape'][shape(g('DATA_ZONE_2011'))] += 1
        stats['pc_shape'][shape(g('POSTCODE'))] += 1
        stats['lodg_year'][g('LODGEMENT_DATE')[:4]] += 1
        stats['created_year'][g('CREATED_AT')[6:10]] += 1
        stats['insp_shape'][shape(g('INSPECTION_DATE'))] += 1
        stats['cur_eff_shape'][shape(g('CURRENT_ENERGY_EFFICIENCY'))] += 1
        stats['rating'][g('CURRENT_ENERGY_RATING')] += 1
        stats['tenure'][g('TENURE')] += 1
        stats['ptype'][g('PROPERTY_TYPE')] += 1
        stats['txn'][g('TRANSACTION_TYPE')] += 1
        rrn = g('REPORT_REFERENCE_NUMBER'); up = g('BUILDING_REFERENCE_NUMBER')
        if rrn == '': stats['rrn_empty'] += 1
        else:
            if rrn in seen: stats['rrn_dup_in_file'] += 1
            seen.add(rrn); rrn_all[rrn] += 1
        if up == '': stats['uprn_empty'] += 1
        stats['rrn_shape'][shape(rrn)] += 1; stats['uprn_shape'][shape(up)] += 1
        if any('\ufffd' in c for c in row): stats['rows_with_replacement_char'] += 1
        try:
            tfa = float(g('TOTAL_FLOOR_AREA'))
            if tfa < 15 or tfa > 1500: stats['tfa_out_of_range'] += 1
        except ValueError: pass
        if g('LODGEMENT_DATE') < g('INSPECTION_DATE'): stats['lodg_before_insp'] += 1
    for k in list(stats):
        if isinstance(stats[k], collections.Counter):
            stats[k] = dict(stats[k].most_common(12))
    out[name] = stats
    print(json.dumps(stats), flush=True)
dups = sum(1 for v in rrn_all.values() if v > 1)
print(json.dumps({'rrn_total_distinct': len(rrn_all), 'rrn_in_more_than_one_row_overall': dups}))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'profile.json'), 'w'), indent=1)
