import fs from 'node:fs';
import path from 'node:path';

export const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
export const BLOG = path.join(ROOT, 'src/content/blog');

// Single source of truth: read the category enum straight out of config.ts
// so this never drifts from the Zod schema.
export function categories() {
  const src = fs.readFileSync(path.join(ROOT, 'src/content/config.ts'), 'utf8');
  const block = src.match(/category:\s*z\.enum\(\[([^\]]+)\]\)/);
  if (!block) throw new Error('Could not find the category enum in src/content/config.ts');
  return [...block[1].matchAll(/'([^']+)'/g)].map(m => m[1]);
}

export function slugify(s) {
  return s.toLowerCase().trim()
    .replace(/['']/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function parseFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return null;
  const out = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);
    if (kv) out[kv[1]] = kv[2].trim();
  }
  return out;
}

const REQUIRED = ['title', 'description', 'date', 'category'];

// Catches the exact mistakes that have cost time: pubDate instead of date,
// tags instead of category, category outside the enum.
export function validate() {
  const valid = categories();
  const problems = [];
  for (const file of fs.readdirSync(BLOG).filter(f => /\.mdx?$/.test(f) && !f.startsWith('.'))) {
    const fm = parseFrontmatter(fs.readFileSync(path.join(BLOG, file), 'utf8'));
    if (!fm) { problems.push([file, 'no frontmatter block found']); continue; }
    for (const key of REQUIRED) {
      if (!(key in fm)) {
        let hint = '';
        if (key === 'date' && 'pubDate' in fm) hint = "  (found 'pubDate' — this repo uses 'date')";
        if (key === 'category' && 'tags' in fm) hint = "  (found 'tags' — this repo needs 'category', tags are optional extra)";
        problems.push([file, `missing '${key}'${hint}`]);
      }
    }
    if (fm.category && !valid.includes(fm.category.replace(/['"]/g, ''))) {
      problems.push([file, `category '${fm.category}' is not one of: ${valid.join(', ')}`]);
    }
  }
  return problems;
}
