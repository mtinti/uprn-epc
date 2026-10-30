"""Per-column profile over every file: max length, empties, whether every value is an int, a decimal, a date, and distinct count up to a cap."""
import csv, sys, os, json, re, collections
csv.field_size_limit(10**9)
root = sys.argv[1]
INT = re.compile(r'^-?\d+$'); DEC = re.compile(r'^-?\d+\.\d+$'); DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$'); TS = re.compile(r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$')
stats = None
for name in sorted(f for f in os.listdir(root) if f.endswith('.csv')):
    with open(os.path.join(root, name), encoding='utf-8-sig', newline='') as f:
        r = csv.reader(f); h = next(r); next(r)
        if stats is None:
            stats = {c: dict(max_len=0, empty=0, n=0, int=0, dec=0, date=0, ts=0, neg=0, distinct=set(), max_int=None, min_int=None, dec_places=0, newline=0, pipe=0, quote=0) for c in h}
        for row in r:
            for c, v in zip(h, row):
                s = stats[c]; s['n'] += 1
                if v == '': s['empty'] += 1; continue
                L = len(v)
                if L > s['max_len']: s['max_len'] = L
                if INT.match(v):
                    s['int'] += 1; iv = int(v)
                    s['max_int'] = iv if s['max_int'] is None or iv > s['max_int'] else s['max_int']
                    s['min_int'] = iv if s['min_int'] is None or iv < s['min_int'] else s['min_int']
                elif DEC.match(v):
                    s['dec'] += 1; s['dec_places'] = max(s['dec_places'], len(v.split('.')[1]))
                elif DATE.match(v): s['date'] += 1
                elif TS.match(v): s['ts'] += 1
                if '\n' in v: s['newline'] += 1
                if '|' in v: s['pipe'] += 1
                if '"' in v: s['quote'] += 1
                if len(s['distinct']) <= 200: s['distinct'].add(v)
    print(name, flush=True)
out = {}
for c, s in stats.items():
    d = s.pop('distinct'); s['distinct_capped'] = len(d); s['examples'] = sorted(d)[:12] if len(d) <= 200 else []
    out[c] = s
json.dump(out, open('columns.json', 'w'), indent=1)
print('done')
