import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const posts = await getCollection('blog');
  return rss({
    title: 'Project Pattie',
    description: 'Notes from a DevSecOps transition',
    site: context.site,
    items: posts
      .sort((a, b) => b.data.date - a.data.date)
      .map((post) => ({
        title: post.data.title,
        description: post.data.description,
        pubDate: post.data.date,
        link: `/blog/${post.id.replace(/\.mdx?$/, '')}/`,
      })),
  });
}
