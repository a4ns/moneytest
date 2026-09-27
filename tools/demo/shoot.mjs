// Mobile screenshot + short scroll video for every rendered page (internal tool).
// Usage: node tools/demo/shoot.mjs tools/demo/out [only-slug]
// Writes <page>/shot.png (first screen), <page>/full.png and <page>/scroll.mp4 (H.264, fits WhatsApp).
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { execFileSync } from 'node:child_process';
import { readdirSync, existsSync, renameSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';

const root = resolve(process.argv[2] || 'tools/demo/out');
const only = process.argv[3];
const ffmpeg = execFileSync('python3', ['-c', 'import imageio_ffmpeg as f; print(f.get_ffmpeg_exe())']).toString().trim();
const viewport = { width: 390, height: 844 };

const browser = await chromium.launch({ proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined });
for (const name of readdirSync(root)) {
  const dir = join(root, name);
  if ((only && name !== only) || !existsSync(join(dir, 'index.html'))) continue;
  const ctx = await browser.newContext({
    viewport, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'ru-RU',
    recordVideo: { dir, size: { width: 720, height: 1558 } },
  });
  const page = await ctx.newPage();
  await page.goto('file://' + join(dir, 'index.html'), { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(dir, 'shot.png') });
  await page.screenshot({ path: join(dir, 'full.png'), fullPage: true });
  // ~6 s smooth scroll to the bottom, 1 s pause at both ends
  await page.evaluate(async () => {
    const end = document.documentElement.scrollHeight - innerHeight, t0 = performance.now(), dur = 6000;
    await new Promise(r => setTimeout(r, 1000));
    await new Promise(done => {
      const step = now => {
        const k = Math.min(1, (now - t0 - 1000) / dur);
        scrollTo(0, end * (k < 0 ? 0 : 0.5 - Math.cos(Math.PI * k) / 2));
        k < 1 ? requestAnimationFrame(step) : done();
      };
      requestAnimationFrame(step);
    });
    await new Promise(r => setTimeout(r, 1000));
  });
  const video = page.video();
  await ctx.close();
  const webm = await video.path();
  execFileSync(ffmpeg, ['-y', '-loglevel', 'error', '-i', webm, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
    '-profile:v', 'baseline', '-crf', '26', '-movflags', '+faststart', join(dir, 'scroll.mp4')]);
  rmSync(webm);
  console.log(dir);
}
await browser.close();
