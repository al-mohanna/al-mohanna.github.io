"""Download the audio track of each channel video and store it as a GitHub Release asset.
Runs in GitHub Actions. Processes a batch per run so each run stays short."""
import json, os, subprocess, sys
REPO = os.environ['GITHUB_REPOSITORY']
TAG = 'audio'
BATCH = int(os.environ.get('BATCH', '25'))
root = os.path.join(os.path.dirname(__file__), '..')

def sh(*a, check=True):
    return subprocess.run(a, check=check, capture_output=True, text=True)

if sh('gh', 'release', 'view', TAG, '-R', REPO, check=False).returncode != 0:
    sh('gh', 'release', 'create', TAG, '-R', REPO, '--title', 'المقاطع الصوتية', '--notes', 'ملفات صوتية لتلاوات القناة، تُضاف تلقائياً.')
assets = json.loads(sh('gh', 'release', 'view', TAG, '-R', REPO, '--json', 'assets').stdout)['assets']
have = {a['name'][:-4] for a in assets if a['name'].endswith('.m4a')}
items = json.load(open(os.path.join(root, 'data.json'), encoding='utf8'))['items']
todo = [r[0] for r in items if r[0] not in have][:BATCH]
print('have', len(have), 'todo this run', len(todo))
fail = 0
for vid in todo:
    out = f'/tmp/{vid}.m4a'
    r = sh('yt-dlp', '-q', '--no-playlist', '-f', '139/140/bestaudio[ext=m4a]', '-o', out,
           f'https://www.youtube.com/watch?v={vid}', check=False)
    if r.returncode != 0 or not os.path.exists(out):
        fail += 1; print('fail', vid, r.stderr[-300:]); continue
    sh('gh', 'release', 'upload', TAG, out, '-R', REPO, '--clobber')
    have.add(vid); os.remove(out); print('ok', vid)
json.dump(sorted(have), open(os.path.join(root, 'audio.json'), 'w'), separators=(',', ':'))
print('total audio', len(have), 'failed', fail)
