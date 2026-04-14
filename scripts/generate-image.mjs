#!/usr/bin/env node
/**
 * Generate a DALL-E 3 hero image for a blog post.
 * Usage: node scripts/generate-image.mjs <post-slug>
 *
 * Reads the post from /posts/<slug>.md to extract title and context,
 * then generates an abstract editorial image and saves it to
 * public/images/posts/<slug>.jpg
 *
 * Requires OPENAI_API_KEY in environment.
 */

import OpenAI from 'openai';
import { readFile, writeFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dir   = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dir, '..');

// ── Args ──────────────────────────────────────────────────────────────────────
const slug = process.argv[2];
if (!slug) {
  console.error('Usage: node scripts/generate-image.mjs <post-slug>');
  console.error('Example: node scripts/generate-image.mjs a-plan-is-a-guess');
  process.exit(1);
}

if (!process.env.OPENAI_API_KEY) {
  console.error('❌  OPENAI_API_KEY is not set');
  process.exit(1);
}

// ── Read post ─────────────────────────────────────────────────────────────────
const postPath = join(rootDir, 'posts', `${slug}.md`);
let postContent = '';
try {
  postContent = await readFile(postPath, 'utf-8');
} catch {
  console.error(`❌  Post not found: posts/${slug}.md`);
  process.exit(1);
}

// Extract title from frontmatter, fall back to slug
const titleMatch = postContent.match(/^title:\s*["']?(.+?)["']?\s*$/m);
const title = titleMatch?.[1] ?? slug.replace(/-/g, ' ');

// Grab first couple of sentences for context
const bodyText = postContent
  .replace(/^---[\s\S]*?---/, '')  // strip frontmatter
  .trim()
  .slice(0, 300);

// ── Build prompt ──────────────────────────────────────────────────────────────
const prompt = `
Abstract editorial photograph for a blog post titled "${title}".

Context from the post: "${bodyText}"

Style requirements:
- Minimalist, atmospheric, thoughtful — not literal
- Warm natural light or moody studio lighting
- No text, no people, no faces
- Could be: textures, geometric forms, natural objects, light and shadow
- Colour palette: warm tones (cream, amber, warm greys, occasional deep blue)
- Aspect ratio: 16:9 (landscape)
- Quality: high-end editorial / magazine photography feel
- Think: The Economist covers, Monocle, Kinfolk magazine
`.trim();

console.log(`\n📝 Post: "${title}"`);
console.log(`🎨 Generating image...\n`);

// ── Call OpenAI ───────────────────────────────────────────────────────────────
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

let imageUrl;
try {
  const response = await client.images.generate({
    model:   'dall-e-3',
    prompt,
    size:    '1792x1024',
    quality: 'standard',
    n:       1,
  });
  imageUrl = response.data[0].url;
} catch (err) {
  console.error('❌  OpenAI API error:', err.message);
  process.exit(1);
}

console.log(`✅ Generated: ${imageUrl}\n`);

// ── Download and save ─────────────────────────────────────────────────────────
const outputDir  = join(rootDir, 'public', 'images', 'posts');
const outputFile = join(outputDir, `${slug}.jpg`);

if (!existsSync(outputDir)) {
  await mkdir(outputDir, { recursive: true });
}

const res = await fetch(imageUrl);
if (!res.ok) {
  console.error(`❌  Failed to download image: ${res.statusText}`);
  process.exit(1);
}

const buffer = await res.arrayBuffer();
await writeFile(outputFile, Buffer.from(buffer));

console.log(`💾 Saved: public/images/posts/${slug}.jpg`);
console.log(`\nAdd this to your post frontmatter:`);
console.log(`  image: /images/posts/${slug}.jpg\n`);
