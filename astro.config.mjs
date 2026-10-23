import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import deepSea from './src/styles/deep-sea-shiki.json' with { type: 'json' };

export default defineConfig({
  site: 'https://projectpattie.com',
  integrations: [mdx()],
  markdown: {
    shikiConfig: {
      theme: deepSea,
      wrap: true,
      transformers: [
        {
          pre(node) {
            node.properties['data-language'] = this.options.lang;
          },
        },
      ],
    },
  },
});