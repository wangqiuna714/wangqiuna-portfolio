#!/usr/bin/env python3
"""Fetch public RSS/search feeds; preserve source metadata and avoid invented summaries."""
import json, re, time, hashlib, html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'news.json'
UA = 'EmbodiedRadarBot/1.0 (public RSS aggregation; contact: site maintainer)'
QUERIES = [
    ('news', 'embodied AI OR humanoid robot OR physical AI'),
    ('news', '\u5177\u8eab\u667a\u80fd OR \u4eba\u5f62\u673a\u5668\u4eba'),
    ('company', 'humanoid robotics funding deployment orders company'),
    ('jobs', '\u5177\u8eab\u667a\u80fd \u62db\u8058 OR \u673a\u5668\u4eba \u7b97\u6cd5\u5de5\u7a0b\u5e08 \u62db\u8058'),
    ('technology', 'robot learning VLA embodied robotics arXiv'),
    ('events', 'robotics humanoid embodied AI conference event 2026'),
    ('interviews', 'embodied AI robotics founder interview researcher CEO'),
    ('interviews', '\u5177\u8eab\u667a\u80fd \u4e13\u8bbf OR \u521b\u59cb\u4eba \u79d1\u5b66\u5bb6 \u5bf9\u8bdd'),
    ('industry', 'embodied AI robotics policy industry strategy standards supply chain'),
    ('industry', '\u5177\u8eab\u667a\u80fd \u4ea7\u4e1a\u653f\u7b56 OR \u673a\u5668\u4eba \u6807\u51c6 \u4f9b\u5e94\u94fe')
]

def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()

def get(url):
    req = Request(url, headers={'User-Agent': UA})
    with urlopen(req, timeout=25) as r:
        return r.read()

def date_of(item):
    raw = item.findtext('pubDate') or item.findtext('{http://purl.org/dc/elements/1.1/}date') or ''
    try:
        d = parsedate_to_datetime(raw)
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).strftime('%Y-%m-%d')
    except Exception:
        return ''

def source_name(item, link):
    src = item.find('source')
    if src is not None and src.text: return clean(src.text)
    m = re.search(r'https?://([^/]+)', link)
    return m.group(1).removeprefix('www.') if m else 'RSS source'

def classify(category, title, desc):
    t = (title + ' ' + desc).lower()
    # Classify by concrete topic using ordered rules to reduce mixed feeds.
    if any(k in t for k in ['招聘','招募','career','job opening','hiring','职位']):
        return 'jobs'
    if any(k in t for k in ['融资','募资','投资','收购','并购','订单','中标','交付','量产','funding','investment','acquisition','purchase order','deployment contract']):
        return 'company'
    if any(k in t for k in ['访谈','专访','对话','采访','interview','podcast']):
        return 'interviews'
    if any(k in t for k in ['大会','峰会','论坛','展会','conference','summit','workshop','symposium']):
        return 'events'
    if any(k in t for k in ['论文','arxiv','preprint','benchmark','dataset','vla','vision-language-action','world model','robot learning','模仿学习','强化学习','运动控制','灵巧操作','manipulation','模型发布','技术报告']):
        return 'technology'
    if any(k in t for k in ['工厂','仓储','物流','医院','养老院','门店','部署','落地','应用案例','factory','warehouse','logistics','hospital','retail','real-world use']):
        return 'application'
    if any(k in t for k in ['政策','行动方案','标准','规范','产业规划','产业链','供应链','industry policy','regulation','standard']):
        return 'industry'
    if category in {'jobs','technology','company','events','interviews','application','industry'}:
        return category
    return 'news'

def fetch_google(category, query):
    params = {'q': query, 'hl': 'zh-CN', 'gl': 'CN', 'ceid': 'CN:zh-Hans'}
    url = 'https://news.google.com/rss/search?' + urlencode(params, quote_via=quote)
    root = ET.fromstring(get(url))
    out = []
    for item in root.findall('./channel/item'):
        title = clean(item.findtext('title'))
        link = item.findtext('link') or ''
        desc = clean(item.findtext('description'))
        if not title or not link: continue
        cat = classify(category, title, desc)
        if cat == 'jobs' and not any(k in (title+' '+desc).lower() for k in ['招聘','engineer','career','job','hiring']): continue
        out.append({'date': date_of(item), 'category': cat, 'title': title, 'summary': desc[:650], 'source': source_name(item, link), 'url': link, 'confidence': 'RSS摘要，需核对原文'})
    return out

def fetch_arxiv():
    url = 'https://export.arxiv.org/api/query?' + urlencode({'search_query':'all:embodied AND (all:robot OR all:robotics)', 'start':0, 'max_results':20, 'sortBy':'submittedDate', 'sortOrder':'descending'})
    root = ET.fromstring(get(url))
    ns = {'a':'http://www.w3.org/2005/Atom'}
    out=[]
    for e in root.findall('a:entry', ns):
        title=clean(e.findtext('a:title', default='', namespaces=ns))
        summary=clean(e.findtext('a:summary', default='', namespaces=ns))
        link=e.find('a:id', ns).text
        published=e.findtext('a:published', default='', namespaces=ns)[:10]
        out.append({'date':published,'category':'technology','title':title,'summary':summary[:650],'source':'arXiv','url':link,'confidence':'论文预印本，非同行评审结论'})
    return out

def main():
    collected=[]
    for cat,q in QUERIES:
        try: collected.extend(fetch_google(cat,q)); time.sleep(1)
        except Exception as e: print('feed error:',cat,str(e)[:180])
    try: collected.extend(fetch_arxiv())
    except Exception as e: print('arxiv error:',str(e)[:180])
    # retain items with usable dates; keep latest 30 days and deduplicate by normalized title
    cutoff = datetime.now(timezone.utc).date().toordinal()-30
    unique={}
    for x in collected:
        try:
            if not x['date'] or datetime.strptime(x['date'],'%Y-%m-%d').date().toordinal()<cutoff: continue
        except Exception: continue
        key=re.sub(r'[^a-z0-9\u4e00-\u9fff]+','',x['title'].lower())
        if not key: continue
        old=unique.get(key)
        if old is None or len(x.get('summary',''))>len(old.get('summary','')): unique[key]=x
    items=list(unique.values())
    items.sort(key=lambda x:x['date'],reverse=True)
    # Keep manually curated seed items if current fetch fails or has no results.
    existing=[]
    if OUT.exists():
        try: existing=json.loads(OUT.read_text(encoding='utf-8')).get('items',[])
        except Exception: pass
    if len(items)<5: items=existing
    payload={'updated_at':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'timezone':'UTC source timestamps; display dates as published','items':items[:100]}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('saved',len(payload['items']),'items')
if __name__=='__main__': main()
