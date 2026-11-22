import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { CATEGORY_SLUGS } from './lib/categories';

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './content/articles' }),
  schema: z
    .object({
      title: z.string().min(10),
      description: z.string().min(25),
      date: z.coerce.date(),
      updatedDate: z.coerce.date().optional(),
      category: z.enum(CATEGORY_SLUGS),
      tags: z.array(z.string().min(1)).min(1),
      authors: z.array(z.string().min(1)).min(1),
      desk: z.string().default('জীববিজ্ঞান গবেষণা ডেস্ক'),
      journal: z.string().min(2),
      doi: z.string().optional(),
      source_url: z.string().url(),
      research_type: z.enum(['original-research', 'review', 'preprint', 'editorial']),
      peer_reviewed: z.boolean(),
      publication_status: z.enum(['peer-reviewed', 'preprint', 'editorial-summary']),
      study_model: z
        .enum([
          'in-vitro',
          'animal',
          'human-observational',
          'human-clinical',
          'computational',
          'field-ecology',
          'multi-study',
        ])
        .default('multi-study'),
      license: z.string().min(2),
      image: z.string().optional(),
      image_alt: z.string().optional(),
      image_attribution: z.string().optional(),
      illustration_motif: z
        .enum([
          'microbe',
          'crispr',
          'dna',
          'cell',
          'antibody',
          'ecosystem',
          'marine',
          'leaf',
          'zoology',
          'phylogeny',
        ])
        .optional(),
      language: z.string().default('bn'),
      status: z.enum(['published', 'sample', 'draft', 'review']).default('published'),
      featured: z.boolean().default(false),
      is_sample: z.boolean().default(false),
      key_findings: z.array(z.string()).optional(),
    })
    .superRefine((data, ctx) => {
      // STRICT SCIENTIFIC INTEGRITY INVARIANT:
      // Preprints must NEVER be marked peer_reviewed: true.
      if (
        (data.research_type === 'preprint' || data.publication_status === 'preprint') &&
        data.peer_reviewed === true
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message:
            'প্রিপ্রিন্ট নিবন্ধ কখনোই peer_reviewed: true হিসেবে চিহ্নিত করা যাবে না (Preprints must never be marked peer-reviewed).',
          path: ['peer_reviewed'],
        });
      }

      if (data.publication_status === 'peer-reviewed' && !data.peer_reviewed) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message:
            'publication_status "peer-reviewed" হলে peer_reviewed অবশ্যই true হতে হবে।',
          path: ['publication_status'],
        });
      }

      // Image reuse safety: if an external/hero image is provided, attribution is mandatory.
      if (data.image && (!data.image_attribution || data.image_attribution.trim().length < 5)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message:
            'ছবি ব্যবহারের ক্ষেত্রে সুস্পষ্ট লাইসেন্স ও উৎস স্বীকৃতি (image_attribution) আবশ্যিক।',
          path: ['image_attribution'],
        });
      }
    }),
});

const explainers = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './content/explainers' }),
  schema: z.object({
    title: z.string().min(8),
    description: z.string().min(20),
    date: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    category: z.enum(CATEGORY_SLUGS),
    tags: z.array(z.string().min(1)).min(1),
    difficulty: z.enum(['প্রাথমিক', 'মাধ্যমিক', 'উচ্চতর']).default('প্রাথমিক'),
    desk: z.string().default('জীববিজ্ঞান শিক্ষা ডেস্ক'),
    illustration_motif: z
      .enum([
        'microbe',
        'crispr',
        'dna',
        'cell',
        'antibody',
        'ecosystem',
        'marine',
        'leaf',
        'zoology',
        'phylogeny',
      ])
      .optional(),
    key_terms: z
      .array(
        z.object({
          bn: z.string(),
          en: z.string(),
          meaning: z.string(),
        })
      )
      .default([]),
    references: z
      .array(
        z.object({
          title: z.string(),
          url: z.string().url(),
        })
      )
      .default([]),
    language: z.string().default('bn'),
    status: z.enum(['published', 'sample', 'draft']).default('published'),
  }),
});

export const collections = {
  articles,
  explainers,
};
