"""Write v/<id>/index.html for every recitation: a tiny page whose title, description and
picture WhatsApp/Telegram/X show when the link is shared. Visitors are sent on to the
recitation inside the site. Applies the same layers as the site: title parse < meta.json < overrides.json."""
import json, os, html, shutil

ROOT = os.path.join(os.path.dirname(__file__), '..')
SITE = 'https://al-mohanna.github.io'
SURAH = 'الفاتحة|البقرة|آل عمران|النساء|المائدة|الأنعام|الأعراف|الأنفال|التوبة|يونس|هود|يوسف|الرعد|إبراهيم|الحجر|النحل|الإسراء|الكهف|مريم|طه|الأنبياء|الحج|المؤمنون|النور|الفرقان|الشعراء|النمل|القصص|العنكبوت|الروم|لقمان|السجدة|الأحزاب|سبأ|فاطر|يس|الصافات|ص|الزمر|غافر|فصلت|الشورى|الزخرف|الدخان|الجاثية|الأحقاف|محمد|الفتح|الحجرات|ق|الذاريات|الطور|النجم|القمر|الرحمن|الواقعة|الحديد|المجادلة|الحشر|الممتحنة|الصف|الجمعة|المنافقون|التغابن|الطلاق|التحريم|الملك|القلم|الحاقة|المعارج|نوح|الجن|المزمل|المدثر|القيامة|الإنسان|المرسلات|النبأ|النازعات|عبس|التكوير|الانفطار|المطففين|الانشقاق|البروج|الطارق|الأعلى|الغاشية|الفجر|البلد|الشمس|الليل|الضحى|الشرح|التين|العلق|القدر|البينة|الزلزلة|العاديات|القارعة|التكاثر|العصر|الهمزة|الفيل|قريش|الماعون|الكوثر|الكافرون|النصر|المسد|الإخلاص|الفلق|الناس'.split('|')
HM = ['محرم', 'صفر', 'ربيع الأول', 'ربيع الآخر', 'جمادى الأولى', 'جمادى الآخرة', 'رجب', 'شعبان', 'رمضان', 'شوال', 'ذو القعدة', 'ذو الحجة']
TL = {'fajr': 'صلاة الفجر', 'maghrib': 'صلاة المغرب', 'isha': 'صلاة العشاء', 'khutbah': 'خطبة الجمعة', 'jumuah': 'صلاة الجمعة',
      'fitr': 'صلاة عيد الفطر', 'adha': 'صلاة عيد الأضحى', 'taraweeh': 'صلاة التراويح', 'istisqa': 'صلاة الاستسقاء', 'kusuf': 'صلاة الكسوف',
      'murattal': 'المصحف المرتل', 'collection': 'إصدار مجمّع', 'lecture': 'محاضرة', 'short': 'مقطع قصير', 'other': 'تلاوة'}
AR = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

def load(name, d):
    try: return json.load(open(os.path.join(ROOT, name), encoding='utf8'))
    except Exception: return d

def snames(S):
    if len(S) == 1: return 'سورة ' + SURAH[S[0] - 1]
    if len(S) == 2: return f'سورتا {SURAH[S[0]-1]} و{SURAH[S[1]-1]}'
    return 'سور ' + '، '.join(SURAH[n - 1] for n in S[:4]) + (' …' if len(S) > 4 else '')

def page(vid, title, desc):
    t, d = html.escape(title), html.escape(desc)
    url = f'{SITE}/v/{vid}'
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t} | تلاوات الشيخ د. خالد المهنا</title>
<meta name="description" content="{d}">
<meta property="og:site_name" content="تلاوات الشيخ د. خالد المهنا">
<meta property="og:type" content="video.other">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://i.ytimg.com/vi/{vid}/hqdefault.jpg">
<meta property="og:image:width" content="480"><meta property="og:image:height" content="360">
<meta property="og:locale" content="ar_SA">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{url}">
<script>location.replace('/#v/{vid}')</script>
</head><body style="font-family:system-ui;background:#0b3d2b;color:#f3ecd9;text-align:center;padding:40px">
<p><a style="color:#e6c674" href="/#v/{vid}">{t}</a></p></body></html>'''

def main():
    data = load('data.json', {'items': []})['items']
    meta, ovr = load('meta.json', {}), load('overrides.json', {})
    recs = {x['video_id']: x for x in load('data/records.json', {'records': []})['records']}
    rows = {r[0]: r for r in data}
    for vid in recs:
        if vid not in rows: rows[vid] = [vid, 'other', 0, 0, 0, [], 0, '', recs[vid]['title'], '', '', 0, '', 0]
    out = os.path.join(ROOT, 'v')
    shutil.rmtree(out, ignore_errors=True)
    n = 0
    for vid, r in rows.items():
        m, o = meta.get(vid, {}), ovr.get(vid, {})
        if o.get('hide'): continue
        t = r[1]
        if m.get('t') == 'short' or (len(r) > 13 and r[13]): t = 'short'
        elif t == 'other' and m.get('t'): t = m['t']
        y, mo, d = r[2], r[3], r[4]
        if not (y and mo and d) and m.get('y'): y, mo, d = m['y'], m.get('m', 0), m.get('d', 0)
        S = [s for s in (r[5] or []) if s != 1] or [s for s in m.get('s', []) if s != 1]
        t = o.get('t', t)
        if 'y' in o: y, mo, d = o['y'], o.get('m', 0), o.get('d', 0)
        if 's' in o: S = [s for s in o['s'] if s != 1]
        if t == 'khutbah': title = 'خطبة الجمعة' + (f' – {r[9]}' if r[9] else '')
        elif t in ('collection', 'lecture'): title = r[8].replace('#', '').split('||')[0].strip()[:90]
        elif t == 'murattal': title = (f'{snames(S[:1])} – ' if S else '') + 'المصحف المرتل'
        elif t == 'short': title = (snames(S) if S else 'مقطع قصير') + ' – مقطع قصير'
        else: title = TL.get(t, 'تلاوة') + (f' – {snames(S)}' if S else '')
        date = (f'{d} {HM[mo-1]} {y}هـ' if y and mo and d else f'{HM[mo-1]} {y}هـ' if y and mo else f'عام {y}هـ' if y else '').translate(AR)
        desc = 'استمع إلى هذه التلاوة الرائعة من تلاوات الشيخ خالد المهنا' + (f' – {date}' if date else '') + '، إمام وخطيب المسجد النبوي.'
        os.makedirs(os.path.join(out, vid), exist_ok=True)
        open(os.path.join(out, vid, 'index.html'), 'w', encoding='utf8').write(page(vid, title, desc))
        n += 1
    print('pages', n)

main()
