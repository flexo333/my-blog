import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Loads all .md files from the /posts directory at the repo root.
// Using Astro 5's Content Layer glob loader so posts live alongside the rest
// of the repo rather than buried inside src/.
//
// KEY FEATURE: draft defaults to true — nothing ever publishes accidentally.
// To publish a post, add "draft: false" to its frontmatter.
// Posts without any frontmatter at all are treated as drafts.
const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './posts' }),
  schema: z.object({
    title: z.string().optional(),          // falls back to slug-derived title if absent
    description: z.string().optional(),
    date: z.coerce.date().optional(),
    draft: z.boolean().default(true),      // ← safe default: must opt-in to publish
    tags: z.array(z.string()).default([]),
  }),
});

const projects = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './projects' }),
  schema: z.object({
    name: z.string(),
    url: z.string().optional(),
    isNew: z.boolean().default(false),
    order: z.number().default(99),
  }),
});

export const collections = { blog, projects };
