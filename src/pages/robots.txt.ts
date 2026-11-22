import type { APIContext } from 'astro';
import { canonicalUrl, withBase } from '../lib/urls';

export function GET(context: APIContext) {
  const sitemapHref = canonicalUrl(withBase('/sitemap-index.xml'), context.site);
  const body = `User-agent: *
Allow: /

Sitemap: ${sitemapHref}
`;

  return new Response(body, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}
