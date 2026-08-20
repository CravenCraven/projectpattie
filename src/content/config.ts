import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.date(),
    category: z.enum([
      'sysadmin',
      'cybersecurity',
      'hackerbox',
      'tryhackme',
      'devops',
      'thoughts',
    ]),
    readTime: z.number().optional(),
    draft: z.boolean().optional().default(false),
    series: z.string().optional(),
    seriesOrder: z.number().optional(),
  }),
});
const demo = defineCollection({
  type: 'content',
  schema: z.object({
    num: z.string(),
    title: z.string(),
    sub: z.string(),
    blurb: z.string(),
    section: z.enum(['aprender', 'midia', 'infra']),
    status: z.string(),
    color: z.enum(['c1', 'c2', 'c3', 'c4', 'c5', 'down']),
    order: z.number(),
  }),
});

export const collections = { blog, demo };