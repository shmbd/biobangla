import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

const rawSiteUrl = (process.env.SITE_URL || 'https://biobangla.org').trim().replace(/\/+$/, '');
const rawBasePath = (process.env.BASE_PATH || '/').trim();
const normalizedBase =
  rawBasePath === '' || rawBasePath === '/'
    ? '/'
    : `/${rawBasePath.replace(/^\/+|\/+$/g, '')}`;

export default defineConfig({
  site: rawSiteUrl,
  base: normalizedBase,
  trailingSlash: 'ignore',
  output: 'static',
  compressHTML: true,
  integrations: [
    sitemap({
      i18n: {
        defaultLocale: 'bn',
        locales: {
          bn: 'bn-BD',
        },
      },
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
  markdown: {
    shikiConfig: {
      theme: 'github-light',
    },
  },
});
