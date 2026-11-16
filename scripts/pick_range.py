"""Pick, from data/found.json, the recordings the owner approved for the library (2026-11-17):
 - obligatory prayers 14 Safar 1441 – 25 Muharram 1442 (before our channel opened)
 - Ramadan night prayers (taraweeh / tahajjud) 1436–1441, one entry per night, no multi-night compilations
One copy per prayer/night; nothing already in the library. Writes data/extras.json, overrides.json entries, data/alternates.json."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from parse_lib import parse, norm, digits
ROOT = os.path.join(os.path.dirname(__file__), '..')
L = lambda p, d: json.load(open(os.path.join(ROOT, p), encoding='utf8')) if os.path.exists(os.path.join(ROOT, p)) else d
F, data, meta, ovr = L('data/found.json', {}), L('data.json', {'items': []})['items'], L('meta.json', {}), L('overrides.json', {})
extras = L('data/extras.json', []); alts = L('data/alternates.json', {})
hk = lambda y, m, d: y * 10000 + m * 100 + d
LO, HI = hk(1441, 2, 14), hk(1442, 1, 25)
secs = lambda d: sum(int(p) * 60 ** i for i, p in enumerate(reversed((d or '0:00').split(':'))))

def eff(r):  # effective type/date of a library row (same layering as the site)
    o, m = ovr.get(r[0], {}), meta.get(r[0], {})
    t, y, mo, d = o.get('t', r[1]), r[2], r[3], r[4]
    if 'y' in o: y, mo, d = o['y'], o.get('m', 0), o.get('d', 0)
    if m.get('t') and m['t'] not in ('other',): t = m['t']
    if m.get('y') and (m.get('d') or not (y and mo and d)): y, mo, d = m['y'], m.get('m', 0), m.get('d', 0)
    return t, y, mo, d
have = {}
for r in data:
    t, y, mo, d = eff(r)
    have.setdefault((t, y, mo, d), []).append(r[0])

MULTI = re.compile(r'ليالي|مجموع|جميع|كامله|ساعات|ساعه|\d+\s*(و|-|الي|حتي)\s*\d+\s*رمضان|العشر|الاسبوع|اسبوع')
def night(T):
    m = re.search(r'ليله\s*(\d{1,2})', T) or re.search(r'(\d{1,2})\s*[-/]\s*9\s*[-/]\s*14\d\d', T) or re.search(r'(\d{1,2})\s*رمضان', T)
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 30 else 0

cands = {}
for vid, v in F.items():
    if v.get('status') != 'جديد' or v.get('note') or vid in extras: continue
    T = norm(digits(v['title']))
    p = parse(vid, v['title'] + ' ' + (v.get('dur') or '0:00'), 0)
    t, y, m, d = p['t'], p.get('y') or 0, p.get('m') or 0, p.get('d') or 0
    if t in ('fajr', 'maghrib', 'isha', 'jumuah') and y and m and d and LO <= hk(y, m, d) <= HI:
        key = (t, y, m, d)
    elif re.search(r'تراويح|تروايح|تهجد|قيام|رمضان', T) and (y or 0) in range(1436, 1442) and not MULTI.search(T) and secs(v.get('dur')) <= 2.5 * 3600:
        n = night(T) or (d if m == 9 else 0)
        key = ('taraweeh', y, 9, n)
    else: continue
    cands.setdefault(key, []).append((vid, v))

def rank(x):
    vid, v = x
    return (('مهنا' in v['channel']) + ('الحرمين' in v['channel'] or 'السنة النبوية' in v['channel']), secs(v.get('dur')), v.get('views') or 0)

added = []
for key, L_ in sorted(cands.items()):
    t, y, m, d = key
    if d and have.get(key): continue                       # already in the library
    L_.sort(key=rank, reverse=True)
    kept = []
    for vid, v in L_:
        s = secs(v.get('dur'))
        twin = next((k for k in kept if abs(secs(F[k].get('dur')) - s) <= 0.15 * max(s, 1)), None)
        if t != 'taraweeh' and kept: twin = kept[0]          # one copy per obligatory prayer
        if twin: alts.setdefault(twin, []).append(vid); continue
        kept.append(vid)
    for vid in kept:
        extras.append(vid); added.append((key, vid))
        ovr[vid] = {'t': t, 'y': y, 'm': m, 'd': d}
json.dump(extras, open(os.path.join(ROOT, 'data/extras.json'), 'w'), indent=0)
json.dump(ovr, open(os.path.join(ROOT, 'overrides.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
json.dump(alts, open(os.path.join(ROOT, 'data/alternates.json'), 'w'), indent=0)
import collections
print('added', len(added), collections.Counter((k[0], k[1]) for k, _ in added))
print('alternates', sum(len(v) for v in alts.values()))
for k, vid in added: print(k, vid, F[vid]['channel'][:18], '|', F[vid]['title'][:70], '|', F[vid].get('dur'))
