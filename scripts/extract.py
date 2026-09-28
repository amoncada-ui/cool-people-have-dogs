#!/usr/bin/env python3
"""
One-time migration script: reads the original Design-canvas .dc.html
article pages and converts each into a Markdown + YAML front-matter file
for the new static-site build (build.py). Desktop file is the source of
truth; mobile is now handled by responsive CSS instead of a duplicate file.
"""
import json
import re
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

SRC = Path("/home/claude/site/project")
OUT = Path("/home/claude/static-site/content/articles")
OUT.mkdir(parents=True, exist_ok=True)

CATEGORY_COLORS = {
    "BEHAVIOR": "#B4552F",
    "DIY CRAFTS": "#7A5980",
    "DIY TREATS": "#C1622D",
    "DOG NAMES": "#8A5A44",
    "ESSENTIALS": "#B8863B",
    "GAMES": "#C1495A",
    "GEAR": "#3D5A73",
    "LIFESTYLE": "#4F7359",
    "FOOD SAFETY": "#5C7A5C",
}

def slug_for(article_stem: str) -> str:
    """Article-BlueberryIceCream -> blueberry-ice-cream
    Article-DIYBandana -> diy-bandana (keeps acronym runs like DIY together)"""
    name = article_stem[len("Article-"):]
    # split before a capital that starts a new word: lower->Upper, or
    # end-of-acronym->Upper+lower (e.g. "DIYBandana" -> "DIY", "Bandana")
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name)
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "-", name)
    return name.lower()


def rewrite_href(href: str) -> str:
    if not href:
        return href
    if href in ("#", ""):
        return "#"
    if href == "/":
        return "/"
    if href.startswith("Article.dc.html") or href.startswith("Article-Mobile.dc.html"):
        # generic placeholder template page in the original design, never a
        # real published article — point anywhere-safe (home) instead.
        return "/"
    m = re.match(r"^(Article-[A-Za-z0-9]+)\.dc\.html(#.*)?$", href)
    if m:
        return f"/{slug_for(m.group(1))}/" + (m.group(2) or "")
    if href.startswith("About.dc.html") or href.startswith("About-Mobile.dc.html"):
        frag = href.split("#", 1)[1] if "#" in href else None
        return "/about/" + (f"#{frag}" if frag else "")
    if href.startswith("Library.dc.html") or href.startswith("Library-Mobile.dc.html"):
        frag = href.split("#", 1)[1] if "#" in href else None
        return "/library/" + (f"#{frag}" if frag else "")
    if href.startswith("mailto:"):
        return href
    return href


def rewrite_all_hrefs(soup):
    for a in soup.find_all("a", href=True):
        a["href"] = rewrite_href(a["href"])


def clean_html(tag) -> str:
    return tag.decode_contents().strip()


def extract(path: Path) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    rewrite_all_hrefs(soup)

    title = soup.find("h1").get_text(strip=True)
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag["content"] if meta_desc_tag else ""

    subhead_tag = soup.find("h1").find_next_sibling("p")
    subhead = subhead_tag.get_text(strip=True) if subhead_tag else ""

    # Topic tag / category
    topic_tag = soup.find("span", string=re.compile(r"^[A-Z][A-Z &]+$"))
    category = topic_tag.get_text(strip=True) if topic_tag else ""

    # Breadcrumb: Home / <category link> / current
    crumb_nav = soup.find("nav", attrs={"aria-label": "Breadcrumb"})
    category_label, category_slug = "", ""
    if crumb_nav:
        links = crumb_nav.find_all("a")
        if len(links) >= 2:
            category_label = links[1].get_text(strip=True)
            href = links[1]["href"]
            category_slug = href.split("#", 1)[1] if "#" in href else ""

    # Meta row: Published <date> · <read time> · <reviewed>
    meta_row_spans = []
    for div in soup.find_all("div"):
        text = div.get_text(" ", strip=True)
        if text.startswith("Published") and "min read" in text:
            meta_row_spans = [s.get_text(strip=True) for s in div.find_all("span") if s.get_text(strip=True)]
            break
    published_date = ""
    read_time = ""
    for s in meta_row_spans:
        if s.startswith("Published"):
            published_date = s.replace("Published", "").strip()
        elif "min read" in s:
            read_time = s

    # Hero caption
    hero_span = soup.find("span", string=re.compile(r"^\[Hero photo"))
    hero_caption = ""
    if hero_span:
        hero_caption = hero_span.get_text(strip=True).strip("[]").replace("Hero photo — ", "").replace("Hero photo — ", "")

    # FAQ from JSON-LD
    faq = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
        except Exception:
            continue
        if data.get("@type") == "FAQPage":
            for item in data.get("mainEntity", []):
                faq.append({
                    "question": item.get("name", ""),
                    "answer": item.get("acceptedAnswer", {}).get("text", ""),
                })

    # Article body: the <article> element with the article text (has a <p> Quick answer or headings)
    article_tag = None
    for cand in soup.find_all("article"):
        if cand.find("h2") or "Quick answer" in cand.get_text():
            article_tag = cand
            break
    body_html = clean_html(article_tag) if article_tag else ""

    # Sidebar extra: lead magnet + "More X" related block.
    # Found as the sibling content after the tag-row (RELATED TOPICS pills).
    sidebar_extra_html = ""
    tag_row_label = soup.find(string=re.compile("RELATED TOPICS"))
    if tag_row_label:
        label_div = tag_row_label.find_parent("div")
        outer_block = label_div.find_parent("div")  # the sidebar-block wrapper
        # outer_block's following siblings (until end of aside) are the
        # lead magnet promo + "More X" related-articles block.
        pieces = []
        for sib in outer_block.find_next_siblings():
            pieces.append(str(sib))
        sidebar_extra_html = "\n".join(pieces).strip()

    # Read Next block
    read_next_html = ""
    read_next_heading = soup.find(string=re.compile(r"^Read Next$"))
    if read_next_heading:
        section = read_next_heading.find_parent("section")
        if section:
            grid = section.find("div")
            if grid:
                read_next_html = clean_html(grid)

    accent = CATEGORY_COLORS.get(category, "#C1622D")
    body_html = body_html.replace("{{accent}}", accent)
    sidebar_extra_html = sidebar_extra_html.replace("{{accent}}", accent)
    read_next_html = read_next_html.replace("{{accent}}", accent)

    return {
        "title": title,
        "meta_description": meta_description,
        "subhead": subhead,
        "category": category,
        "category_label": category_label,
        "category_slug": category_slug,
        "published_date": published_date,
        "read_time": read_time,
        "hero_caption": hero_caption,
        "faq": faq,
        "body_html": body_html,
        "sidebar_extra_html": sidebar_extra_html,
        "read_next_html": read_next_html,
    }


def main():
    files = sorted(
        f for f in SRC.glob("Article-*.dc.html")
        if "Mobile" not in f.name and "TreatRoundup" not in f.name
    )
    print(f"Found {len(files)} source articles")
    ok, failed = 0, []
    for f in files:
        stem = f.stem.replace(".dc", "")
        slug = slug_for(stem)
        try:
            data = extract(f)
        except Exception as e:
            failed.append((f.name, str(e)))
            continue
        front = {k: v for k, v in data.items() if k not in ("body_html",)}
        front = {k: v for k, v in front.items() if v not in (None, "", [], {})}
        fm_yaml = yaml.dump(front, allow_unicode=True, sort_keys=False, width=1000)
        out_path = OUT / f"{slug}.md"
        out_path.write_text(f"---\n{fm_yaml}---\n{data['body_html']}\n", encoding="utf-8")
        ok += 1
    print(f"Converted {ok} articles")
    if failed:
        print("FAILED:")
        for name, err in failed:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
