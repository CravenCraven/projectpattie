#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { ROOT, BLOG, validate } from './lib.mjs';

const [slugArg, ...msgParts] = process.argv.slice(2);
const run = (cmd) => execSync(cmd, { cwd: ROOT, stdio: 'inherit' });
const die = (m) => { console.error(`\n${m}\n`); process.exit(1); };

if (!slugArg) die('Usage:  npm run publish <slug> "commit message"');
const message = msgParts.join(' ') || `Publish ${slugArg}`;

const file = path.join(BLOG, `${slugArg}.mdx`);
if (!fs.existsSync(file)) die(`No such post: src/content/blog/${slugArg}.mdx`);

// 1. Validate every post, with plain-language errors, before Astro gets a chance
// to fail with a stack trace.
console.log('\n[1/5] Checking frontmatter on every post');
const problems = validate();
if (problems.length) {
  console.error('\nFrontmatter problems:\n');
  for (const [f, p] of problems) console.error(`  ${f}\n    ${p}`);
  die('Fix these first. Nothing was built, committed or pushed.');
}
console.log('      all posts valid');

// 2. Flip this post out of draft.
console.log(`[2/5] Marking ${slugArg} as published`);
const src = fs.readFileSync(file, 'utf8');
if (/^draft:\s*true\s*$/m.test(src)) {
  fs.writeFileSync(file, src.replace(/^draft:\s*true\s*$/m, 'draft: false'));
  console.log('      draft: true -> draft: false');
} else {
  console.log('      already published');
}

// 3. Real build. This is the gate.
console.log('[3/5] Building');
try { run('npm run build'); }
catch { die('Build failed. Nothing was committed or pushed.'); }

// 4. Stage and commit.
console.log('[4/5] Committing');
const lock = path.join(ROOT, '.git/index.lock');
if (fs.existsSync(lock) && fs.statSync(lock).size === 0) {
  fs.unlinkSync(lock);
  console.log('      cleared a stale .git/index.lock');
}
run('git add -A src public astro.config.mjs package.json');
try { run(`git commit -m ${JSON.stringify(message)}`); }
catch { console.log('      nothing new to commit'); }

// 5. Push. Cloudflare Pages builds from main.
console.log('[5/5] Pushing');
run('git push origin main');

console.log(`\n  Published  https://projectpattie.com/blog/${slugArg}`);
console.log('  Cloudflare Pages builds on push. Give it a minute.\n');
