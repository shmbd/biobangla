import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';
import { canonicalUrl, withBase } from '../lib/urls';

function escapeXml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export async function GET(context: APIContext) {
  const articles = (await getCollection('articles'))
    .filter((a) => a.data.status === 'published' || a.data.status === 'sample')
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

  const site = context.site || 'https://biobangla.org';
  const siteRoot = canonicalUrl(withBase('/'), site);
  const selfUrl = canonicalUrl(withBase('/atom.xml'), site);
  const updated = articles[0]?.data.date.toISOString() || new Date().toISOString();

  const entriesXml = articles
    .map((article) => {
      const link = canonicalUrl(withBase(`/articles/${article.id}`), site);
      const statusNote = article.data.peer_reviewed ? '' : '[প্রিপ্রিন্ট — অ-পর্যালোচিত] ';
      const entryUpdated = (article.data.updatedDate || article.data.date).toISOString();
      return `  <entry>
    <title>${escapeXml(statusNote + article.data.title)}</title>
    <link href="${escapeXml(link)}" />
    <id>${escapeXml(link)}</id>
    <published>${article.data.date.toISOString()}</published>
    <updated>${entryUpdated}</updated>
    <summary>${escapeXml(`${article.data.description} (জার্নাল: ${article.data.journal})`)}</summary>
    <author><name>${escapeXml(article.data.desk)}</name></author>
  </entry>`;
    })
    .join('\n');

  const atomXml = `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="bn">
  <title>জীববিজ্ঞান (biobangla)</title>
  <subtitle>বিজ্ঞানের নতুন আবিষ্কার, বাংলায় সহজ ব্যাখ্যা।</subtitle>
  <link href="${escapeXml(selfUrl)}" rel="self" type="application/atom+xml" />
  <link href="${escapeXml(siteRoot)}" rel="alternate" type="text/html" />
  <id>${escapeXml(siteRoot)}</id>
  <updated>${updated}</updated>
${entriesXml}
</feed>
`;

  return new Response(atomXml, {
    headers: {
      'Content-Type': 'application/atom+xml; charset=utf-8',
    },
  });
}
