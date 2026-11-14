"""Link each YouTube recitation to its Telegram post (video) and audio post.
Reads the public preview of t.me/s/KhaledAlMuhanna, groups posts sent together,
and matches them to data.json by YouTube link, or by prayer + Hijri date in the caption.
Writes telegram.json: {videoId: {"p": videoPost, "a": audioPost}}"""
import json, os, re, sys, html, urllib.request, datetime
sys.path.insert(0, os.path.dirname(__file__))
from parse_lib import parse

CH = 'KhaledAlMuhanna'
ROOT = os.path.join(os.path.dirname(__file__), '..')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; mihana-bot)'}

def page(before=None):
    url = f'https://t.me/s/{CH}' + (f'?before={before}' if before else '')
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode('utf8')

def posts():
    out, before = {}, None
    for _ in range(300):
        h = page(before)
        blocks = re.split(r'<div class="tgme_widget_message_wrap', h)[1:]
        nums = []
        for b in blocks:
            m = re.search(r'data-post="%s/(\d+)"' % CH, b)
            if not m: continue
            n = int(m.group(1)); nums.append(n)
            t = re.search(r'<time datetime="([^"]+)"', b)
            tx = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', b, re.S)
            raw = tx.group(1) if tx else ''
            ids = re.findall(r'(?:youtu\.be/|watch\?v=|shorts/)([\w-]{11})', raw)
            text = html.unescape(re.sub(r'<[^>]+>', ' ', raw))
            kind = 'v' if 'tgme_widget_message_video_player' in b else (
                'a' if ('tgme_widget_message_document_title' in b or 'tgme_widget_message_voice' in b) else '')
            out[n] = {'t': t.group(1) if t else '', 'text': text, 'ids': ids, 'k': kind}
        if not nums: break
        mn = min(nums)
        if mn <= 1 or mn == before: break
        before = mn
    return out

def ts(s):
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None

def clusters(P):
    cl = []
    for n in sorted(P):
        p = P[n]; c = cl[-1] if cl else None
        new = c is None
        if c:
            t0, t1 = ts(c['last']), ts(p['t'])
            gap = (t1 - t0).total_seconds() if t0 and t1 else 0
            if gap > 3 * 3600: new = True
            elif p['k'] == 'v' and c['v']: new = True
            elif p['k'] == 'a' and c['a']: new = True
        if new:
            c = {'v': None, 'a': None, 'text': '', 'ids': [], 'last': p['t']}; cl.append(c)
        if p['k'] == 'v' and not c['v']: c['v'] = n
        if p['k'] == 'a' and not c['a']: c['a'] = n
        c['text'] += ' ' + p['text']; c['ids'] += p['ids']; c['last'] = p['t'] or c['last']
    return cl

def main():
    data = json.load(open(os.path.join(ROOT, 'data.json'), encoding='utf8'))['items']
    try: ovr = json.load(open(os.path.join(ROOT, 'overrides.json'), encoding='utf8'))
    except Exception: ovr = {}
    key = {}
    for r in data:
        o = ovr.get(r[0], {}); t = o.get('t', r[1]); y = o.get('y', r[2]); m = o.get('m', r[3]); d = o.get('d', r[4])
        if y and m and d and t not in ('collection', 'murattal', 'lecture'):
            key.setdefault((t, y, m, d), []).append(r[0])
    known = {r[0] for r in data}
    P = posts()
    print('posts', len(P))
    res = {}
    for c in clusters(P):
        if not (c['v'] or c['a']):
            # a text-only post with a YouTube link still counts as the post
            pass
        target = [i for i in dict.fromkeys(c['ids']) if i in known]
        if not target and c['text'].strip():
            q = parse('x', c['text'] + ' 0:00', 0)
            k = (q.get('t'), q.get('y'), q.get('m'), q.get('d'))
            if all(k) and len(key.get(k, [])) == 1: target = key[k]
        for vid in target:
            e = res.setdefault(vid, {})
            post = c['v'] or (min(n for n in P if P[n]['ids'] and vid in P[n]['ids']) if any(vid in P[n]['ids'] for n in P) else None)
            if post and 'p' not in e: e['p'] = post
            if c['a'] and 'a' not in e: e['a'] = c['a']
    json.dump(res, open(os.path.join(ROOT, 'telegram.json'), 'w', encoding='utf8'), separators=(',', ':'), sort_keys=True)
    print('linked', len(res), 'with audio', sum(1 for v in res.values() if 'a' in v))

main()
