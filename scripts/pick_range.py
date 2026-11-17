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
    if not y:                                                 # «… ليلة 20 رمضان … لعام 1440هـ»: year far from the month
        my = re.search(r'(?<!\d)(14[34]\d)(?!\d)', T)
        y = int(my.group(1)) if my else 0
    if t in ('fajr', 'maghrib', 'isha', 'jumuah') and y and m and d and LO <= hk(y, m, d) <= HI:
        key = (t, y, m, d)
    elif re.search(r'تراويح|تروايح|تهجد|قيام|رمضان', T) and (y or 0) in range(1436, 1442) and not MULTI.search(T) and secs(v.get('dur')) <= 2.5 * 3600:
        n = night(T) or (d if m == 9 else 0)
        key = ('taraweeh', y, 9, n)
    else: continue
    cands.setdefault(key, []).append((vid, v))

def dur_of(vid):
    if vid in F and F[vid].get('dur'): return secs(F[vid]['dur'])
    r = next((r for r in data if r[0] == vid), None)
    return secs(r[7]) if r else 0

def rank(vid):   # the most complete recording first, then channels dedicated to the Sheikh / the Two Mosques
    v = F.get(vid, {})
    ch = v.get('channel', '')
    return (dur_of(vid), ('مهنا' in ch) + ('الحرمين' in ch or 'السنة النبوية' in ch), v.get('views') or 0)

own_ids = {r[0] for r in data if not (len(r) > 12 and r[12])}      # recordings from our own channel
added, swapped = [], []
for key, L_ in sorted(cands.items()):
    t, y, m, d = key
    if t == 'taraweeh' and not d:                                 # no night number: only a long recording, never a clip
        L_ = [(vid, v) for vid, v in L_ if dur_of(vid) >= 20 * 60]
        if not L_: continue
    lib = [x for x in have.get(key, []) if d]                     # what the library already has for this prayer/night
    if any(x in own_ids for x in lib): continue                   # our channel's copy stays the main one
    pool = [vid for vid, _ in L_] + [x for x in lib if x in extras]
    best = max(pool, key=rank)
    cur = [x for x in lib if x in extras]
    if cur and best in cur: 
        for vid, _ in L_: alts.setdefault(best, []).append(vid)
        continue
    if cur and dur_of(best) < 1.3 * max(dur_of(x) for x in cur): # not clearly longer: keep what we have
        for vid, _ in L_: alts.setdefault(cur[0], []).append(vid)
        continue
    for x in cur:                                                 # a fuller copy replaces the short one
        extras.remove(x); ovr.pop(x, None); alts.setdefault(best, []).append(x); swapped.append((key, x, best))
    for vid, _ in L_:
        if vid != best: alts.setdefault(best, []).append(vid)
    extras.append(best); added.append((key, best))
    ovr[best] = {'t': t, 'y': y, 'm': m, 'd': d}
for k in alts: alts[k] = sorted(set(alts[k]) - {k})
json.dump(extras, open(os.path.join(ROOT, 'data/extras.json'), 'w'), indent=0)
json.dump(ovr, open(os.path.join(ROOT, 'overrides.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
json.dump(alts, open(os.path.join(ROOT, 'data/alternates.json'), 'w'), indent=0)
import collections
print('added', len(added), collections.Counter((k[0], k[1]) for k, _ in added), '| replaced', len(swapped))
for k, old, new in swapped: print('replaced', k, old, '->', new)
print('alternates', sum(len(v) for v in alts.values()))
for k, vid in added: print(k, vid, F[vid]['channel'][:18], '|', F[vid]['title'][:70], '|', F[vid].get('dur'))
