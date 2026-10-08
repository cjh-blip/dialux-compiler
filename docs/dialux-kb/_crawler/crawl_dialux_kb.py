#!/usr/bin/env python3
"""抓取 DIALux evo 官方知识库（英文）为 Markdown 离线知识包。

用法:
    python3 crawl_dialux_kb.py [输出目录]

输出:
    <outdir>/README.md              总索引（分类 -> 文章）
    <outdir>/articles/<id>-<slug>.md 单篇
    <outdir>/_raw_index.json         抓取清单（含标题、分类、来源 URL、修改日期）
"""
import json
import os
import re
import sys
import time
import urllib.request
from html import unescape

BASE = "https://evo.support-en.dial.de"
HOME = BASE + "/support/home"
UA = "Mozilla/5.0 (compatible; knowledge-archiver/1.0)"

ART_RE = re.compile(r'/support/solutions/articles/(\d+)-([a-z0-9\-]+)')
CAT_RE = re.compile(r'/support/solutions/(\d+)"')


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            if i == tries - 1:
                print(f"  ! failed {url}: {e}")
                return ""
            time.sleep(1.5 * (i + 1))
    return ""


def strip_tags(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", html)
    html = re.sub(r"(?i)<li[^>]*>", "- ", html)
    html = re.sub(r"<[^>]+>", "", html)
    txt = unescape(html)
    txt = re.sub(r"[ \t\xa0]+", " ", txt)
    txt = re.sub(r"\n\s*\n\s*\n+", "\n\n", txt)
    return txt.strip()


def extract_article(html):
    """返回 (title, breadcrumb, modified, body)"""
    title = ""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if m:
        title = unescape(m.group(1)).split(" : ")[0].strip()
    modified = ""
    m = re.search(r"Modified on:\s*([^<]+)", html)
    if m:
        modified = m.group(1).strip()
    crumb = []
    m = re.search(r"(?is)<div[^>]*class=\"[^\"]*breadcrumb[^\"]*\"[^>]*>(.*?)</div>", html)
    if m:
        crumb = [unescape(x).strip() for x in re.findall(r">([^<>]+)<", m.group(1)) if x.strip()]
    body = ""
    i = html.find("article-body")
    if i > 0:
        seg = html[i:]
        j = seg.find("</article>")
        if j > 0:
            seg = seg[:j]
        body = strip_tags(seg)
        # 砍掉尾部固定噪音
        for tail in ["Did you find it helpful?", "Print\nModified on:"]:
            k = body.find(tail)
            if k > 0:
                body = body[:k]
        body = re.sub(r"^[^>]*?>", "", body).strip()
    return title, crumb, modified, body


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "dialux_kb"
    arts_dir = os.path.join(outdir, "articles")
    os.makedirs(arts_dir, exist_ok=True)

    print("fetch home ...")
    home = get(HOME)
    cats = sorted(set(CAT_RE.findall(home)))
    print(f"categories: {len(cats)}")

    found = {}  # id -> slug
    for a_id, slug in ART_RE.findall(home):
        found[a_id] = slug

    for cid in cats:
        url = f"{BASE}/support/solutions/{cid}"
        html = get(url)
        for a_id, slug in ART_RE.findall(html):
            found.setdefault(a_id, slug)
        time.sleep(0.4)
    print(f"articles discovered: {len(found)}")

    index = []
    for n, (a_id, slug) in enumerate(sorted(found.items()), 1):
        url = f"{BASE}/support/solutions/articles/{a_id}-{slug}"
        html = get(url)
        if not html:
            continue
        title, crumb, modified, body = extract_article(html)
        rec = {
            "id": a_id,
            "slug": slug,
            "title": title or slug,
            "breadcrumb": crumb,
            "modified": modified,
            "url": url,
            "body": body,
        }
        index.append(rec)
        fn = os.path.join(arts_dir, f"{a_id}-{slug}.md")
        cat = " / ".join(crumb) if crumb else "未分类"
        with open(fn, "w", encoding="utf-8") as f:
            f.write(f"# {rec['title']}\n\n")
            f.write(f"> 分类：{cat} ｜ 更新：{modified}\n")
            f.write(f"> 来源：{url}\n\n")
            f.write(body + "\n")
        if n % 20 == 0:
            print(f"  {n}/{len(found)}")
        time.sleep(0.35)

    with open(os.path.join(outdir, "_raw_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # 按分类聚合的索引
    by_cat = {}
    for r in index:
        key = " / ".join(r["breadcrumb"][1:-1]) if len(r["breadcrumb"]) > 2 else (
            " / ".join(r["breadcrumb"]) if r["breadcrumb"] else "未分类")
        by_cat.setdefault(key or "未分类", []).append(r)

    lines = [
        "# DIALux evo 官方知识库（英文）离线包",
        "",
        f"> 来源：{BASE}/support/home（DIALux 官方支持站点，英文版）",
        f"> 抓取时间：{time.strftime('%Y-%m-%d %H:%M')} ｜ 文章数：{len(index)}",
        "> 用途：供智能体在无网络或需要稳定引用时查阅 DIALux evo 的操作知识",
        "",
        "## 目录",
        "",
    ]
    for cat in sorted(by_cat):
        lines.append(f"- **{cat}**（{len(by_cat[cat])} 篇）")
        for r in sorted(by_cat[cat], key=lambda x: x["title"]):
            lines.append(f"  - [{r['title']}](articles/{r['id']}-{r['slug']}.md)")
    lines.append("")
    with open(os.path.join(outdir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"done: {len(index)} articles -> {outdir}")


if __name__ == "__main__":
    main()
