import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';

const ROOT = process.cwd();
const DIST = path.join(ROOT, 'dist');

const REQUIRED_CATEGORIES = [
  'microbiology',
  'biotechnology',
  'genetics-genomics',
  'biomedical-science',
  'immunology',
  'environment-biodiversity',
  'marine-biology',
  'botany',
  'zoology',
  'evolution',
];

function walkFiles(dir, extFilter = null) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkFiles(full, extFilter));
    } else if (!extFilter || full.endsWith(extFilter)) {
      results.push(full);
    }
  }
  return results;
}

function resolveInternalPath(distRoot, rawHref, basePrefix = '') {
  const cleanHref = rawHref.split('#')[0].split('?')[0];
  if (!cleanHref) return true;

  let rel = cleanHref;
  if (basePrefix && basePrefix !== '/') {
    if (!rel.startsWith(basePrefix)) {
      return false;
    }
    rel = rel.slice(basePrefix.length) || '/';
  }

  const decoded = decodeURIComponent(rel).replace(/^\/+/, '');
  if (decoded === '') {
    return fs.existsSync(path.join(distRoot, 'index.html'));
  }

  const directFile = path.join(distRoot, decoded);
  const indexFile = path.join(distRoot, decoded, 'index.html');
  const htmlFile = `${directFile}.html`;
  return (
    fs.existsSync(directFile) ||
    fs.existsSync(indexFile) ||
    fs.existsSync(htmlFile)
  );
}

function verifyDistOutput(distRoot, basePrefix = '') {
  assert.ok(fs.existsSync(distRoot), `dist directory missing at ${distRoot}`);

  const requiredOutputs = [
    'index.html',
    'news/index.html',
    'categories/index.html',
    'explainers/index.html',
    'search/index.html',
    'about/index.html',
    'editorial-policy/index.html',
    'sources-attribution/index.html',
    'contact/index.html',
    '404.html',
    'rss.xml',
    'atom.xml',
    'robots.txt',
    'sitemap-index.xml',
    '.nojekyll',
    'pagefind/pagefind.js',
  ];

  for (const rel of requiredOutputs) {
    assert.ok(
      fs.existsSync(path.join(distRoot, rel)),
      `Missing required build artifact: ${rel}`
    );
  }

  for (const cat of REQUIRED_CATEGORIES) {
    assert.ok(
      fs.existsSync(path.join(distRoot, 'category', cat, 'index.html')),
      `Missing category page for: ${cat}`
    );
  }

  const htmlFiles = walkFiles(distRoot, '.html');
  assert.ok(htmlFiles.length >= 25, `Expected at least 25 HTML pages, found ${htmlFiles.length}`);

  // Broken internal link & asset check across all generated HTML pages
  const attrRegex = /\b(?:href|src)="([^"]+)"/g;
  const brokenLinks = [];

  for (const htmlFile of htmlFiles) {
    const html = fs.readFileSync(htmlFile, 'utf8');
    assert.ok(html.includes('lang="bn"'), `Missing Bangla lang="bn" in ${htmlFile}`);
    assert.ok(html.includes('<link rel="canonical"'), `Missing canonical link in ${htmlFile}`);

    let match;
    while ((match = attrRegex.exec(html)) !== null) {
      const target = match[1];
      if (
        target.startsWith('http://') ||
        target.startsWith('https://') ||
        target.startsWith('mailto:') ||
        target.startsWith('tel:') ||
        target.startsWith('#') ||
        target.startsWith('data:')
      ) {
        continue;
      }
      if (!resolveInternalPath(distRoot, target, basePrefix)) {
        brokenLinks.push(`${path.relative(distRoot, htmlFile)} -> ${target}`);
      }
    }
  }

  assert.equal(
    brokenLinks.length,
    0,
    `Broken internal links detected:\n${brokenLinks.join('\n')}`
  );

  // Verify Preprint Scientific Integrity Invariant on rendered HTML
  const preprintHtmlPath = path.join(
    distRoot,
    'articles',
    'biorxiv-preprint-ancient-environmental-dna-phylogeny',
    'index.html'
  );
  const preprintHtml = fs.readFileSync(preprintHtmlPath, 'utf8');
  assert.ok(
    preprintHtml.includes('সতর্কবার্তা: প্রিপ্রিন্ট গবেষণা (এখনও পিয়ার-রিভিউকৃত নয়)'),
    'Preprint article MUST display the non-peer-reviewed warning banner'
  );
  assert.ok(
    !preprintHtml.includes('বৈজ্ঞানিক যাচাইকরণ: পিয়ার-রিভিউকৃত'),
    'Preprint article MUST NEVER display a peer-reviewed verification banner'
  );

  // Verify JSON-LD structured data on an article page
  const crisprHtmlPath = path.join(
    distRoot,
    'articles',
    'crispr-cas9-programmable-gene-editing',
    'index.html'
  );
  const crisprHtml = fs.readFileSync(crisprHtmlPath, 'utf8');
  assert.ok(crisprHtml.includes('"@type":"NewsArticle"'), 'Article page missing NewsArticle JSON-LD');
  assert.ok(crisprHtml.includes('10.1126/science.1225829'), 'Article page missing DOI citation');
}

console.log('১/৩ প্রোডাকশন বিল্ড আউটপুট, SEO এবং অভ্যন্তরীণ লিংক পরীক্ষা করা হচ্ছে...');
verifyDistOutput(DIST, '');
console.log('✓ মূল ডোমেইন (`BASE_PATH=/`) বিল্ড ও লিংক পরীক্ষা সফল!');

console.log('২/৩ GitHub Pages সাব-পাথ (`BASE_PATH=/biobangla`) সামঞ্জস্য পরীক্ষা করা হচ্ছে...');
const localTmp = path.join(ROOT, '.astro', 'tmp');
fs.mkdirSync(localTmp, { recursive: true });

const env = {
  ...process.env,
  ASTRO_TELEMETRY_DISABLED: '1',
  APPDATA: path.join(ROOT, '.astro'),
  XDG_CONFIG_HOME: path.join(ROOT, '.astro'),
  TEMP: localTmp,
  TMP: localTmp,
  SITE_URL: 'https://example.github.io',
  BASE_PATH: '/biobangla',
};
fs.rmSync(DIST, { recursive: true, force: true, maxRetries: 5, retryDelay: 250 });
execSync('node scripts/build_site.mjs build', {
  cwd: ROOT,
  env,
  stdio: 'pipe',
});
verifyDistOutput(DIST, '/biobangla');
console.log('✓ GitHub Pages সাব-পাথ (`BASE_PATH=/biobangla`) বিল্ড ও লিংক পরীক্ষা সফল!');

console.log('৩/৩ ডিফল্ট প্রোডাকশন বিল্ড পুনঃস্থাপন করা হচ্ছে...');
fs.rmSync(DIST, { recursive: true, force: true, maxRetries: 5, retryDelay: 250 });
execSync('node scripts/build_site.mjs build', {
  cwd: ROOT,
  env: {
    ...env,
    SITE_URL: 'https://biobangla.org',
    BASE_PATH: '/',
  },
  stdio: 'pipe',
});
verifyDistOutput(DIST, '');
console.log('✓ সকল ফ্রন্টএন্ড বিল্ড, কনটেন্ট স্কিমা, Pagefind সার্চ ও লিংক পরীক্ষা শতভাগ সফল!');
