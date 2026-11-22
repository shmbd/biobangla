import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const ROOT = process.cwd();
const localTmp = path.join(ROOT, '.astro', 'tmp');
fs.mkdirSync(localTmp, { recursive: true });

const mode = process.argv[2] || 'build';

const env = {
  ...process.env,
  ASTRO_TELEMETRY_DISABLED: '1',
  APPDATA: process.env.CI ? process.env.APPDATA : path.join(ROOT, '.astro'),
  XDG_CONFIG_HOME: process.env.CI ? process.env.XDG_CONFIG_HOME : path.join(ROOT, '.astro'),
  TEMP: localTmp,
  TMP: localTmp,
  RAYON_NUM_THREADS: '1',
};

if (mode === 'check') {
  execSync('npx astro check', { cwd: ROOT, env, stdio: 'inherit' });
} else {
  const distDir = path.join(ROOT, 'dist');
  fs.rmSync(distDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  execSync('npx astro build', { cwd: ROOT, env, stdio: 'inherit' });
  execSync('npx pagefind --site dist', { cwd: ROOT, env, stdio: 'inherit' });
}
