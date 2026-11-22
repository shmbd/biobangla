/**
 * Base-path safe URL helpers for GitHub Pages (supports both `/` custom domains
 * and `/<repo-name>` project subpaths).
 */
export function withBase(path: string): string {
  const base = import.meta.env.BASE_URL || '/';
  if (/^(https?:|mailto:|tel:|#)/i.test(path)) {
    return path;
  }
  const cleanBase = base === '/' ? '' : base.replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  if (cleanPath === '/' && cleanBase === '') {
    return '/';
  }
  if (cleanPath === '/') {
    return `${cleanBase}/`;
  }
  return `${cleanBase}${cleanPath}`;
}

export function canonicalUrl(pathname: string, site?: URL | string): string {
  const baseSite = (site ? site.toString() : import.meta.env.SITE || 'https://biobangla.org').replace(
    /\/+$/,
    ''
  );
  const normalizedPath = pathname.startsWith('/') ? pathname : `/${pathname}`;
  return `${baseSite}${normalizedPath}`;
}
