#!/usr/bin/env node
/**
 * Publish a post by adding/updating frontmatter.
 * Usage: node scripts/publish.mjs <post-slug>
 *
 * Uses the file's modification date as the post date, so a post
 * you drafted three weeks ago gets the right date automatically.
 */

import { readFile, writeFile, stat } from 'fs/promises';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dir   = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dir, '..');

const slug = process.argv[2];
if (!slug) {
  console.error('Usage: node scripts/publish.mjs <post-slug>');
  console.error('Example: node scripts/publish.mjs a-plan-is-a-guess');
  process.exit(1);
}

const postPath = join(rootDir, 'posts', `${slug}.md`);
if (!existsSync(postPath)) {
  console.error(`❌  Post not found: posts/${slug}.md`);
  process.exit(1);
}

const content  = await readFile(postPath, 'utf-8');
const fileStat = await stat(postPath);

// Use the file's last modification date as the post date.
// This means a draft you worked on last Tuesday gets published with that date,
// not today's date. Override by adding `date:` to frontmatter manually.
const fileDate = fileStat.mtime.toISOString().split('T')[0];

const titleFromSlug = slug
  .replace(/-/g, ' ')
  .replace(/\b\w/g, c => c.toUpperCase());

const hasFrontmatter = content.trimStart().startsWith('---');

let updated;

if (hasFrontmatter) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) {
    console.error('❌  Could not parse frontmatter');
    process.exit(1);
  }

  let fm     = match[1];
  const body = match[2];

  if (/^draft:/m.test(fm)) {
    fm = fm.replace(/^draft:.*$/m, 'draft: false');
  } else {
    fm += '\ndraft: false';
  }

  if (!/^date:/m.test(fm)) {
    fm += `\ndate: ${fileDate}`;
  }

  if (!/^title:/m.test(fm)) {
    fm = `title: "${titleFromSlug}"\n` + fm;
  }

  updated = `---\n${fm.trim()}\n---\n${body}`;

} else {
  // No frontmatter at all — prepend a full block
  updated = `---
title: "${titleFromSlug}"
date: ${fileDate}
draft: false
description: ""
tags: []
---

${content}`;
}

await writeFile(postPath, updated, 'utf-8');

console.log(`✅ Published: posts/${slug}.md`);
console.log(`   date:  ${fileDate}  (file modification date)`);
console.log(`\nEdit the frontmatter to set a title and description, then 'make deploy'.`);
