"""Collect every YouTube video of Sheikh Dr. Khalid Al-Muhanna from ANY channel.
Runs nightly in GitHub Actions and resumes where it stopped (YouTube allows ~100 searches a day).
1) many searches (name spellings x topics x years), 2) then every upload of channels that publish him.
Writes data/found.json (all finds) and data/found.csv (opens in Excel) with a status per video."""
import json, os, re, sys, csv, time, urllib.request, urllib.parse, urllib.error, datetime
sys.path.insert(0, os.path.dirname(__file__))
from parse_lib import norm

KEY = os.environ.get('YOUTUBE_API_KEY')
API = 'https://www.googleapis.com/youtube/v3/'
ROOT = os.path.join(os.path.dirname(__file__), '..')
OWN = '@khalid_almihana'
MAX_SEARCH = int(os.environ.get('MAX_SEARCH', '70'))     # 100 units each
MAX_PAGES = int(os.environ.get('MAX_PAGES', '1200'))      # 1 unit each (channel uploads, details)

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
    if not cheap: time.sleep(1.5)                      # be gentle: YouTube refuses bursts (429)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(API + path + '?' + urllib.parse.urlencode(q), timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf8', 'ignore')
            if e.code == 403 and 'quotaexceeded' in body.lower().replace(' ', ''): raise Quota('daily quota')
            if e.code == 429 or (e.code == 403 and 'ratelimit' in body.lower()) or e.code >= 500:
                time.sleep(20 * (attempt + 1)); continue
            raise
    raise Quota('YouTube keeps refusing (rate limit)')

# ---- is this video about our Sheikh? ----
NAME = re.compile(r'مهنا|muhanna|mohanna|mehanna|mihana|muhana|mohana', re.I)
HOMONYM = re.compile(r'محنا|محنّا|mahna\b|mhna\b', re.I)      # «خالد محنا» – a different person (audio producer)
BLOCK_CH = {'UCCxfgAfV8itfSr5P93Pfv4Q'}   # «خالد المهنا | Khalid Al-Muhanna»: the singer, not the Sheikh
MUSHAF = re.compile(r'مرتل|المصحف المرتل|مصحف المدينة|المصحف الشريف|مجمع الملك فهد|بصوت القارئ|عرض للصفحة|murattal|mushaf|with english translation', re.I)
PRAYER = re.compile(r'فجر|مغرب|عشاء|عشا|تراويح|تهجد|قيام|صلاة|صلاه|خطبة|خطبه|جمعة|جمعه|عيد|استسقاء|كسوف|ليلة|ليله|fajr|maghrib|isha|taraweeh|tahajjud|prayer|khutbah', re.I)
ARTIST = re.compile(r'اغني|أغني|أغان|فنان|موسيق|كليب|شيله|شيلة|عزف|طرب|لحن|ألحان|مطرب|song|music|clip|official audio|lyrics|concert', re.I)
HARAM = re.compile(r'نبوي|حرم|مسجد|تلاو|صلاه|صلاة|تراويح|تهجد|قيام|فجر|مغرب|عشاء|جمعه|جمعة|خطبه|خطبة|سوره|سورة|quran|recit|prayer|madinah|nabawi|haram|taraweeh|surah', re.I)

def relevant(sn):
    t = sn.get('title', '') + ' ' + sn.get('description', '')[:600] + ' ' + sn.get('channelTitle', '')
    if not NAME.search(t) and not NAME.search(norm(t)): return None
    note = ''
    if ARTIST.search(sn.get('title', '') + ' ' + sn.get('channelTitle', '')) and not HARAM.search(sn.get('title', '')): note = 'مستبعد: يبدو للفنان صاحب الاسم المشابه'
    elif HOMONYM.search(t) and not re.search(r'مهنا', t): note = 'قد يكون «خالد محنا» (شخص آخر)'
    elif not HARAM.search(t): note = 'لا يظهر أنه تلاوة'
    return note

def tasks():
    """All years are treated equally."""
    names = ['خالد المهنا', 'الشيخ خالد المهنا', 'خالد بن سليمان المهنا', 'الشيخ الدكتور خالد المهنا', 'د. خالد المهنا', 'المهنا المسجد النبوي',
             'Dr. Khalid Al-Muhanna', 'Khalid Al Muhanna', 'Khalid Al-Muhanna', 'Khaled Al Muhanna', 'Khaled Al-Muhanna',
             'Khaled Almohanna', 'Khalid Almuhanna', 'Sheikh Khalid Al Muhanna']
    topics = ['تلاوة', 'تراويح', 'تهجد', 'قيام الليل', 'صلاة الفجر', 'صلاة الظهر', 'صلاة العصر', 'صلاة المغرب', 'صلاة العشاء', 'صلاة الجمعة',
              'خطبة الجمعة', 'خطبة العيد', 'صلاة العيد', 'استسقاء', 'كسوف', 'خسوف', 'دعاء القنوت', 'ختم القرآن', 'سورة',
              'محاضرة', 'درس', 'كلمة', 'لقاء', 'مقابلة', 'دورة علمية']
    # approved ranges first: obligatory prayers Safar 1441 – Muharram 1442, Ramadan nights 1436–1441
    T = []
    # full-length copies wanted for nights we only have as short clips (owner's request 17-11-2026)
    for y, n in [(1436, 3), (1436, 21), (1436, 24), (1436, 26), (1436, 28), (1441, 12), (1441, 15), (1441, 27), (1437, 8)]:
        T += [(f'خالد المهنا ليلة {n} رمضان {y}', None)]
    T += [('خالد المهنا صلاة العشاء 5 شعبان 1441', None), ('خالد المهنا تراويح 1441 كاملة', None), ('خالد المهنا تهجد 1436 كاملة', None)]
    for mo in ['صفر', 'ربيع الأول', 'ربيع الآخر', 'جمادى الأولى', 'جمادى الآخرة', 'رجب', 'شعبان', 'رمضان', 'شوال', 'ذو القعدة', 'ذو الحجة']:
        T += [(f'صلاة الفجر خالد المهنا {mo} 1441', None), (f'خالد المهنا المغرب العشاء {mo} 1441', None)]
    T += [('خالد المهنا محرم 1442', None), ('صلاة الفجر خالد المهنا محرم 1442', None)]
    for y in range(1436, 1442):
        T += [(f'خالد المهنا رمضان {y}', None), (f'خالد المهنا ليلة رمضان {y} المسجد النبوي', None)]
    T += [(n, None) for n in names]
    T += [(f'خالد المهنا {t}', None) for t in topics]
    for y in range(1436, 1449):
        T += [(f'المهنا تراويح {y}', None), (f'خالد المهنا {y}', None), (f'المهنا تهجد {y}', None)]
    for gy in range(2014, 2027):
        T += [(n, gy) for n in ['خالد المهنا', 'الشيخ خالد المهنا', 'Khalid Al-Muhanna', 'Khaled Al Muhanna']]
    return T

def main():
    if not KEY: sys.exit('YOUTUBE_API_KEY missing')
    fpath, spath = os.path.join(ROOT, 'data/found.json'), os.path.join(ROOT, 'data/collect_state.json')
    try: F = json.load(open(fpath, encoding='utf8'))
    except Exception: F = {}
    try: S = json.load(open(spath, encoding='utf8'))
    except Exception: S = {'done': [], 'chan_done': [], 'own': ''}
    lib = {r[0] for r in json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf8'))['items']}
    def details():
        need = [] if os.environ.get('OFFLINE') else [k for k, v in F.items() if 'dur' not in v]
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
        except (Quota, urllib.error.URLError, OSError) as e: print('details stopped:', e)

    try:
        if os.environ.get('OFFLINE'): raise Quota('offline rebuild')
        details()
        if not S.get('own'):
            S['own'] = get('channels', part='id', forHandle=OWN)['items'][0]['id']
        new_ids = []

        def keep(vid, sn, how):
            if sn.get('channelId') in BLOCK_CH or sn.get('channelId') == S['own']: return False
            note = relevant(sn)
            if note is None: return False
            if MUSHAF.search(sn.get('title', '') + ' ' + sn.get('description', '')[:300]) and not PRAYER.search(sn.get('title', '')): return False   # both Mushafs are out of scope
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
                    pl, token = up[0]['contentDetails']['relatedPlaylists']['uploads'], S.setdefault('chan_tok', {}).get(cid)
                    while True:
                        p = dict(part='snippet', playlistId=pl, maxResults=50)
                        if token: p['pageToken'] = token
                        r = get('playlistItems', **p)
                        for it in r.get('items', []):
                            sn = it['snippet']; sn['channelId'] = cid
                            sn['channelTitle'] = sn.get('videoOwnerChannelTitle') or sn.get('channelTitle', '')
                            # a general channel (not named after the Sheikh): only videos naming him in the title
                            if NAME.search(sn['channelTitle'] or '') or NAME.search(sn.get('title', '')):
                                keep(sn['resourceId']['videoId'], sn, 'قناة: ' + sn['channelTitle'])
                        token = r.get('nextPageToken')
                        S['chan_tok'][cid] = token
                        if not token: break
                S['chan_done'].append(cid)
        # 1) searches first (the scarce, expensive part of the daily quota)
        searched_all = False
        try:
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
            searched_all = True
        except Quota as e: print('searches stopped:', e)
        # 2) then every upload of the channels that publish the Sheikh, resuming where the last run stopped
        try: channels()
        except Quota as e: print('channels stopped:', e)
        seeds = {c for c in {v['cid'] for v in F.values() if v['cid']} if sum(1 for v in F.values() if v['cid'] == c and not v['note']) >= 3}
        S['complete'] = searched_all and all(c in S['chan_done'] for c in seeds - {S['own']})
    except Quota as e:
        S['complete'] = False
        print('stopped:', e)
    finally:
        details()

        own = S.get('own')
        for k in [k for k, v in F.items() if v['cid'] in BLOCK_CH or v['cid'] == own]: del F[k]   # never list our channel or the singer
        for k in [k for k, v in F.items() if v.get('how', '').startswith('قناة:') and not NAME.search(v['channel']) and not NAME.search(v['title'])]: del F[k]
        # both Mushafs (Prophet's Mosque and King Fahd Complex) are out of scope
        mus = lambda v: MUSHAF.search(v['title'] + ' ' + v.get('desc', '')) and not PRAYER.search(v['title'])
        for k in [k for k, v in F.items() if mus(v)]: del F[k]
        # channels that mostly publish Mushaf surahs ("سورة X - خالد المهنا"): keep only their prayer recordings
        surah_only = lambda v: re.match(r'^\s*(سورة|سورتا|surah|quran)\b', v['title'], re.I) and not PRAYER.search(v['title'])
        by = {}
        for v in F.values(): by.setdefault(v['cid'], []).append(v)
        S['mushaf_ch'] = sorted(set(S.get('mushaf_ch', [])) | {c for c, L in by.items() if len(L) >= 5 and sum(map(bool, map(surah_only, L))) / len(L) >= .6})
        for k in [k for k, v in F.items() if v['cid'] in S['mushaf_ch'] and not PRAYER.search(v['title'])]: del F[k]
        for k, v in F.items():
            if not v['note'] and not NAME.search(v['title']): v['note'] = 'اسم الشيخ ليس في العنوان – يحتاج تحقق'
            v['status'] = 'في المكتبة' if k in lib else ('قناة الشيخ – سيُضاف تلقائياً' if v['cid'] == own else 'جديد')
        json.dump(F, open(fpath, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
        json.dump(S, open(spath, 'w', encoding='utf8'), ensure_ascii=False, indent=0)
        order = {'جديد': 0, 'قناة الشيخ – سيُضاف تلقائياً': 1, 'في المكتبة': 2}
        rows = sorted(F.items(), key=lambda kv: (order[kv[1]['status']], bool(kv[1]['note']), kv[1]['up']))
        with open(os.path.join(ROOT, 'data/found.csv'), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['الحالة', 'تنبيه', 'العنوان', 'الرابط', 'القناة', 'تاريخ الرفع', 'المدة', 'المشاهدات', 'بداية الوصف'])
            for k, v in rows:
                if v['status'] == 'في المكتبة': continue
                w.writerow([v['status'], v['note'], v['title'], 'https://youtu.be/' + k, v['channel'], v['up'], v.get('dur', ''), v.get('views', ''), v.get('desc', '')])
        st = {s: sum(1 for v in F.values() if v['status'] == s) for s in order}
        n_new = st['جديد']
        now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if not os.environ.get('OFFLINE'):
            S.setdefault('runs', []).append({'at': now, 'added': max(0, n_new - S.get('last_total', 0)), 'total': n_new})
            S['last_total'] = n_new
        status = {'complete': bool(S.get('complete')), 'total': n_new, 'tasks_done': len(S['done']), 'tasks_all': len(tasks()),
                  'channels_done': len(S.get('chan_done', [])), 'runs': S.get('runs', [])[-8:], 'updated_utc': now}
        json.dump(status, open(os.path.join(ROOT, 'data/collect_status.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
        json.dump(S, open(spath, 'w', encoding='utf8'), ensure_ascii=False, indent=0)
        print(f"found {len(F)} | {st} | searches used {used['search']} | pages {used['cheap']} | tasks done {len(S['done'])}/{len(tasks())} | complete {S.get('complete')}")

main()
