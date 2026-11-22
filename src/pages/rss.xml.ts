import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';
import { getCategoryMeta } from '../lib/categories';
import { withBase } from '../lib/urls';

export async function GET(context: APIContext) {
  const articles = (await getCollection('articles'))
    .filter((a) => a.data.status === 'published' || a.data.status === 'sample')
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

  const siteUrl = context.site || new URL('https://biobangla.org');

  return rss({
    title: 'জীববিজ্ঞান (biobangla) — বিজ্ঞানের নতুন আবিষ্কার, বাংলায় সহজ ব্যাখ্যা।',
    description:
      'জীববিজ্ঞান ও চিকিৎসা জীববিজ্ঞানের সাম্প্রতিক গবেষণাপত্রের তথ্যনিষ্ঠ বাংলা ব্যাখ্যা ও সারসংক্ষেপ।',
    site: siteUrl,
    customData: `<language>bn-BD</language>`,
    items: articles.map((article) => {
      const cat = getCategoryMeta(article.data.category);
      const statusPrefix = article.data.peer_reviewed ? '' : '[প্রিপ্রিন্ট — অ-পর্যালোচিত] ';
      return {
        title: `${statusPrefix}${article.data.title}`,
        pubDate: article.data.date,
        description: `${article.data.description} (উৎস: ${article.data.journal})`,
        link: withBase(`/articles/${article.id}`),
        categories: [cat.nameBn, ...article.data.tags],
      };
    }),
  });
}
