# /kubecraft page data

The page at `src/pages/kubecraft.astro` reads everything from these files. Edit the data, never the page.

| File | What it holds | Edit it when |
| --- | --- | --- |
| `meta.json` | hero copy, badge numbers, screenshots list, contact band, `updated` date | numbers change, you add screenshots |
| `hardware.json` | one row per node | a node changes |
| `stack.json` | one row per tool, with `status` and `since` | a tool goes live |
| `decisions.json` | ADR rows, each linked to the post it came from | you make a decision worth defending |
| `incidents.json` | things that broke, each linked to a post | something breaks and you write it up |
| `roadmap.json` | 20 goals, each with items and `status` | you finish a lesson or exercise |

## Status values

`done`, `doing`, `next`. Nothing else.

## Finishing something

1. In `roadmap.json`, change the item's `status` to `done`.
2. Add `"post": "<blog slug>"` if there's a write-up. The page links it.
3. If a tool went live, flip its row in `stack.json` and fill in `since`.
4. Bump `updated` in `meta.json`.
5. `npm run check`, then `npm run publish`.

## Screenshots

Drop PNGs into `public/kubecraft/screenshots/` and list them in `meta.json`:

```json
"screenshots": [
  { "file": "grafana-node-memory.png", "title": "Node memory", "note": "my Grafana panel" }
]
```

The section is hidden while the list is empty. Same for `photo`: set it to a path under `public/` and the hero shows it.

## Build logs

The page lists every post with `homelab: kubecraft` in its frontmatter. A post without that field can be added by slug in `meta.json` under `buildLogSlugs`.
