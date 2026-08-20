# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev       # astro dev — local server with HMR
npm run build     # astro build — static output to dist/
npm run preview   # serve dist/ locally
```

There is no test suite, linter, or formatter configured. `npm run build` is the only verification step — it type-checks content frontmatter against the Zod schemas and fails on any post that violates them.

Convert a draft into a blog post:

```bash
python3 scripts/html_to_mdx.py posts-source/some-draft.html \
    --slug my-post --title "…" --description "…" \
    --category sysadmin --date 2026-05-04 --read-time 14
```

## What this is

A personal Astro 4 static blog (`projectpattie.com`) with a terminal/hacker aesthetic. Content lives in `src/content/`, pages are prerendered, no server runtime.

## Content pipeline

Drafts are written as standalone HTML (or Markdown) in `posts-source/` — **gitignored on purpose**, it's a scratch area — then converted by `scripts/html_to_mdx.py` into `src/content/blog/*.mdx`. The converter handles three input shapes (full HTML with a `pp-article` wrapper, bare HTML fragments, plain Markdown), slugifies and de-duplicates `<h2>` anchor ids, wraps multi-line `<pre>` bodies in MDX template literals, and emits the frontmatter block. `scripts/post-template.mdx` is the hand-authoring reference for the same output format.

**Posts are HTML-in-MDX, not Markdown.** Body content uses a `pp-*` class vocabulary (`pp-title`, `pp-subtitle`, `pp-toc`, `pp-h2`, `pp-code`, `pp-note`, `pp-next`, plus `c-pink`/`c-cyan`/`c-green`/`c-orange` inline spans). Every one of those classes is defined in the `<style is:global>` block inside `src/layouts/PostLayout.astro` — that block is the single source of truth for how a post looks. A handful of `pp-*` rules are repeated in `src/styles/global.css` with `!important` purely to stop the global stylesheet from overriding them on post pages; changing a post style usually means editing both.

Posts also hand-write a `<p class="pp-meta">` line and `<h1 class="pp-title">` that duplicate the frontmatter `category`/`date`/`readTime`/`title`. The layout does not render them, so both copies must be updated together.

## Collections

`src/content/config.ts` registers two collections:

- **blog** — `category` is a closed enum (`sysadmin`, `cybersecurity`, `hackerbox`, `tryhackme`, `devops`, `thoughts`). Optional `series` + `seriesOrder` group posts.
- **kubecraft** — learning-journal entries with their own fields (`confidence`, `energy`, `nextGoal`, …), rendered by `KubecraftLayout.astro`.

`src/content/demo/` is a third, **unregistered** collection (tile metadata for `src/pages/demo.astro`). Astro resolves it untyped, so its frontmatter is unvalidated.

The blog category list is duplicated in five places that must stay in sync: the Zod enum in `config.ts`, `links` in `src/components/Nav.astro`, `categoryNames` in `src/pages/index.astro`, the static paths in `src/pages/category/[category].astro`, and `VALID_CATEGORIES` in `scripts/html_to_mdx.py`.

Series pages live at `/series/<slugified-name>`; the slug is derived from the frontmatter string, so `series: "The Ticket Queue"` → `/series/the-ticket-queue`.

## Layouts

Two independent top-level layouts, each emitting its own full `<html>` document:

- `BaseLayout.astro` — imports `global.css`, carries the canonical/OG/Twitter meta, wraps `Nav` + `Footer`. Used by the index, category, series, and kubecraft pages.
- `PostLayout.astro` — does **not** extend BaseLayout. It duplicates the `<head>`, loads no `global.css`, and carries no OG/canonical tags, so blog posts get none of BaseLayout's SEO metadata.

`src/pages/demo.astro` and the raw files under `public/` (`pomodoro.html`, `kubecraft/kubecraft-entry-v2.html`) bypass both layouts and ship self-contained inline CSS.

## Styling

Two unrelated palettes coexist:

- `src/styles/global.css` — the live one. Dark navy (`#0d0d14`) with neon green/cyan/pink/orange accents.
- `src/styles/tokens.css` — a warm amber token set described as the site-wide source of truth, but **not imported anywhere**. Treat it as a pending redesign, not as active tokens.

## Known dead ends

Existing gaps, not bugs to fix unprompted — but don't build on them assuming they work:

- `src/pages/about.astro` and `src/pages/contact.astro` are empty files; `Nav` links to both and the build emits blank pages.
- `FeaturedHomelab.astro` filters for `series === 'homelab'`, which no post uses, so it always renders the empty state and its `/series/homelab/` link 404s.
- `demo.astro` filters posts against `LAB_CATEGORIES` (`'Kubernetes'`, `'Storage'`, …), none of which match the lowercase category enum, so its post list is always empty.
- `projectpattie.html` at the repo root is an untracked standalone mockup, not part of the build.
