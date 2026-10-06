#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { BLOG, categories, slugify } from './lib.mjs';

const rl = readline.createInterface({ input, output });
const ask = async (q, def = '') => {
  const a = (await rl.question(def ? `${q} [${def}] ` : `${q} `)).trim();
  return a || def;
};

const title = process.argv.slice(2).join(' ') || await ask('Title:');
if (!title) { console.error('A title is required.'); process.exit(1); }

const cats = categories();
console.log('\nCategory:');
cats.forEach((c, i) => console.log(`  ${i + 1}. ${c}`));
let idx = NaN;
while (Number.isNaN(idx) || idx < 1 || idx > cats.length) {
  idx = parseInt(await ask(`Pick 1-${cats.length}:`), 10);
}
const category = cats[idx - 1];

const description = await ask('\nOne-line description:');
const readTime = await ask('Read time in minutes:', '6');
const slug = await ask('Slug:', slugify(title));
const series = await ask('Series name (Enter to skip):', '');
const seriesOrder = series ? await ask('Part number:', '1') : '';
const subtitle = await ask('Stylized second line for the title (Enter to skip):', '');

const date = new Date();
const iso = date.toISOString().slice(0, 10);
const human = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

const fm = [
  '---',
  `title: "${title.replace(/"/g, '\\"')}"`,
  `description: "${description.replace(/"/g, '\\"')}"`,
  `date: ${iso}`,
  `category: ${category}`,
  `readTime: ${readTime}`,
  ...(series ? [`series: "${series}"`, `seriesOrder: ${seriesOrder}`] : []),
  'draft: true',
  '---',
].join('\n');

const h1 = subtitle
  ? `<h1 class="pp-title">${title}<br/><em>${subtitle}</em></h1>`
  : `<h1 class="pp-title">${title}</h1>`;

const body = `
<div class="pp-meta"><span>${category}</span> · ${human} · ${readTime} min read</div>

${h1}

<p class="pp-subtitle">${description}</p>

## First section

Write in plain Markdown from here down. Headings, lists, tables, code fences
and inline \`code\` are all styled. You do not need pp-* HTML for body content.
`;

const file = path.join(BLOG, `${slug}.mdx`);
if (fs.existsSync(file)) { console.error(`\n${slug}.mdx already exists. Pick another slug.`); process.exit(1); }
fs.writeFileSync(file, fm + '\n' + body);
rl.close();

console.log(`\n  Created  src/content/blog/${slug}.mdx`);
console.log(`  Preview  http://localhost:4321/blog/${slug}   (npm run dev)`);
console.log(`  Publish  npm run publish ${slug} "commit message"\n`);
