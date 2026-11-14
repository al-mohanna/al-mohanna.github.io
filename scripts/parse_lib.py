import re, json, sys
SURAH='الفاتحة|البقرة|آل عمران|النساء|المائدة|الأنعام|الأعراف|الأنفال|التوبة|يونس|هود|يوسف|الرعد|إبراهيم|الحجر|النحل|الإسراء|الكهف|مريم|طه|الأنبياء|الحج|المؤمنون|النور|الفرقان|الشعراء|النمل|القصص|العنكبوت|الروم|لقمان|السجدة|الأحزاب|سبأ|فاطر|يس|الصافات|ص|الزمر|غافر|فصلت|الشورى|الزخرف|الدخان|الجاثية|الأحقاف|محمد|الفتح|الحجرات|ق|الذاريات|الطور|النجم|القمر|الرحمن|الواقعة|الحديد|المجادلة|الحشر|الممتحنة|الصف|الجمعة|المنافقون|التغابن|الطلاق|التحريم|الملك|القلم|الحاقة|المعارج|نوح|الجن|المزمل|المدثر|القيامة|الإنسان|المرسلات|النبأ|النازعات|عبس|التكوير|الانفطار|المطففين|الانشقاق|البروج|الطارق|الأعلى|الغاشية|الفجر|البلد|الشمس|الليل|الضحى|الشرح|التين|العلق|القدر|البينة|الزلزلة|العاديات|القارعة|التكاثر|العصر|الهمزة|الفيل|قريش|الماعون|الكوثر|الكافرون|النصر|المسد|الإخلاص|الفلق|الناس'.split('|')
def norm(s):
    s=re.sub(r'[ً-ْٰـ‎‏]','',s)
    s=re.sub('[أإآ]','ا',s).replace('ة','ه').replace('ى','ي')
    return s
AR='٠١٢٣٤٥٦٧٨٩'
def digits(s): return ''.join(str(AR.index(c)) if c in AR else c for c in s)
SN={norm(n):i+1 for i,n in enumerate(SURAH)}
SN[norm('الإنفطار')]=82; SN[norm('الأسراء')]=17; SN[norm('المنافقين')]=63; SN['الم نافقون']=63
MONTHS=[(1,['محرم']),(2,['صفر']),(3,['ربيع الاول','ربيع اول']),(4,['ربيع الاخر','ربيع الثاني','ربيع ثاني','ربيع اخر']),
 (5,['جمادي الاولي','جماد الاولي','جمادي اولي']),(6,['جمادي الاخره','جمادي الثانيه','جمادي الاخر']),(7,['رجب']),(8,['شعبان']),(9,['رمضان']),(10,['شوال']),
 (11,['ذو القعده','ذي القعده','ذوالقعده']),(12,['ذو الحجه','ذي الحجه','ذوالحجه'])]
MRE='|'.join(re.escape(v) for _,vs in MONTHS for v in vs)
def mnum(txt):
    for n,vs in MONTHS:
        if txt in vs: return n
ORD={'الاولي':1,'الثانيه':2,'الثالثه':3,'الرابعه':4,'الخامسه':5,'الخامس':5,'السادسه':6,'السابعه':7,'الثامنه':8,'التاسعه':9,'العاشره':10,'الحاديه عشر':11,'الحاديه عشره':11,'الثاني':2,'الثالث':3,'الرابع':4,'السادس':6,'السابع':7,'الثامن':8,'التاسع':9,'العاشر':10}

def surahs(t):
    """t normalized. returns list of surah numbers"""
    cand=None
    m=re.search(r'(سوره|سورتي|لسوره|سور)\s',t)
    if m: cand=t[m.start():]
    else:
        p=re.search(r'\(([^)]*)\)',t)
        if p: cand=p.group(1)
        else:
            segs=[s for s in re.split(r'\||\s-\s',t) if s.strip()]
            cand=segs[-1] if len(segs)>1 else ''
    cand=re.split(r'صلاه|صلوات|للشيخ|بصوت|بالمسجد|بالحرم|من الحرم|من المسجد|\sفجر\s|#|المدينه|\|\||\sعام\s|\sتراويح|المصحف',cand)[0]
    toks=re.findall(r'[؀-ۿ]+',cand)
    out=[];i=0
    while i<len(toks):
        w=toks[i]; two=' '.join(toks[i:i+2])
        if two in SN: out.append(SN[two]); i+=2; continue
        for c in (w, w[1:] if w.startswith('و') else None):
            if c and c in SN and c not in ('سوره',):
                out.append(SN[c]); break
        i+=1
    # range "من X وحتى Y" / "حتى"
    if 'حتي' in cand and len(out)>=2 and out[1]>out[0]:
        out=list(range(out[0],out[-1]+1))
    seen=[]; [seen.append(x) for x in out if x not in seen]
    return seen

def parse(vid,raw,order):
    title=raw.strip()
    dur=''
    m=re.search(r'\s(\d{1,2}(?::\d{2}){1,2})(\s+(?:قبل|خلال).*)?$',title)
    if m: dur=m.group(1); title=title[:m.start()].strip()
    t=norm(digits(title)).replace('#',' ').replace('_',' ')
    t=re.sub(r'\s+',' ',t)
    it={'i':vid,'o':order,'title':title,'dur':dur}
    # type
    if 'المصحف المرتل' in t:
        it['t']='murattal'
        jm=re.search(r'الجزء (\S+ ?\S*) من المصحف',t)
        if jm: it['juz']=jm.group(1)
    elif re.search(r'جميع الفروض|الفروض الجهريه|خلال شهر|الاصدار|اصدار|تلاوات مختاره|\( ?\d* ?ساع|ساعات\s?\)|تلاوات الشيخ خالد بن سليمان المهنا - |مجموع تلاوات',t):
        it['t']='collection'
    elif re.search(r'محاضره|كلمه الشيخ|لقاء الشيخ|دوره|الدوره العلميه',t): it['t']='lecture'
    elif 'خطبه' in t: it['t']='khutbah'
    elif 'صلاه الجمعه' in t: it['t']='jumuah'
    elif 'استسقاء' in t: it['t']='istisqa'
    elif 'كسوف' in t or 'خسوف' in t: it['t']='kusuf'
    elif 'عيد الفطر' in t: it['t']='fitr'
    elif 'عيد الاضحي' in t: it['t']='adha'
    elif re.search(r'صلاه (ال)?فجر',t): it['t']='fajr'
    elif re.search(r'تراويح|التهجد|تهجد|القيام|ليله|ليالي',t) or ('رمضان' in t and not re.search(r'فجر|مغرب|عشاء',t)): it['t']='taraweeh'
    elif re.search(r'الفجر|فجر|فجريه',t) and not re.search(r'(سوره|سورتي)\s+الفجر',t): it['t']='fajr'
    elif re.search(r'المغرب|مغرب',t): it['t']='maghrib'
    elif re.search(r'العشاء|عشاء|عشائي',t): it['t']='isha'
    elif re.search(r'(سوره|سورتي)\s+الفجر',t) and 'صلاه الفجر' in t: it['t']='fajr'
    else: it['t']='other'
    # date
    y=mo=d=None
    m=re.search(r'(14\d\d)\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})',t)
    if m: y,mo,d=int(m[1]),int(m[2]),int(m[3])
    if not y:
        m=re.search(r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(14\d\d)',t)
        if m: d,mo,y=int(m[1]),int(m[2]),int(m[3])
    if not y:
        m=re.search(r'(\d{1,2})\s*(?:من\s+)?('+MRE+r')\s*(?:لعام\s*)?(14\d\d)?',t)
        if m: d,mo=int(m[1]),mnum(m[2]); y=int(m[3]) if m[3] else None
    if not d and it['t']=='taraweeh':
        m=re.search(r'ليله\s*(?:ال)?(\d{1,2})',t)
        if m: d=int(m[1]); mo=9
        else:
            for k,v in ORD.items():
                if 'الليله '+k in t or 'ليله '+k in t: d=v; mo=9
        ym=re.search(r'(14\d\d)',t)
        if ym: y=int(ym[1])
    if it['t']=='collection' or (not d):
        ym=re.search(r'(1[34]\d\d)',t)
        if ym and not y: y=int(ym[1])
        mm=re.search('('+MRE+')',t)
        if mm and it['t']=='collection': mo=mnum(mm[1])
    if it['t'] in ('collection',): d=None
    it['y'],it['m'],it['d']=y,mo,d
    if it['t'] not in ('khutbah','collection','lecture'):
        s=surahs(t)
        if it['t']=='murattal' and s: s=s[:1]
        it['s']=s
        it['full']=bool(re.search(r'كامله',t))
    if it['t']=='khutbah':
        km=re.search(r'خطبه الجمعه\s+(.+?)\s*\|',title) or re.search(r'بعنوان\s+(.+?)\s*-',title)
        if km: it['topic']=km.group(1).strip()
    return it


def build(entries):
    """entries: list of dicts {id,title,dur,up} newest first -> compact rows"""
    rows=[]
    for o,e in enumerate(entries):
        it=parse(e['id'],e['title']+' '+e['dur'],o)
        it['up']=e.get('up','')
        rows.append(it)
    for i,it in enumerate(rows):
        if it['d'] and not it['y']:
            for j in list(range(i+1,min(i+15,len(rows))))+list(range(i-1,max(i-15,-1),-1)):
                if rows[j]['y'] and rows[j]['y']>=1440: it['y']=rows[j]['y']; break
    out=[]
    for x in rows:
        e=[x['i'],x['t'],x.get('y') or 0,x.get('m') or 0,x.get('d') or 0,x.get('s',[]),1 if x.get('full') else 0,x['dur'],x['title'],x.get('topic') or '',x.get('up','')]
        out.append(e)
    return out
