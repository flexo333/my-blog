import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

// site URL is set by /setup to match your domain
export default defineConfig({
  site: 'https://willbright.link',
  integrations: [mdx(), sitemap()],
  output: 'static',
});
