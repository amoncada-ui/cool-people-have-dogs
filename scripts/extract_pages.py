#!/usr/bin/env python3
"""Extract Home / Library / About / 404 <main> content into page markdown
files, reusing the same href-rewriting logic as extract.py."""
import re
from pathlib import Path

from bs4 import BeautifulSoup
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent))
from extract import rewrite_all_hrefs, slug_for  # noqa: E402

SRC = Path("/home/claude/site/project")
OUT = Path("/home/claude/static-site/content/pages")
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("Home.dc.html", "home", "Cool People Have Dogs", "page.html"),
    ("Library.dc.html", "library", "The Library", "page.html"),
    ("About.dc.html", "about", "About", "page.html"),
    ("404.dc.html", "404", "Page Not Found", "page.html"),
]


def main():
    for filename, slug, title, template in PAGES:
        path = SRC / filename
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        rewrite_all_hrefs(soup)
        main_tag = soup.find("main")
        if main_tag:
            body_html = main_tag.decode_contents().strip()
        else:
            # Home page has no <main> wrapper — its content is a run of
            # top-level <section> elements between the header/menu and footer.
            sections = soup.find_all("section", recursive=True)
            body_html = "\n".join(str(s) for s in sections
                                   if s.find_parent("footer") is None)

        body_html = body_html.replace("{{accent}}", "#C1622D").replace("{{progress}}", "0")

        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_description = meta_desc_tag["content"] if meta_desc_tag else ""

        front = {
            "title": title,
            "meta_description": meta_description,
            "template": template,
        }
        fm_yaml = yaml.dump(front, allow_unicode=True, sort_keys=False, width=1000)
        (OUT / f"{slug}.md").write_text(f"---\n{fm_yaml}---\n{body_html}\n", encoding="utf-8")
        print(f"wrote {slug}.md ({len(body_html)} chars)")


if __name__ == "__main__":
    main()
