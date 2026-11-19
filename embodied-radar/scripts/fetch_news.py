#!/usr/bin/env python3
"""Daily public-source discovery for the Embodied Intelligence Radar.
RSS/search results are leads, not independently verified facts.
"""
import json, re, time, html, hashlib
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
UA = "EmbodiedRadar/2.0 (+https://github.com/wangqiuna714/wangqiuna-portfolio)"
MAX_PER_QUERY = 20
DAYS_BACK = 45

QUERIES = [
    ("news", '("embodied AI" OR "physical AI" OR humanoid robot)'),
    ("news", '("具身智能" OR "人形机器人")'),
    ("technology", '("vision-language-action" OR VLA OR "robot learning" OR "world model") robotics'),
    ("technology", '("具身智能" AND (模型 OR 算法 OR 数据 OR 操作 OR 控制))'),
    ("company", '("humanoid robot" OR "embodied AI") (funding OR investment OR order OR deployment OR production)'),
    ("company", '("具身智能" OR "人形机器人") (融资 OR 订单 OR 交付 OR 量产 OR 合作)'),
    ("application", '("humanoid robot" OR "embodied AI") (factory OR warehouse OR hospital OR retail OR deployment)'),
    ("application", '("机器人" OR "具身智能") (工厂 OR 仓储 OR 物流 OR 医疗 OR 零售 OR 落地)'),
    ("jobs", '("embodied AI" OR robotics OR humanoid) (hiring OR jobs OR career OR engineer)'),
    ("jobs", '("具身智能" OR 机器人) (招聘 OR 算法工程师 OR 控制工程师 OR 数据采集)'),
    ("events", '("robotics" OR "humanoid" OR "embodied AI") (conference OR summit OR workshop 2026)'),
    ("events", '("机器人" OR "具身智能") (大会 OR 峰会 OR 论坛 OR 展会)'),
    ("interviews", '("embodied AI" OR humanoid robotics) (interview OR podcast OR founder OR researcher)'),
    ("interviews", '("具身智能" OR "人形机器人") (专访 OR 访谈 OR 对话 OR 创始人)'),
    ("industry", '("embodied AI" OR robotics) (policy OR standards OR supply chain OR industry report)'),
    ("industry", '("具身智能" OR 机器人) (政策 OR 标准 OR 产业链 OR 供应链 OR 行动方案)'),
]

MEDIA_SITES = [
    ("news", "infoq.cn", "具身智能 OR 机器人 OR 人工智能"),
    ("news", "geekpark.net", "具身智能 OR 人形机器人 OR AI"),
    ("news", "jiqizhixin.com", "具身智能 OR 机器人 OR 视觉语言动作"),
    ("news", "jazzyear.com", "具身智能 OR 机器人产业"),
    ("news", "leiphone.com", "具身智能 OR 人形机器人"),
    ("news", "qbitai.com", "具身智能 OR 机器人"),
    ("news", "aiera.com", "具身智能 OR 机器人 OR AI"),
    ("news", "therobotreport.com", "humanoid OR embodied AI OR robotics"),
    ("news", "spectrum.ieee.org", "humanoid robot OR robot learning"),
    ("news", "techcrunch.com", "humanoid robot OR robotics AI"),
    ("news", "technologyreview.com", "robotics OR embodied AI"),
]

def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def get(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=25) as response:
        return response.read()

def parse_date(item):
    raw = item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""

def classify(default, title, summary):
    text = (title + " " + summary).lower()
    rules = [
        ("jobs", ["招聘", "招募", "hiring", "job opening", "career opportunity", "职位"]),
        ("company", ["融资", "募资", "投资", "收购", "并购", "订单", "中标", "交付", "量产", "funding", "investment", "acquisition", "purchase order"]),
        ("interviews", ["访谈", "专访", "对话", "采访", "interview", "podcast"]),
        ("events", ["大会", "峰会", "论坛", "展会", "conference", "summit", "workshop", "symposium"]),
        ("technology", ["论文", "arxiv", "preprint", "benchmark", "dataset", "vla", "vision-language-action", "world model", "robot learning", "模仿学习", "强化学习", "运动控制", "灵巧操作", "manipulation", "技术报告"]),
        ("application", ["工厂", "仓储", "物流", "医院", "养老院", "门店", "部署", "落地", "factory", "warehouse", "logistics", "hospital", "retail", "deployment"]),
        ("industry", ["政策", "行动方案", "标准", "规范", "产业规划", "产业链", "供应链", "policy", "regulation", "standard", "supply chain"]),
    ]
    for category, terms in rules:
        if any(term in text for term in terms):
            return category
    return default

def source_from_item(item, link):
    source = item.find("source")
    if source is not None and source.text:
        return clean(source.text)
    match = re.search(r"https?://([^/]+)", link)
    return match.group(1).removeprefix("www.") if match else "RSS"

def google_news(query, default_category, source_hint=None):
    params = {"q": query, "hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"}
    url = "https://news.google.com/rss/search?" + urlencode(params, quote_via=quote)
    root = ET.fromstring(get(url))
    items = []
    for item in root.findall("./channel/item")[:MAX_PER_QUERY]:
        title = clean(item.findtext("title"))
        link = item.findtext("link") or ""
        summary = clean(item.findtext("description"))
        date = parse_date(item)
        if not title or not link or not date:
            continue
        category = classify(default_category, title, summary)
        if default_category == "jobs" and category != "jobs":
            continue
        source = source_hint or source_from_item(item, link)
        items.append({
            "date": date, "category": category, "title": title,
            "summary": summary[:700], "source": source, "url": link,
            "confidence": "媒体检索线索 · 请核对原文",
            "evidence_type": "media_lead"
        })
    return items

def arxiv_items():
    query = '(all:embodied OR all:"vision-language-action" OR all:robot-learning) AND (all:robot OR all:robotics)'
    params = {"search_query": query, "start": 0, "max_results": 30, "sortBy": "submittedDate", "sortOrder": "descending"}
    url = "https://export.arxiv.org/api/query?" + urlencode(params)
    root = ET.fromstring(get(url))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    result = []
    for entry in root.findall("a:entry", ns):
        title = clean(entry.findtext("a:title", default="", namespaces=ns))
        summary = clean(entry.findtext("a:summary", default="", namespaces=ns))
        link_node = entry.find("a:id", ns)
        date = entry.findtext("a:published", default="", namespaces=ns)[:10]
        if not title or link_node is None or not date:
            continue
        result.append({
            "date": date, "category": "technology", "title": title,
            "summary": summary[:900], "source": "arXiv",
            "url": link_node.text, "confidence": "论文预印本 · 尚不代表同行评审结论",
            "evidence_type": "preprint"
        })
    return result

def main():
    collected = []
    for category, query in QUERIES:
        try:
            collected.extend(google_news(query, category))
            time.sleep(0.7)
        except Exception as exc:
            print("Google News query failed:", category, str(exc)[:160])

    for category, domain, terms in MEDIA_SITES:
        try:
            collected.extend(google_news(f"site:{domain} ({terms})", category, domain))
            time.sleep(0.5)
        except Exception as exc:
            print("Media search failed:", domain, str(exc)[:160])

    try:
        collected.extend(arxiv_items())
    except Exception as exc:
        print("arXiv fetch failed:", str(exc)[:160])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)).date()
    unique = {}
    for item in collected:
        try:
            if datetime.strptime(item["date"], "%Y-%m-%d").date() < cutoff:
                continue
        except Exception:
            continue
        key = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", item["title"].lower())
        if not key:
            continue
        if key not in unique or len(item.get("summary", "")) > len(unique[key].get("summary", "")):
            unique[key] = item

    items = sorted(unique.values(), key=lambda x: (x["date"], x["title"]), reverse=True)
    old = []
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            pass

    # Do not replace a populated dataset with an empty/near-empty run.
    if len(items) < 5 and len(old) > len(items):
        items = old
        warning = "本次抓取结果不足，保留上次数据；请检查采集日志。"
    else:
        warning = ""

    counts = {}
    for item in items[:150]:
        counts[item["category"]] = counts.get(item["category"], 0) + 1

    now = datetime.now(timezone.utc)
    payload = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "timezone": "原始来源日期；更新时间为UTC",
        "items_count": min(len(items), 150),
        "category_counts": counts,
        "fetch_warning": warning,
        "items": items[:150]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved", payload["items_count"], "items; categories:", counts)
    if warning:
        print("WARNING:", warning)

if __name__ == "__main__":
    main()
