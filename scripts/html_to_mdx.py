#!/usr/bin/env python3
"""
Convert a WordPress-exported HTML post OR a plain Markdown file into an Astro
.mdx file suitable for src/content/blog/.

Handles three input formats:
  1. FULL HTML — has <div id="pp-zt"><article class="pp-article"> with a
     pp-title / pp-meta / pp-subtitle / pp-toc block already present.
  2. FRAGMENT HTML — bare <p> and <h2> tags, no wrapper, no title block, no
     TOC. The converter synthesises the wrapper from CLI flags / defaults.
  3. MARKDOWN (.md) — standard Markdown (h1-h3, fenced code blocks, **bold**,
     `inline code`, [links], numbered/bulleted lists). Converted to the same
     pp-* classed HTML format.

Usage:
    # Full HTML (Zero Trust / Pentesting Lab files):
    python3 scripts/html_to_mdx.py path/to/zero-trust-fixed.html

    # Fragment HTML (User Management style — provide metadata):
    python3 scripts/html_to_mdx.py path/to/file.html \\
        --slug user-management-rhel-9 \\
        --title "User Management on RHEL 9" \\
        --description "..." \\
        --category sysadmin --date 2026-04-24 --read-time 14

    # Markdown:
    python3 scripts/html_to_mdx.py path/to/post.md \\
        --slug docker-for-beginners \\
        --title "Docker for Beginners" \\
        --description "..." \\
        --category devops --date 2026-04-24 --read-time 16
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


# ─────────────────────────────────────────────────────────────────────────────
# Markdown → pp-styled HTML body
# ─────────────────────────────────────────────────────────────────────────────

def _md_inline(text: str) -> str:
    """Apply inline Markdown transforms inside a single line of text."""
    # Inline code first so its contents aren't matched by other rules.
    placeholders: list[str] = []

    def stash_code(m: re.Match) -> str:
        # MDX 3 reads { and } as JSX expression delimiters even inside <code>.
        # Escape them as HTML entities so they render literally.
        content = m.group(1).replace("{", "&#123;").replace("}", "&#125;")
        placeholders.append(content)
        return f"\x00{len(placeholders) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash_code, text)

    # Bold: **text**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # Links: [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # Restore inline code placeholders
    def restore(m: re.Match) -> str:
        return f"<code>{placeholders[int(m.group(1))]}</code>"

    text = re.sub(r"\x00(\d+)\x00", restore, text)
    return text


def markdown_to_pp_body(md: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Convert a Markdown document body to pp-* classed HTML.
    Returns (body_html, [(h2_id, h2_text), ...]) for TOC synthesis.
    """
    lines = md.splitlines()
    out: list[str] = []
    sections: list[tuple[str, str]] = []
    seen_ids: set[str] = set()

    def make_id(text: str) -> str:
        slug = slugify(text) or "section"
        if slug in seen_ids:
            i = 2
            while f"{slug}-{i}" in seen_ids:
                i += 1
            slug = f"{slug}-{i}"
        seen_ids.add(slug)
        return slug

    i = 0
    in_toc_skip = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip the manual "## Table of Contents" block — we autogen our own TOC.
        if stripped.lower() == "## table of contents":
            in_toc_skip = True
            i += 1
            continue
        if in_toc_skip:
            # Skip until we hit a blank line followed by something that's not the TOC list.
            if stripped == "" or re.match(r"^\d+\.\s", stripped) or stripped.startswith("---"):
                i += 1
                continue
            in_toc_skip = False
            # Fall through to handle this line normally.

        # Skip horizontal rules (visual separators in source MD).
        if stripped == "---":
            i += 1
            continue

        # Top-level title — drop it; we synthesise from --title.
        if stripped.startswith("# ") and not stripped.startswith("## "):
            i += 1
            continue

        # H2
        if stripped.startswith("## ") and not stripped.startswith("### "):
            text = stripped[3:].strip()
            hid = make_id(text)
            sections.append((hid, text))
            out.append(f'<h2 class="pp-h2" id="{hid}">{_md_inline(text)}</h2>')
            i += 1
            continue

        # H3
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            out.append(f'<h3 class="pp-h3">{_md_inline(text)}</h3>')
            i += 1
            continue

        # Fenced code block: ```lang ... ```
        m = re.match(r"^```\s*([\w-]+)?\s*$", stripped)
        if m:
            lang = m.group(1) or "bash"
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and lines[i].rstrip() != "```":
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing ```
            code_text = "\n".join(code_lines)
            esc = (
                code_text.replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("${", "\\${")
                .replace("\n", "\\n")
            )
            out.append(
                '<div class="pp-code"><div class="pp-code-head"><div class="pp-code-dots">'
                '<div class="pp-code-dot" style="background:#ff5f57"></div>'
                '<div class="pp-code-dot" style="background:#febc2e"></div>'
                '<div class="pp-code-dot" style="background:#28c840"></div></div>'
                f'<div class="pp-code-lang">{lang}</div>'
                '<button class="pp-code-copy" '
                "onclick=\"navigator.clipboard.writeText(this.closest('.pp-code').querySelector('pre').textContent);"
                "this.textContent='copied!';setTimeout(()=>this.textContent='copy',1500)\">copy</button>"
                '</div><div class="pp-code-body">'
                f"<pre>{{`{esc}`}}</pre>"
                "</div></div>"
            )
            continue

        # Numbered list block (consecutive `N. ...` lines)
        if re.match(r"^\d+\.\s+", stripped):
            items: list[str] = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                item_text = re.sub(r"^\s*\d+\.\s+", "", lines[i]).rstrip()
                items.append(f"  <li>{_md_inline(item_text)}</li>")
                i += 1
            out.append("<ol>\n" + "\n".join(items) + "\n</ol>")
            continue

        # Bulleted list block (consecutive `- ...` lines)
        if re.match(r"^-\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\s*-\s+", lines[i]):
                item_text = re.sub(r"^\s*-\s+", "", lines[i]).rstrip()
                items.append(f"  <li>{_md_inline(item_text)}</li>")
                i += 1
            out.append("<ul>\n" + "\n".join(items) + "\n</ul>")
            continue

        # Blank line — paragraph separator
        if stripped == "":
            i += 1
            continue

        # Paragraph: gather contiguous non-blank, non-block lines
        para_lines: list[str] = []
        while i < len(lines):
            l = lines[i]
            ls = l.strip()
            if ls == "" or ls.startswith("#") or ls.startswith("```") or ls == "---" \
               or re.match(r"^\d+\.\s+", ls) or re.match(r"^-\s+", ls):
                break
            para_lines.append(ls)
            i += 1
        para = " ".join(para_lines)
        if para:
            out.append(f"<p>{_md_inline(para)}</p>")

    return "\n\n".join(out), sections


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
    is_markdown = src_path.suffix.lower() in (".md", ".markdown")

    # --- Resolve metadata -----------------------------------------------------
    if is_markdown:
        # Pull the first `# title` from the markdown if --title isn't passed.
        m = re.search(r"^#\s+(.+)$", src, flags=re.MULTILINE)
        md_title = m.group(1).strip() if m else None
        html_title = md_title
        html_subtitle = None
        html_cat = html_date = html_rt = None
    else:
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
    if is_markdown:
        body, sections = markdown_to_pp_body(src)
        needs_synthesis = True
    else:
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

    # Prepend the synthesised header (meta + title + subtitle + auto-TOC)
    if needs_synthesis:
        header = build_synthesised_header(
            title, subtitle, category, date_iso, read_time, sections
        )
        body = header + "\n" + body

    if not is_markdown:
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
