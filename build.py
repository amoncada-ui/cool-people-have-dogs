#!/usr/bin/env python3
"""
Static site builder for Cool People Have Dogs.
Reads Markdown+YAML-frontmatter content files, renders Jinja2 templates,
writes plain static HTML to output/. No JS framework, no build service
required beyond Python (jinja2, pyyaml, markdown — all in requirements.txt).

Usage: python3 build.py
"""
import json
import re
import shutil
from pathlib import Path

import markdown as mdlib
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
OUTPUT = ROOT / "output"
DOMAIN = "https://coolpeoplehavedogs.com"

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

CATEGORY_SLUGS = {
    "dogs-and-puppies": "Dogs & Puppies",
    "food-and-treats": "Food & Treats",
    "daily-life": "Daily Life",
    "diy-projects": "DIY Projects",
    "resources": "Resources",
}

CATEGORY_DESCRIPTIONS = {
    "dogs-and-puppies": "Names, behavior, and the everyday stuff of life with a dog.",
    "food-and-treats": "DIY treats, recipes, and what's actually safe for your dog to eat.",
    "daily-life": "Routines and essentials for every stage and situation.",
    "diy-projects": "Toys, gear, and weekend builds you can make yourself.",
    "resources": "Games and activities matched to your dog's energy and space.",
}

env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=False)


def load_article(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        data = yaml.safe_load(fm) or {}
    else:
        data, body = {}, text
    data["slug"] = path.stem
    data["_body_md"] = body.strip()
    return data


def render_body(md_text: str) -> str:
    """Article bodies are stored as raw HTML (ported directly from the
    original design) wrapped in a markdown-compatible file, so pass through
    unless it looks like plain markdown (no HTML tags at all)."""
    if "<" in md_text and ">" in md_text:
        return md_text
    return mdlib.markdown(md_text, extensions=["extra"])


def build_articles():
    articles_dir = CONTENT / "articles"
    articles = [load_article(p) for p in sorted(articles_dir.glob("*.md"))]
    by_slug = {a["slug"]: a for a in articles}
    tmpl = env.get_template("article.html")

    for a in articles:
        out_dir = OUTPUT / a["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        accent = CATEGORY_COLORS.get(a.get("category", ""), "#C1622D")
        canonical = f"{DOMAIN}/{a['slug']}/"

        schema_blocks = []
        schema_blocks.append(json.dumps({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{DOMAIN}/"},
                {"@type": "ListItem", "position": 2, "name": a.get("category_label", ""),
                 "item": f"{DOMAIN}/{a.get('category_slug', '')}/"},
                {"@type": "ListItem", "position": 3, "name": a["title"], "item": canonical},
            ],
        }))
        schema_blocks.append(json.dumps({
            "@context": "https://schema.org", "@type": "BlogPosting",
            "headline": a["title"], "description": a.get("meta_description", ""),
            "url": canonical,
            "author": {"@type": "Person", "name": a.get("author", "Jordan"), "url": f"{DOMAIN}/about/"},
            "publisher": {"@type": "Organization", "name": "Cool People Have Dogs"},
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        }))
        if a.get("faq"):
            schema_blocks.append(json.dumps({
                "@context": "https://schema.org", "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": q["question"],
                     "acceptedAnswer": {"@type": "Answer", "text": q["answer"]}}
                    for q in a["faq"]
                ],
            }))

        html = tmpl.render(
            root="",
            title=a["title"],
            og_title=a["title"],
            og_type="article",
            meta_description=a.get("meta_description", ""),
            canonical=canonical,
            schema_blocks=schema_blocks,
            accent=accent,
            progress=62,
            category=a.get("category", ""),
            category_slug=a.get("category_slug", ""),
            category_label=a.get("category_label", ""),
            subhead=a.get("subhead", ""),
            published_date=a.get("published_date", ""),
            read_time=a.get("read_time", ""),
            hero_image=a.get("hero_image"),
            hero_alt=a.get("hero_alt"),
            hero_caption=a.get("hero_caption", ""),
            download_file=a.get("download_file"),
            tags=a.get("tags", []),
            sidebar_extra_html=a.get("sidebar_extra_html"),
            read_next_html=a.get("read_next_html"),
            body_html=render_body(a["_body_md"]),
        )
        (out_dir / "index.html").write_text(html, encoding="utf-8")
    return articles


def copy_static():
    if (OUTPUT / "css").exists():
        shutil.rmtree(OUTPUT / "css")
    shutil.copytree(STATIC / "css", OUTPUT / "css")
    if (STATIC / "images").exists():
        if (OUTPUT / "images").exists():
            shutil.rmtree(OUTPUT / "images")
        shutil.copytree(STATIC / "images", OUTPUT / "images")
    if (STATIC / "downloads").exists():
        if (OUTPUT / "downloads").exists():
            shutil.rmtree(OUTPUT / "downloads")
        shutil.copytree(STATIC / "downloads", OUTPUT / "downloads")


def build_simple_pages(articles):
    """Home / Library / About / 404 — simple pages, each with its own
    template + markdown content file under content/pages/."""
    pages_dir = CONTENT / "pages"
    for path in sorted(pages_dir.glob("*.md")):
        data = load_article(path)
        slug = data["slug"]
        tmpl_name = data.get("template", f"{slug}.html")
        tmpl = env.get_template(tmpl_name)
        out_dir = OUTPUT if slug == "home" else OUTPUT / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        canonical = f"{DOMAIN}/" if slug == "home" else f"{DOMAIN}/{slug}/"
        schema_blocks = [json.dumps(b) for b in data.get("schema", [])]
        html = tmpl.render(
            root="",
            title=data.get("title", ""),
            og_title=data.get("title", ""),
            meta_description=data.get("meta_description", ""),
            canonical=canonical,
            schema_blocks=schema_blocks,
            accent=data.get("accent", "#C1622D"),
            progress=0,
            articles=articles,
            categories=CATEGORY_SLUGS,
            body_html=render_body(data["_body_md"]),
            **{k: v for k, v in data.items() if k not in
               ("title", "meta_description", "accent", "schema", "_body_md")}
        )
        (out_dir / "index.html").write_text(html, encoding="utf-8")


def build_category_pages(articles):
    """One real collection page per nav category (e.g. /dogs-and-puppies/),
    listing every article whose category_slug matches — generated straight
    from article front matter, so it can't drift out of sync like a
    hand-maintained page could."""
    tmpl = env.get_template("category.html")
    for slug, label in CATEGORY_SLUGS.items():
        in_category = [a for a in articles if a.get("category_slug") == slug]
        card_data = [
            {
                "slug": a["slug"],
                "title": a["title"],
                "category": a.get("category", ""),
                "accent": CATEGORY_COLORS.get(a.get("category", ""), "#C1622D"),
                "meta_description": a.get("meta_description", ""),
            }
            for a in in_category
        ]
        out_dir = OUTPUT / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        canonical = f"{DOMAIN}/{slug}/"
        schema_blocks = [json.dumps({
            "@context": "https://schema.org", "@type": "CollectionPage",
            "name": label, "url": canonical,
        })]
        html = tmpl.render(
            root="",
            title=f"{label} — Guides",
            og_title=f"{label} — Cool People Have Dogs",
            meta_description=f"Every {label} guide on Cool People Have Dogs, in one place.",
            canonical=canonical,
            schema_blocks=schema_blocks,
            accent="#C1622D",
            progress=0,
            category_label=label,
            category_description=CATEGORY_DESCRIPTIONS.get(slug, ""),
            articles=card_data,
        )
        (out_dir / "index.html").write_text(html, encoding="utf-8")


def build_sitemap(articles):
    urls = [f"{DOMAIN}/", f"{DOMAIN}/about/", f"{DOMAIN}/library/"]
    urls += [f"{DOMAIN}/{slug}/" for slug in CATEGORY_SLUGS]
    urls += [f"{DOMAIN}/{a['slug']}/" for a in articles if not a.get("noindex")]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"  <url><loc>{u}</loc></url>")
    xml.append("</urlset>")
    (OUTPUT / "sitemap.xml").write_text("\n".join(xml), encoding="utf-8")
    (OUTPUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nDisallow: /404\n\nSitemap: {DOMAIN}/sitemap.xml\n",
        encoding="utf-8",
    )


def copy_admin():
    if (OUTPUT / "admin").exists():
        shutil.rmtree(OUTPUT / "admin")
    shutil.copytree(ROOT / "admin", OUTPUT / "admin")


def main():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    articles = build_articles()
    copy_static()
    build_simple_pages(articles)
    build_category_pages(articles)
    build_sitemap(articles)
    copy_admin()
    # Netlify convention: a 404.html at the site root is served automatically
    # for unmatched routes, in addition to the normal /404/ page.
    src_404 = OUTPUT / "404" / "index.html"
    if src_404.exists():
        shutil.copy(src_404, OUTPUT / "404.html")
    print(f"Built {len(articles)} articles + pages to {OUTPUT}")


if __name__ == "__main__":
    main()
