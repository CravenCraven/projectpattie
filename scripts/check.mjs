#!/usr/bin/env node
import { validate } from './lib.mjs';
const problems = validate();
if (!problems.length) { console.log('\nAll posts have valid frontmatter.\n'); process.exit(0); }
console.error('\nFrontmatter problems:\n');
for (const [f, p] of problems) console.error(`  ${f}\n    ${p}`);
console.error('');
process.exit(1);
