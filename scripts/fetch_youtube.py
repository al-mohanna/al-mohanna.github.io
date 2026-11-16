"""Fetch every upload of the YouTube channel and rebuild data.json.
Runs in GitHub Actions every hour. Needs env YOUTUBE_API_KEY."""
import json, os, re, sys, urllib.request, urllib.parse, urllib.error, datetime
sys.path.insert(0, os.path.dirname(__file__))
from parse_lib import build

KEY = os.environ.get('YOUTUBE_API_KEY')
HANDLE = '@khalid_almihana'
API = 'https://www.googleapis.com/youtube/v3/'

def get(path, **q):
    q['key'] = KEY
    with urllib.request.urlopen(API + path + '?' + urllib.parse.urlencode(q), timeout=30) as r:
        return json.load(r)

def iso_dur(s):
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or '')
    d, h, mi, se = (int(x or 0) for x in m.groups()) if m else (0, 0, 0, 0)
    h += d * 24
    return f'{h}:{mi:02d}:{se:02d}' if h else f'{mi}:{se:02d}'

ROOT = os.path.join(os.path.dirname(__file__), '..')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None

def is_short(vid):
    """YouTube serves /shorts/ID directly for Shorts and redirects ordinary videos."""
    req = urllib.request.Request('https://www.youtube.com/shorts/' + vid, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
    try:
        r = urllib.request.build_opener(NoRedirect).open(req, timeout=15)
        return 1 if r.status == 200 else 0
    except urllib.error.HTTPError as e:
        return 0 if e.code in (301, 302, 303, 307, 308) else None
    except Exception:
        return None

def secs(d):
    return sum(int(p) * 60 ** i for i, p in enumerate(reversed(d.split(':'))))

def details(vids):
    durs, views, chans, info = {}, {}, {}, {}
    for i in range(0, len(vids), 50):
        ids = ','.join(v['id'] for v in vids[i:i+50])
        for it in get('videos', part='snippet,contentDetails,statistics', id=ids)['items']:
            durs[it['id']] = iso_dur(it['contentDetails'].get('duration'))
            views[it['id']] = int(it.get('statistics', {}).get('viewCount', 0) or 0)
            info[it['id']] = it['snippet']
    return durs, views, info

def main():
    if not KEY:
        sys.exit('YOUTUBE_API_KEY is missing')
    ch = get('channels', part='contentDetails', forHandle=HANDLE)['items'][0]
    uploads = ch['contentDetails']['relatedPlaylists']['uploads']
    vids, token = [], None
    while True:
        q = dict(part='snippet', playlistId=uploads, maxResults=50)
        if token: q['pageToken'] = token
        r = get('playlistItems', **q)
        for it in r['items']:
            sn = it['snippet']
            if sn.get('title') in ('Private video', 'Deleted video'): continue
            vids.append({'id': sn['resourceId']['videoId'], 'title': sn['title'], 'up': sn['publishedAt'][:10], 'views': 0})
        token = r.get('nextPageToken')
        if not token: break
    durs, views, _ = details(vids)
    for v in vids:
        v['dur'] = durs.get(v['id'], '0:00')
        v['views'] = views.get(v['id'], 0)
    vids.sort(key=lambda v: v['up'], reverse=True)
    # Shorts: check short videos once and remember the answer
    cpath = os.path.join(ROOT, 'data/shorts_cache.json')
    try: cache = json.load(open(cpath))
    except Exception: cache = {}
    for v in vids:
        if secs(v['dur']) <= 180 and v['id'] not in cache:
            r = is_short(v['id'])
            if r is not None: cache[v['id']] = r
        v['short'] = cache.get(v['id'], 0)
    json.dump(cache, open(cpath, 'w'), separators=(',', ':'), sort_keys=True)
    # recitations of the Sheikh kept on other channels (data/extras.json)
    try: extras = json.load(open(os.path.join(ROOT, 'data/extras.json'), encoding='utf8'))
    except Exception: extras = []
    ext = []
    if extras:
        d2, v2, inf = details([{'id': e} for e in extras])
        for e in extras:
            if e not in inf: continue
            sn = inf[e]
            ext.append({'id': e, 'title': sn['title'], 'up': sn['publishedAt'][:10], 'dur': d2.get(e, '0:00'), 'views': v2.get(e, 0), 'src': sn.get('channelTitle', 'قناة أخرى')})
    rows = build(vids) + build(ext)
    out = {'synced': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'), 'count': len(rows), 'items': rows}
    path = os.path.join(os.path.dirname(__file__), '..', 'data.json')
    old = None
    try: old = json.load(open(path, encoding='utf8'))
    except Exception: pass
    if old and old.get('items') == rows:
        print('no changes'); return
    json.dump(out, open(path, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('updated', len(rows))

main()
