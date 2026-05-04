# HANDOFF — projectpattie.com migration

Paste this whole file at the start of a new chat to resume work. It captures
state, conventions, and pending tasks.

## Project at a glance

- **Site**: WordPress blog migrated to Astro + Cloudflare Pages
- **Live (working) URL**: https://projectpattie.pages.dev
- **Custom domain (still broken)**: https://projectpattie.com (apex)
- **Custom domain (working)**: https://www.projectpattie.com
- **Repo**: https://github.com/CravenCraven/projectpattie (branch: `main`)
- **Local checkout**: `~/projectpattie`
- **Editor**: VS Code on a Mac
- **Stack**: Astro 4.11, `@astrojs/mdx` 3.1, content collections, Cloudflare Pages free tier
- **Auto-deploy**: every push to `main` triggers a Cloudflare Pages build (~60s)
- **Domain registrar**: Namecheap (no email used at this domain)

---

## Status

### Done
- Category pages now render posts from the content collection (root cause: an `.mdx` file was created at the wrong path, so `getCollection('blog')` returned `[]` site-wide).
- Post styling renders correctly. PostLayout uses `<style is:global>` because Astro's default `<style>` scoping doesn't apply to elements rendered from `.mdx` content.
- MDX 3 quirks documented and handled by the converter:
  - Multi-line `<pre>` bodies wrapped as JSX template literals (`<pre>{\`...\\n...\`}</pre>`).
  - HTML comments (`<!-- ... -->`) stripped (MDX 3 rejects them).
  - Void tags self-closed (`<br/>`, `<hr/>`, `<img/>`).
- Converter script at `scripts/html_to_mdx.py` turns a standalone "pp-zt"-style HTML post into a ready-to-build `.mdx` in `src/content/blog/`.
- Reusable post starter at `scripts/post-template.mdx`.
- Source HTML drafts kept in `posts-source/` (gitignored).

### Posts published
- `zero-trust-on-linux` — cybersecurity
- `pentesting-lab-part-1` — cybersecurity (no Final checklist yet — see below)
- `pentesting-lab-part-2` — cybersecurity (Final checklist added at the end + linked in TOC)

### Posts not yet converted
- Pentesting Lab Parts 3-4
- SELinux on RHEL 9
- systemd timers
- systemd timers exercises
- User management on RHEL 9
- vim for RHCSA

### Pending tasks
1. **Fix the apex domain `projectpattie.com`** (currently times out — see DNS section below).
2. **Backfill Final Checklist on `pentesting-lab-part-1.mdx`** to match the standard pattern used in Part 2 and Zero Trust.
3. **Convert remaining posts** using `scripts/html_to_mdx.py`, then add a Final Checklist to each before pushing.
4. **About + Contact pages** (still need to be rebuilt to match the WordPress originals).

---

## DNS situation (where we left off — pick up here)

- Namecheap is the registrar AND the active DNS host. Nameservers are still `ns1.registrar-servers.com` / `ns2.registrar-servers.com`.
- The domain has been added to Cloudflare's DNS panel (`dash.cloudflare.com → projectpattie.com`) but **the nameservers at Namecheap have never been switched to the Cloudflare-assigned ones**.
- `www.projectpattie.com` works because Namecheap holds a `CNAME www → projectpattie.pages.dev`. That part is fine.
- `projectpattie.com` (apex) doesn't work. Tried two redirect approaches at Namecheap:
  - **Masked URL Redirect** → broken (Cloudflare Pages refuses to be iframed, so the page never loads).
  - **Permanent (301) URL Redirect** → also broken because Namecheap's URL Redirect Record does not provision an SSL cert for the apex. Browsers force HTTPS, the TLS handshake hangs, request times out.
- The real fix: **move nameservers to Cloudflare**, then add `projectpattie.com` and `www.projectpattie.com` as custom domains in the Cloudflare Pages project. Cloudflare provisions the SSL cert and uses CNAME flattening so the apex works.
- User has no email at `projectpattie.com`, so the existing TXT/SPF records and Email Forwarding can be discarded during the move.
- User wants both apex and www to serve. No strong preference for which is canonical — assume apex is canonical, www → 301 → apex (the standard for personal blogs).

### Next steps when we resume DNS work
1. User logs into `dash.cloudflare.com → Websites → projectpattie.com → Overview`. Pastes back the two assigned Cloudflare nameservers (e.g. `kate.ns.cloudflare.com` / `liam.ns.cloudflare.com` — they're random per-account).
2. User goes to `dash.cloudflare.com → projectpattie.com → DNS → Records` and pastes a screenshot. Clean any auto-imported junk before flipping nameservers.
3. In Namecheap (`Domain List → projectpattie.com → Manage → Nameservers`), select **Custom DNS** and replace the two `*.registrar-servers.com` entries with the two Cloudflare nameservers. Save.
4. Wait for propagation (5-30 min typically; Cloudflare emails when the zone goes Active).
5. In Cloudflare Pages (`Workers & Pages → projectpattie → Custom domains`), add **`projectpattie.com`** and **`www.projectpattie.com`**. Cloudflare creates the right CNAME-flattened DNS records and provisions SSL.
6. Optional: a **Page Rule** or **Bulk Redirect** to forward `www.projectpattie.com/*` → `https://projectpattie.com/$1` (301). Cloudflare Free includes 3 page rules.
7. Verify with `curl -I https://projectpattie.com` (expect 200) and `curl -I https://www.projectpattie.com` (expect 301 to apex).

---

## Repo conventions

### File layout
```
~/projectpattie/
├── posts-source/                  # raw HTML drafts (gitignored)
├── scripts/
│   ├── html_to_mdx.py             # WordPress-HTML → MDX converter
│   └── post-template.mdx          # starter skeleton for new posts
├── src/
│   ├── content/
│   │   ├── config.ts              # blog collection schema
│   │   └── blog/                  # ALL published posts live here, flat, one .mdx per post
│   ├── layouts/
│   │   ├── BaseLayout.astro       # general layout (homepage, About, Contact)
│   │   └── PostLayout.astro       # post layout — uses <style is:global>
│   ├── pages/
│   │   ├── index.astro
│   │   ├── about.astro
│   │   ├── contact.astro
│   │   ├── blog/[slug].astro      # dynamic route pulling from blog collection
│   │   └── category/[category].astro
│   └── components/
└── astro.config.mjs
```

### Frontmatter schema (every post must conform)
```yaml
title: "string"
description: "string"
date: 2026-04-24                   # ISO date
category: cybersecurity             # one of: sysadmin, cybersecurity, hackerbox, tryhackme, devops, thoughts
readTime: 7                         # optional, integer minutes
draft: false                        # optional, hides post when true
```

### Styling classes (defined globally in PostLayout.astro)
- Layout: `.pp-article`, `.pp-meta`, `.pp-title`, `.pp-subtitle`
- Sections: `.pp-h2`, `.pp-toc`, `.pp-toc-label`, `.pp-series`
- Code: `.pp-code`, `.pp-code-head`, `.pp-code-dots`, `.pp-code-dot`, `.pp-code-lang`, `.pp-code-copy`, `.pp-code-body`
- Callouts: `.pp-note`, `.pp-next`
- Inline color: `.c-pink`, `.c-cyan`, `.c-green`, `.c-orange`, `.c-light`

### MDX gotchas (the converter handles all of these — only matters if writing by hand)
- **Multi-line `<pre>`**: must be wrapped as `<pre>{\`line1\\nline2\\nline3\`}</pre>`. Real newlines between `<pre>` and `</pre>` will break the build.
- **HTML comments**: not allowed. Use `{/* mdx comment */}` if needed.
- **Void tags**: `<br/>`, `<hr/>`, `<img src="..." alt="..." />`. No bare `<br>`.
- **Underscore-prefixed filenames** (`_foo.mdx`) are excluded from the build by Astro convention. Don't use as a "draft hide" mechanism — use `draft: true` in frontmatter instead.
- **Backticks inside template literals** must be escaped `\\\``.
- **`${`** inside template literals must be escaped `\\${`.

### Final Checklist pattern (every post must end with one)
Every post ends with an `<h2 class="pp-h2" id="checklist">` followed by a `.pp-code` block with bash-style numbered verification commands. The TOC at the top of the post must include `<li><a href="#checklist">…</a></li>` so readers can jump to it. See `scripts/post-template.mdx` for the exact shape, or copy from `pentesting-lab-part-2.mdx`.

The converter does NOT auto-generate this — content is post-specific. Manual step after every conversion.

---

## Workflows (cheat sheet)

### Add a brand-new post from scratch
```bash
cd ~/projectpattie
cp scripts/post-template.mdx src/content/blog/<slug>.mdx
# edit in VS Code, fill in content, customize the Final Checklist
npm run dev   # preview at http://localhost:4321/blog/<slug>
git add src/content/blog/<slug>.mdx
git commit -m "post: <slug>"
git push origin main
# Cloudflare auto-builds in ~60s
```

### Convert a WordPress HTML draft
```bash
cd ~/projectpattie
mkdir -p posts-source
mv ~/Downloads/whatever.html posts-source/
python3 scripts/html_to_mdx.py posts-source/whatever.html --slug whatever
# Open src/content/blog/whatever.mdx in VS Code, add a Final Checklist
# (paste the block from scripts/post-template.mdx, customize items, add to TOC)
npm run dev   # preview
git add src/content/blog/whatever.mdx
git commit -m "post: whatever"
git push origin main
```

### Local preview
```bash
cd ~/projectpattie
npm run dev
# open http://localhost:4321 — leave the terminal running
# Ctrl+C to stop
```

### Production check after pushing
- Visit `https://projectpattie.pages.dev/blog/<slug>` (NOT `projectpattie.com` — apex is broken until DNS is fixed).
- Hard-refresh with **Cmd+Shift+R** to bypass Cloudflare cache.
- Cloudflare deployment status: `dash.cloudflare.com → Workers & Pages → projectpattie → Deployments`.

---

## What I want help with next

(fill this in when resuming — example items below)

- [ ] Walk me through moving Namecheap nameservers to Cloudflare. I'll paste the two Cloudflare nameserver names and a screenshot of my current Cloudflare DNS records before we change anything.
- [ ] Convert Pentesting Lab Part 3 (HTML attached).
- [ ] Help me write the About page.
- [ ] Backfill a Final Checklist on Pentesting Lab Part 1.

---

*Generated 2026-05-04 to capture session state for continuation.*
