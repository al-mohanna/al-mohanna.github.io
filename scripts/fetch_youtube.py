"""Fetch every upload of the YouTube channel and rebuild data.json.
Runs in GitHub Actions every hour. Needs env YOUTUBE_API_KEY."""
import json, os, re, sys, urllib.request, urllib.parse, datetime
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
    durs, views = {}, {}
    for i in range(0, len(vids), 50):
        ids = ','.join(v['id'] for v in vids[i:i+50])
        for it in get('videos', part='contentDetails,statistics', id=ids)['items']:
            durs[it['id']] = iso_dur(it['contentDetails'].get('duration'))
            views[it['id']] = int(it.get('statistics', {}).get('viewCount', 0) or 0)
    for v in vids:
        v['dur'] = durs.get(v['id'], '0:00')
        v['views'] = views.get(v['id'], 0)
    vids.sort(key=lambda v: v['up'], reverse=True)
    rows = build(vids)
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
