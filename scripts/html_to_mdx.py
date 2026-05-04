#!/usr/bin/env python3
"""
Convert a standalone "pp-zt" style HTML post (like zero-trust-fixed.html)
into an Astro .mdx file suitable for src/content/blog/.

Usage:
    python3 scripts/html_to_mdx.py path/to/zero-trust-fixed.html
    python3 scripts/html_to_mdx.py path/to/file.html --slug custom-slug --category sysadmin

What it does:
  1. Strips the <style>...</style> block (PostLayout provides styles).
  2. Strips the <div id="pp-zt"> and <article class="pp-article"> wrappers
     (PostLayout provides the article wrapper).
  3. Reads the title from <h1 class="pp-title">, the subtitle from
     <p class="pp-subtitle">, and the meta line (category · date · readtime)
     from <div class="pp-meta">.
  4. Builds the .mdx frontmatter from those values.
  5. Converts multi-line <pre>...</pre> bodies to single-line JSX template
     literals, because MDX 3 reads `# ` at line starts as markdown headings
     and breaks the <pre> tag.
  6. Writes the result to src/content/blog/<slug>.mdx (or --out PATH).
"""
import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "src" / "content" / "blog"

VALID_CATEGORIES = {"sysadmin", "cybersecurity", "hackerbox", "tryhackme", "devops", "thoughts"}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def extract_meta(html: str) -> tuple[str, str, int]:
    """Return (category, iso_date, read_time_minutes) from <div class="pp-meta">."""
    m = re.search(r'<div class="pp-meta">(.*?)</div>', html, re.DOTALL)
    if not m:
        return "sysadmin", datetime.today().date().isoformat(), 5
    inner = m.group(1)

    cat_m = re.search(r"<span>(.*?)</span>", inner)
    category = cat_m.group(1).strip().lower() if cat_m else "sysadmin"
    if category not in VALID_CATEGORIES:
        print(f"  warn: category {category!r} not in {VALID_CATEGORIES}, defaulting to sysadmin")
        category = "sysadmin"

    # strip tags so we can scan for date and read time as plain text
    plain = re.sub(r"<[^>]+>", "", inner)
    date_m = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})", plain)
    if date_m:
        try:
            date_iso = datetime.strptime(
                f"{date_m.group(1)} {date_m.group(2)} {date_m.group(3)}", "%b %d %Y"
            ).date().isoformat()
        except ValueError:
            date_iso = datetime.today().date().isoformat()
    else:
        date_iso = datetime.today().date().isoformat()

    rt_m = re.search(r"(\d+)\s*min", plain)
    read_time = int(rt_m.group(1)) if rt_m else 5
    return category, date_iso, read_time


def extract_title(html: str) -> str:
    m = re.search(r'<h1 class="pp-title">(.*?)</h1>', html, re.DOTALL)
    if not m:
        return "untitled"
    inner = m.group(1)
    plain = re.sub(r"<[^>]+>", " ", inner)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain


def extract_subtitle(html: str) -> str:
    m = re.search(r'<p class="pp-subtitle">(.*?)</p>', html, re.DOTALL)
    if not m:
        return ""
    plain = re.sub(r"<[^>]+>", " ", m.group(1))
    return re.sub(r"\s+", " ", plain).strip()


def get_body(html: str) -> str:
    """Return the post body — everything inside <article class="pp-article">."""
    m = re.search(r'<article class="pp-article">(.*?)</article>', html, re.DOTALL)
    if m:
        return m.group(1).strip()
    # fallback: everything inside #pp-zt
    m = re.search(r'<div id="pp-zt">(.*?)</div>\s*$', html, re.DOTALL)
    if m:
        return m.group(1).strip()
    return html


def fix_multiline_pre(body: str) -> str:
    """Wrap multi-line <pre>...</pre> bodies as JSX template literals with \\n."""
    pat = re.compile(r"<pre>(.*?)</pre>", re.DOTALL)

    def wrap(m: re.Match) -> str:
        text = m.group(1)
        if "\n" not in text:
            return m.group(0)
        # already wrapped?
        if text.lstrip().startswith("{`") and text.rstrip().endswith("`}"):
            return m.group(0)
        # escape backslashes, backticks, ${ for safe template-literal embedding,
        # then collapse newlines to \n so JSX expression stays on one line.
        esc = (
            text.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
            .replace("\n", "\\n")
        )
        return "<pre>{`" + esc + "`}</pre>"

    return pat.sub(wrap, body)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input", help="Path to the standalone HTML file")
    p.add_argument("--slug", help="Override the auto-generated slug")
    p.add_argument("--category", help="Override the detected category")
    p.add_argument("--out", help="Override the output path")
    args = p.parse_args()

    src = Path(args.input).read_text(encoding="utf-8")

    title = extract_title(src)
    subtitle = extract_subtitle(src)
    category, date_iso, read_time = extract_meta(src)
    if args.category:
        if args.category not in VALID_CATEGORIES:
            sys.exit(f"--category must be one of {sorted(VALID_CATEGORIES)}")
        category = args.category

    body = get_body(src)
    # MDX 3 rejects HTML comments (<!-- ... -->). Strip them.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    # Collapse the blank-line gaps left behind by removed comments
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    # MDX 3 (JSX) requires void HTML elements to be self-closing: <br> -> <br/>
    void_tags = ["br", "hr", "img", "input", "meta", "link", "area",
                 "base", "col", "embed", "source", "track", "wbr", "param"]
    for tag in void_tags:
        # <br>, <br > -> <br/>
        body = re.sub(rf"<{tag}\s*>", f"<{tag}/>", body)
        # <br foo="bar"> -> <br foo="bar"/>  (only if not already self-closed)
        body = re.sub(
            rf"<{tag}(\s[^>]*[^/])>", rf"<{tag}\1/>", body
        )
    body = fix_multiline_pre(body)

    slug = args.slug or slugify(title) or "untitled"
    out_path = Path(args.out) if args.out else BLOG_DIR / f"{slug}.mdx"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # build frontmatter — quote strings to be YAML-safe
    def yaml_str(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    frontmatter = (
        "---\n"
        f"title: {yaml_str(title)}\n"
        f"description: {yaml_str(subtitle)}\n"
        f"date: {date_iso}\n"
        f"category: {category}\n"
        f"readTime: {read_time}\n"
        "---\n\n"
    )

    out_path.write_text(frontmatter + body + "\n", encoding="utf-8")
    print(f"  wrote {out_path}")
    print(f"  title:    {title}")
    print(f"  category: {category}")
    print(f"  date:     {date_iso}")
    print(f"  readTime: {read_time}")
    print(f"  slug:     {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
