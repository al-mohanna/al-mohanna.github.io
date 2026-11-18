"""Turn data/records.json (the reviewed records file) into meta.json, a fill-in layer
the site applies under the title parse and overrides.json: surahs/dates where the title
has none, verse ranges, Shorts flags, prayer types for unclassified items, external videos."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from parse_lib import SURAH, MONTHS, norm, digits
ROOT = os.path.join(os.path.dirname(__file__), '..')
NS = [norm(s) for s in SURAH]

def surahs(t):
    t = norm(t); out = []
    toks = [x for x in re.split(r'[\s،,:;()/\-–]+', t) if x]
    i = 0
    while i < len(toks):
        hit = None
        if i + 1 < len(toks) and toks[i] + ' ' + toks[i + 1] in NS: hit = toks[i] + ' ' + toks[i + 1]; i += 1
        else:
            w = toks[i]
            for c in (w, w[1:] if w.startswith('و') else ''):
                if c and c in NS: hit = c; break
        if hit and NS.index(hit) + 1 not in out: out.append(NS.index(hit) + 1)
        i += 1
    return out

def date(t):
    t = norm(digits(t)); m = None
    for k, vs in MONTHS:
        if any(v in t for v in vs): m = k; break
    if m is None and 'رمضان' in t: m = 9
    nums = [int(x) for x in re.findall(r'\d+', t)]
    y = next((x for x in nums if 1400 < x < 1500), 0)
    d = next((x for x in nums if x <= 30), 0) if m else 0
    return y, m or 0, d

TYPE = [('Shorts', 'short'), ('خطبة', 'khutbah'), ('استسقاء', 'istisqa'), ('عيد الأضحى', 'adha'), ('عيد الفطر', 'fitr'),
        ('تراويح', 'taraweeh'), ('تهجد', 'taraweeh'), ('ختمة', 'taraweeh'), ('الفجر', 'fajr'), ('المغرب', 'maghrib'),
        ('العشاء', 'isha'), ('الجمعة', 'jumuah'), ('المصحف', 'murattal'), ('إصدار', 'collection'),
        ('محاضرة', 'lecture'), ('درس', 'lecture'), ('دورة', 'lecture'), ('ندوة', 'lecture'), ('كلمة', 'lecture')]

def kind(p):
    for k, t in TYPE:
        if k in p: return t
    return 'other'

def verses(s):
    m = re.search(r'\(([^()]{2,40})\)\s*$', s)
    if not m: return ''
    v = m.group(1).strip()
    if '(' in v or 'حسب' in v: return ''
    return v

ORD = {'الاولي': 1, 'الاول': 1, 'الثانيه': 2, 'الثاني': 2, 'الثالثه': 3, 'الثالث': 3, 'الرابعه': 4, 'الخامسه': 5, 'السادسه': 6, 'السابعه': 7,
       'الثامنه': 8, 'التاسعه': 9, 'العاشره': 10, 'الحاديه عشر': 11, 'الثانيه عشر': 12, 'الثالثه عشر': 13, 'الرابعه عشر': 14,
       'الخامسه عشر': 15, 'السادسه عشر': 16, 'السابعه عشر': 17, 'الثامنه عشر': 18, 'التاسعه عشر': 19, 'العشرين': 20}

def night(t):
    """Ramadan night number from 'ليلة 28' or 'الليلة الثامنة'."""
    t = norm(digits(t))
    m = re.search(r'ليله\s*(\d{1,2})\b', t)
    if m and 1 <= int(m.group(1)) <= 30: return int(m.group(1))
    for w in sorted(ORD, key=len, reverse=True):
        if re.search(r'ليله\s+' + w + r'(\s|$)', t) or re.search(r'(ليله|ليالي)\s+' + w, t): return ORD[w]
    return 0

def main():
    R = json.load(open(os.path.join(ROOT, 'data/records.json'), encoding='utf8'))['records']
    out = {}
    for x in R:
        y, m, d = date(x['date_hijri'])
        if y and not m and kind(x['prayer']) == 'taraweeh': m = 9
        if y and m == 9 and not d: d = night(x['date_hijri']) or night(x['title'])
        e = {'t': kind(x['prayer']), 's': surahs(x['surah']), 'y': y, 'm': m, 'd': d}
        v = re.sub(r'^سور:\s*', '', x['surah']).strip()
        if v and len(v) <= 160: e['v'] = v
        if 'كاملة' in x['surah']: e['full'] = 1
        out[x['video_id']] = {k: v for k, v in e.items() if v or k == 's' and 'k' in e}
    json.dump(out, open(os.path.join(ROOT, 'meta.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('meta', len(out), 'shorts', sum(1 for v in out.values() if v.get('t') == 'short'))

if __name__ == '__main__': main()
