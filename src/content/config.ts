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
const kubecraft = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    section: z.string(),
    date: z.date(),
    timeSpent: z.string().optional(),
    confidence: z.number().min(1).max(5).default(3),
    tags: z.array(z.string()).optional(),
    difficulty: z.string().optional(),
    energy: z.string().optional(),
    nextGoal: z.string().optional(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog, kubecraft };