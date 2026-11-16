"""Collect every YouTube video of Sheikh Dr. Khalid Al-Muhanna from ANY channel.
Runs nightly in GitHub Actions and resumes where it stopped (YouTube allows ~100 searches a day).
1) many searches (name spellings x topics x years), 2) then every upload of channels that publish him.
Writes data/found.json (all finds) and data/found.csv (opens in Excel) with a status per video."""
import json, os, re, sys, csv, urllib.request, urllib.parse, urllib.error, datetime
sys.path.insert(0, os.path.dirname(__file__))
from parse_lib import norm

KEY = os.environ.get('YOUTUBE_API_KEY')
API = 'https://www.googleapis.com/youtube/v3/'
ROOT = os.path.join(os.path.dirname(__file__), '..')
OWN = '@khalid_almihana'
MAX_SEARCH = int(os.environ.get('MAX_SEARCH', '70'))     # 100 units each
MAX_PAGES = int(os.environ.get('MAX_PAGES', '600'))      # 1 unit each (channel uploads, details)

class Quota(Exception): pass
used = {'search': 0, 'cheap': 0}

def get(path, cheap=True, **q):
    if cheap:
        if used['cheap'] >= MAX_PAGES: raise Quota('page budget')
        used['cheap'] += 1
    else:
        if used['search'] >= MAX_SEARCH: raise Quota('search budget')
        used['search'] += 1
    q['key'] = KEY
    try:
        with urllib.request.urlopen(API + path + '?' + urllib.parse.urlencode(q), timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf8', 'ignore')
        if e.code == 403 and 'quota' in body.lower(): raise Quota('daily quota')
        raise

# ---- is this video about our Sheikh? ----
NAME = re.compile(r'مهنا|muhanna|mohanna|mehanna|mihana|muhana|mohana', re.I)
HOMONYM = re.compile(r'محنا|محنّا|mahna\b|mhna\b', re.I)      # «خالد محنا» – a different person (audio producer)
HARAM = re.compile(r'نبوي|حرم|مسجد|تلاو|صلاه|صلاة|تراويح|تهجد|قيام|فجر|مغرب|عشاء|جمعه|جمعة|خطبه|خطبة|سوره|سورة|quran|recit|prayer|madinah|nabawi|haram|taraweeh|surah', re.I)

def relevant(sn):
    t = sn.get('title', '') + ' ' + sn.get('description', '')[:600] + ' ' + sn.get('channelTitle', '')
    if not NAME.search(t) and not NAME.search(norm(t)): return None
    note = ''
    if HOMONYM.search(t) and not re.search(r'مهنا', t): note = 'قد يكون «خالد محنا» (شخص آخر)'
    elif not HARAM.search(t): note = 'لا يظهر أنه تلاوة'
    return note

def tasks():
    names = ['خالد المهنا', 'الشيخ خالد المهنا', 'خالد بن سليمان المهنا', 'د. خالد المهنا', 'المهنا المسجد النبوي',
             'Khalid Al-Muhanna', 'Khaled Almohanna', 'Khalid Almuhanna', 'Khaled Al Muhanna', 'Sheikh Khalid Al Muhanna']
    topics = ['تلاوة', 'تراويح', 'تهجد', 'قيام الليل', 'صلاة الفجر', 'صلاة المغرب', 'صلاة العشاء', 'خطبة الجمعة', 'دعاء القنوت',
              'سورة', 'المصحف المرتل', 'تلاوة خاشعة', 'ختم القرآن', 'استسقاء', 'عيد']
    T = [(n, None) for n in names]
    T += [(f'خالد المهنا {t}', None) for t in topics]
    for y in range(1436, 1449):
        T += [(f'المهنا تراويح {y}', None), (f'خالد المهنا {y}', None)]
    for gy in range(2014, 2027):                      # split by year to get past YouTube's 500-results limit
        T += [(n, gy) for n in ['خالد المهنا', 'Khalid Al-Muhanna']]
    return T

def main():
    if not KEY: sys.exit('YOUTUBE_API_KEY missing')
    fpath, spath = os.path.join(ROOT, 'data/found.json'), os.path.join(ROOT, 'data/collect_state.json')
    try: F = json.load(open(fpath, encoding='utf8'))
    except Exception: F = {}
    try: S = json.load(open(spath, encoding='utf8'))
    except Exception: S = {'done': [], 'chan_done': [], 'own': ''}
    lib = {r[0] for r in json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf8'))['items']}
    try:
        if not S.get('own'):
            S['own'] = get('channels', part='id', forHandle=OWN)['items'][0]['id']
        new_ids = []

        def keep(vid, sn, how):
            note = relevant(sn)
            if note is None: return False
            if vid not in F:
                F[vid] = {'title': sn['title'], 'channel': sn.get('channelTitle', ''), 'cid': sn.get('channelId', ''),
                          'up': sn.get('publishedAt', '')[:10], 'how': how, 'note': note}
                new_ids.append(vid)
            return True

        def channels():
            # 1) every upload of channels that publish the Sheikh (cheap: 1 unit per 50 videos)
            seeds = {}
            for v in F.values():
                if v['cid'] and v['cid'] != S['own'] and not v['note']: seeds[v['cid']] = seeds.get(v['cid'], 0) + 1
            for cid, n in sorted(seeds.items(), key=lambda x: -x[1]):
                if cid in S['chan_done'] or n < 3: continue
                up = get('channels', part='contentDetails', id=cid)['items']
                if up:
                    pl, token = up[0]['contentDetails']['relatedPlaylists']['uploads'], None
                    while True:
                        p = dict(part='snippet', playlistId=pl, maxResults=50)
                        if token: p['pageToken'] = token
                        r = get('playlistItems', **p)
                        for it in r.get('items', []):
                            sn = it['snippet']; sn['channelId'] = cid
                            sn['channelTitle'] = sn.get('videoOwnerChannelTitle') or sn.get('channelTitle', '')
                            keep(sn['resourceId']['videoId'], sn, 'قناة: ' + sn['channelTitle'])
                        token = r.get('nextPageToken')
                        if not token: break
                S['chan_done'].append(cid)
        channels()
        # 2) searches
        for q, gy in tasks():
            key = f'{q}|{gy or ""}'
            if key in S['done']: continue
            token, dry = None, 0
            for _ in range(10):
                p = dict(part='snippet', q=q, type='video', maxResults=50, relevanceLanguage='ar')
                if gy: p.update(publishedAfter=f'{gy}-01-01T00:00:00Z', publishedBefore=f'{gy+1}-01-01T00:00:00Z')
                if token: p['pageToken'] = token
                r = get('search', cheap=False, **p)
                hits = sum(keep(it['id']['videoId'], it['snippet'], 'بحث: ' + q) for it in r.get('items', []) if it['id'].get('videoId'))
                dry = dry + 1 if hits == 0 else 0
                token = r.get('nextPageToken')
                if not token or dry >= 2: break
            S['done'].append(key)

        channels()   # channels discovered by tonight's searches
        S['complete'] = True
    except Quota as e:
        S['complete'] = False
        print('stopped:', e)
    finally:
        # details for videos without them (duration, views, description start)
        need = [k for k, v in F.items() if 'dur' not in v]
        try:
            for i in range(0, len(need), 50):
                for it in get('videos', part='contentDetails,statistics,snippet', id=','.join(need[i:i+50])).get('items', []):
                    v = F[it['id']]
                    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', it['contentDetails'].get('duration') or '')
                    d, h, mi, se = (int(x or 0) for x in m.groups()) if m else (0, 0, 0, 0)
                    h += 24 * d
                    v['dur'] = f'{h}:{mi:02d}:{se:02d}' if h else f'{mi}:{se:02d}'
                    v['views'] = int(it.get('statistics', {}).get('viewCount', 0) or 0)
                    v['desc'] = re.sub(r'\s+', ' ', it['snippet'].get('description', ''))[:220]
        except Quota: pass
        own = S.get('own')
        for k, v in F.items():
            v['status'] = 'في المكتبة' if k in lib else ('قناة الشيخ – سيُضاف تلقائياً' if v['cid'] == own else 'جديد')
        json.dump(F, open(fpath, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
        json.dump(S, open(spath, 'w', encoding='utf8'), ensure_ascii=False, indent=0)
        order = {'جديد': 0, 'قناة الشيخ – سيُضاف تلقائياً': 1, 'في المكتبة': 2}
        rows = sorted(F.items(), key=lambda kv: (order[kv[1]['status']], bool(kv[1]['note']), kv[1]['up']))
        with open(os.path.join(ROOT, 'data/found.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['الحالة', 'تنبيه', 'العنوان', 'الرابط', 'القناة', 'تاريخ الرفع', 'المدة', 'المشاهدات', 'بداية الوصف'])
            for k, v in rows:
                w.writerow([v['status'], v['note'], v['title'], 'https://youtu.be/' + k, v['channel'], v['up'], v.get('dur', ''), v.get('views', ''), v.get('desc', '')])
        st = {s: sum(1 for v in F.values() if v['status'] == s) for s in order}
        print(f"found {len(F)} | {st} | searches used {used['search']} | pages {used['cheap']} | tasks done {len(S['done'])}/{len(tasks())} | complete {S.get('complete')}")

main()
