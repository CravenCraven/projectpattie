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

export const collections = { blog };