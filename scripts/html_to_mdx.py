#!/usr/bin/env python3
"""
Convert a WordPress-exported or pp-zt-style HTML post into an Astro .mdx file
suitable for src/content/blog/.

Handles two input formats:
  1. FULL — has <div id="pp-zt"><article class="pp-article"> with a
     pp-title / pp-meta / pp-subtitle / pp-toc block already present.
  2. FRAGMENT — bare <p> and <h2> tags, no wrapper, no title block, no TOC.
     The converter synthesises the wrapper from CLI flags / sensible defaults.

Usage:
    # Full format (Zero Trust / Pentesting Lab files):
    python3 scripts/html_to_mdx.py path/to/zero-trust-fixed.html

    # Fragment format (User Management style — provide title etc.):
    python3 scripts/html_to_mdx.py path/to/file.html \\
        --slug user-management-rhel-9 \\
        --title "User Management on RHEL 9" \\
        --description "Going deep on every aspect of user and group management on RHEL 9." \\
        --category sysadmin \\
        --date 2026-04-24 \\
        --read-time 14

What it does:
  1. Strips any <style>...</style> block (PostLayout provides styles).
  2. Strips outer <div id="pp-zt"> and <article class="pp-article"> wrappers
     when present.
  3. Strips HTML comments (MDX 3 rejects them).
  4. Self-closes void tags (<br>, <hr>, <img>, etc.) so MDX 3 accepts them.
  5. Wraps multi-line <pre>...</pre> bodies as JSX template literals so MDX 3
     doesn't try to markdown-parse content inside <pre>.
  6. Adds class="pp-h2" and an auto-generated id to bare <h2> tags.
  7. Converts inline <strong style="color:#hex"> -> <span class="c-name">.
  8. If the input lacks a pp-title/meta/subtitle/toc block, synthesises one
     from CLI flags, derives a TOC from the h2 sections.
  9. Writes the result to src/content/blog/<slug>.mdx (or --out PATH).
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "src" / "content" / "blog"

VALID_CATEGORIES = {"sysadmin", "cybersecurity", "hackerbox", "tryhackme", "devops", "thoughts"}

# Maps the hex colors used in WordPress posts to the standardised CSS classes
# defined in PostLayout.astro.
COLOR_HEX_TO_CLASS = {
    "#ff00ff": "c-pink",
    "#f0f":     "c-pink",
    "#00d4ff": "c-cyan",
    "#0df":     "c-cyan",
    "#00ff9d": "c-green",
    "#ff9d00": "c-orange",
    "#e0e0f0": "c-light",
}


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)  # strip any HTML
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def extract_title_from_html(html: str) -> str | None:
    m = re.search(r'<h1 class="pp-title">(.*?)</h1>', html, re.DOTALL)
    if not m:
        return None
    plain = re.sub(r"<[^>]+>", " ", m.group(1))
    return re.sub(r"\s+", " ", plain).strip()


def extract_subtitle_from_html(html: str) -> str | None:
    m = re.search(r'<p class="pp-subtitle">(.*?)</p>', html, re.DOTALL)
    if not m:
        return None
    plain = re.sub(r"<[^>]+>", " ", m.group(1))
    return re.sub(r"\s+", " ", plain).strip()


def extract_meta_from_html(html: str) -> tuple[str | None, str | None, int | None]:
    """Return (category, iso_date, read_time) parsed from a pp-meta line, or Nones."""
    m = re.search(r'<div class="pp-meta">(.*?)</div>', html, re.DOTALL)
    if not m:
        return None, None, None
    inner = m.group(1)

    cat_m = re.search(r"<span>(.*?)</span>", inner)
    category = cat_m.group(1).strip().lower() if cat_m else None

    plain = re.sub(r"<[^>]+>", "", inner)
    date_iso = None
    date_m = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})", plain)
    if date_m:
        try:
            date_iso = datetime.strptime(
                f"{date_m.group(1)} {date_m.group(2)} {date_m.group(3)}", "%b %d %Y"
            ).date().isoformat()
        except ValueError:
            pass

    rt_m = re.search(r"(\d+)\s*min", plain)
    read_time = int(rt_m.group(1)) if rt_m else None

    return category, date_iso, read_time


def get_body(html: str) -> str:
    """Strip the wrapper and return the inner content."""
    m = re.search(r'<article class="pp-article">(.*?)</article>', html, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r'<div id="pp-zt">(.*?)</div>\s*$', html, re.DOTALL)
    if m:
        return m.group(1).strip()
    # No wrapper — strip any trailing <style> block (often appended by WP) and return.
    return html


def fix_multiline_pre(body: str) -> str:
    """Wrap multi-line <pre>...</pre> bodies as JSX template literals."""
    pat = re.compile(r"<pre>(.*?)</pre>", re.DOTALL)

    def wrap(m: re.Match) -> str:
        text = m.group(1)
        if "\n" not in text:
            return m.group(0)
        if text.lstrip().startswith("{`") and text.rstrip().endswith("`}"):
            return m.group(0)
        esc = (
            text.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
            .replace("\n", "\\n")
        )
        return "<pre>{`" + esc + "`}</pre>"

    return pat.sub(wrap, body)


def annotate_h2s(body: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Find bare or partially-classed <h2> tags. Add class="pp-h2" and an
    id="<slug>" if missing. Return (new_body, [(id, plain_text), ...]).
    Skips <h2> tags that already have an id (so existing <h2 class="pp-h2"
    id="..."> blocks are left alone).
    """
    seen_ids: set[str] = set()
    sections: list[tuple[str, str]] = []
    pat = re.compile(r"<h2([^>]*)>(.*?)</h2>", re.DOTALL)

    def make_unique(slug: str) -> str:
        if slug not in seen_ids:
            seen_ids.add(slug)
            return slug
        i = 2
        while f"{slug}-{i}" in seen_ids:
            i += 1
        seen_ids.add(f"{slug}-{i}")
        return f"{slug}-{i}"

    def replace(m: re.Match) -> str:
        attrs = m.group(1) or ""
        inner = m.group(2)
        plain = re.sub(r"<[^>]+>", " ", inner)
        plain = re.sub(r"\s+", " ", plain).strip()

        # extract existing id (if any)
        id_m = re.search(r'\bid="([^"]+)"', attrs)
        if id_m:
            heading_id = id_m.group(1)
            seen_ids.add(heading_id)
        else:
            heading_id = make_unique(slugify(plain) or "section")
            attrs = attrs.rstrip() + f' id="{heading_id}"'

        # ensure class="pp-h2" is present
        cls_m = re.search(r'\bclass="([^"]*)"', attrs)
        if cls_m:
            classes = cls_m.group(1).split()
            if "pp-h2" not in classes:
                classes.append("pp-h2")
                attrs = re.sub(r'\bclass="[^"]*"', f'class="{" ".join(classes)}"', attrs)
        else:
            attrs = attrs.rstrip() + ' class="pp-h2"'

        sections.append((heading_id, plain))
        return f"<h2{attrs}>{inner}</h2>"

    return pat.sub(replace, body), sections


def convert_inline_color_styles(body: str) -> str:
    """
    Convert <strong style="color:#XXXXXX">text</strong> and similar inline
    color styles to <span class="c-name">text</span> using the colour map.
    """
    pat = re.compile(r'<(strong|span|b)\s+style="color\s*:\s*(#[0-9a-fA-F]+)"\s*>(.*?)</\1>', re.DOTALL)

    def replace(m: re.Match) -> str:
        hex_color = m.group(2).lower()
        text = m.group(3)
        cls = COLOR_HEX_TO_CLASS.get(hex_color)
        if not cls:
            return m.group(0)  # unknown colour — leave as-is
        return f'<span class="{cls}">{text}</span>'

    return pat.sub(replace, body)


def build_synthesised_header(
    title: str, subtitle: str, category: str, date_iso: str, read_time: int,
    sections: list[tuple[str, str]],
) -> str:
    """
    Build the pp-meta / pp-title / pp-subtitle / pp-toc block when the input
    HTML didn't have one.
    """
    date_obj = datetime.fromisoformat(date_iso)
    pretty_date = date_obj.strftime("%b %-d, %Y") if hasattr(date_obj, "strftime") else date_iso
    # %-d is GNU; on macOS this also works in Python's strftime.

    toc_items = "\n".join(
        f'    <li><a href="#{sid}">{stext}</a></li>' for sid, stext in sections
    )
    if toc_items:
        toc_block = (
            '<div class="pp-toc">\n'
            '  <div class="pp-toc-label">// <span>what we\'re getting into</span></div>\n'
            '  <ol>\n'
            f"{toc_items}\n"
            '  </ol>\n'
            '</div>'
        )
    else:
        toc_block = ""

    parts = [
        f'<div class="pp-meta"><span>{category}</span> · {pretty_date} · {read_time} min read</div>',
        '',
        f'<h1 class="pp-title">{title}</h1>',
        '',
    ]
    if subtitle:
        parts.append(f'<p class="pp-subtitle">{subtitle}</p>')
        parts.append('')
    if toc_block:
        parts.append(toc_block)
        parts.append('')
    return "\n".join(parts)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input", help="Path to the standalone HTML file")
    p.add_argument("--slug", help="Override the auto-generated slug")
    p.add_argument("--title", help="Title (overrides any pp-title found in HTML)")
    p.add_argument("--description", help="Subtitle / SEO description (overrides pp-subtitle)")
    p.add_argument("--category", help="Category override; one of " + ", ".join(sorted(VALID_CATEGORIES)))
    p.add_argument("--date", help="ISO date (YYYY-MM-DD); overrides pp-meta date")
    p.add_argument("--read-time", type=int, help="Read time in minutes; overrides pp-meta")
    p.add_argument("--out", help="Override the output path")
    args = p.parse_args()

    src_path = Path(args.input)
    src = src_path.read_text(encoding="utf-8")

    # --- Resolve metadata -----------------------------------------------------
    html_title = extract_title_from_html(src)
    html_subtitle = extract_subtitle_from_html(src)
    html_cat, html_date, html_rt = extract_meta_from_html(src)

    title = args.title or html_title or src_path.stem.replace("-", " ").title()
    subtitle = args.description or html_subtitle or ""
    category = (args.category or html_cat or "sysadmin").lower()
    if category not in VALID_CATEGORIES:
        sys.exit(f"--category must be one of {sorted(VALID_CATEGORIES)} (got {category!r})")
    date_iso = args.date or html_date or datetime.today().date().isoformat()
    read_time = args.read_time or html_rt or 5

    # --- Body cleanup --------------------------------------------------------
    body = get_body(src)
    body = re.sub(r"<style\b[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    # MDX 3 (JSX) requires void HTML elements to be self-closing.
    void_tags = ["br", "hr", "img", "input", "meta", "link", "area",
                 "base", "col", "embed", "source", "track", "wbr", "param"]
    for tag in void_tags:
        body = re.sub(rf"<{tag}\s*>", f"<{tag}/>", body)
        body = re.sub(rf"<{tag}(\s[^>]*[^/])>", rf"<{tag}\1/>", body)

    # Inline <strong style="color:..."> -> <span class="c-...">
    body = convert_inline_color_styles(body)

    # Annotate h2 tags with class+id, harvest TOC sections.
    body, sections = annotate_h2s(body)

    # If the original HTML lacked the wrapper, prepend a synthesised one.
    needs_synthesis = not (html_title and html_subtitle is not None)
    if needs_synthesis:
        header = build_synthesised_header(
            title, subtitle, category, date_iso, read_time, sections
        )
        body = header + "\n" + body

    body = fix_multiline_pre(body)

    # --- Output --------------------------------------------------------------
    slug = args.slug or slugify(title) or "untitled"
    out_path = Path(args.out) if args.out else BLOG_DIR / f"{slug}.mdx"
    out_path.parent.mkdir(parents=True, exist_ok=True)

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
    if needs_synthesis:
        print(f"  synthesised header (input was a fragment with {len(sections)} sections)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
