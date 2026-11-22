import { canonicalUrl, withBase } from './urls';

export interface ArticleSchemaInput {
  headline: string;
  description: string;
  urlPath: string;
  datePublished: Date;
  dateModified?: Date;
  authors: string[];
  desk?: string;
  categoryBn: string;
  tags: string[];
  doi?: string;
  sourceUrl: string;
  journal: string;
  peerReviewed: boolean;
  imageUrl?: string;
  site?: URL | string;
}

export function buildArticleJsonLd(input: ArticleSchemaInput): Record<string, unknown> {
  const fullUrl = canonicalUrl(input.urlPath, input.site);
  const siteRoot = canonicalUrl(withBase('/'), input.site);
  const ogImage = input.imageUrl
    ? input.imageUrl.startsWith('http')
      ? input.imageUrl
      : canonicalUrl(withBase(input.imageUrl), input.site)
    : canonicalUrl(withBase('/og-default.svg'), input.site);

  const schema: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'NewsArticle',
    headline: input.headline,
    description: input.description,
    inLanguage: 'bn-BD',
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': fullUrl,
    },
    datePublished: input.datePublished.toISOString(),
    dateModified: (input.dateModified || input.datePublished).toISOString(),
    articleSection: input.categoryBn,
    keywords: input.tags.join(', '),
    isAccessibleForFree: true,
    image: [ogImage],
    author: {
      '@type': 'Organization',
      name: input.desk || 'জীববিজ্ঞান বিজ্ঞান ডেস্ক',
      url: siteRoot,
    },
    publisher: {
      '@type': 'Organization',
      name: 'জীববিজ্ঞান (biobangla)',
      url: siteRoot,
      logo: {
        '@type': 'ImageObject',
        url: canonicalUrl(withBase('/favicon.svg'), input.site),
      },
    },
    citation: {
      '@type': 'ScholarlyArticle',
      name: `${input.journal}${input.doi ? ` (DOI: ${input.doi})` : ''}`,
      url: input.sourceUrl,
      author: input.authors.map((name) => ({
        '@type': 'Person',
        name,
      })),
    },
  };

  if (input.doi) {
    schema.sameAs = `https://doi.org/${input.doi.replace(/^https?:\/\/doi\.org\//i, '')}`;
  }

  return schema;
}

export function buildWebsiteJsonLd(site?: URL | string): Record<string, unknown> {
  const siteRoot = canonicalUrl(withBase('/'), site);
  const searchUrl = canonicalUrl(withBase('/search'), site);
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'জীববিজ্ঞান (biobangla)',
    alternateName: 'biobangla',
    description: 'বিজ্ঞানের নতুন আবিষ্কার, বাংলায় সহজ ব্যাখ্যা।',
    inLanguage: 'bn-BD',
    url: siteRoot,
    potentialAction: {
      '@type': 'SearchAction',
      target: `${searchUrl}?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  };
}
