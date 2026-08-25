/**
 * 日報自檢 — 在 build_index.py 跑完之後執行，驗建置產物而不是原稿。
 *
 *   node tools/selfcheck.mjs 2026-08-25 [http://localhost:8899]
 *
 * 沒給 base 就自己在 repo 根目錄開一個臨時 http server（CSS 是絕對路徑
 * /assets/report.css，用 file:// 開會抓不到樣式，所以一定要走 http）。
 * 全過 exit 0，任一項失敗 exit 1 並印出哪一項。
 */
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DATE = process.argv[2];
const SITE = 'https://ai-medical-daily.peteraim.com';

if (!/^\d{4}-\d{2}-\d{2}$/.test(DATE || '')) {
  console.error('用法：node tools/selfcheck.mjs YYYY-MM-DD [base-url]');
  process.exit(2);
}

/* ---------- 需要時自己起 server ---------- */
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.xml': 'application/xml', '.txt': 'text/plain' };
let server = null, BASE = process.argv[3];
if (!BASE) {
  server = createServer(async (req, res) => {
    try {
      let p = join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if ((await stat(p).catch(() => null))?.isDirectory()) p = join(p, 'index.html');
      const body = await readFile(p);
      res.writeHead(200, { 'content-type': MIME[extname(p)] || 'application/octet-stream' });
      res.end(body);
    } catch { res.writeHead(404).end('not found'); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  BASE = `http://127.0.0.1:${server.address().port}`;
}

/* ---------- 找 Chromium ---------- */
const launch = {};
for (const p of ['/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
                 '/opt/pw-browsers/chromium/chrome-linux/chrome']) {
  const { existsSync } = await import('node:fs');
  if (existsSync(p)) { launch.executablePath = p; break; }
}

const R = [];
const ok = (n, c, d = '') => { R.push({ n, c, d }); };

const browser = await chromium.launch(launch);

/* ---------- 兩份日報 ---------- */
for (const [lang, path, canon] of [
  ['zh', `/reports/${DATE}.html`, `${SITE}/reports/${DATE}.html`],
  ['en', `/en/reports/${DATE}.html`, `${SITE}/en/reports/${DATE}.html`],
]) {
  const p = await browser.newPage();
  const http4xx = [];
  p.on('response', r => { if (r.status() >= 400) http4xx.push(`${r.url()} ${r.status()}`); });
  const resp = await p.goto(BASE + path, { waitUntil: 'networkidle' });
  if (!resp || resp.status() >= 400) { ok(`[${lang}] 頁面存在`, false, `HTTP ${resp?.status()}`); await p.close(); continue; }

  const n = await p.evaluate(() => ({
    zh: document.querySelectorAll('.zh, .zh-inline').length,
    en: document.querySelectorAll('.en, .en-inline').length,
  }));
  const self = lang === 'zh' ? n.zh : n.en, other = lang === 'zh' ? n.en : n.zh;
  ok(`[${lang}] 只剩自己語言的節點`, other === 0 && self > 0, `self=${self} other=${other}`);

  ok(`[${lang}] html lang`,
    (await p.evaluate(() => document.documentElement.lang)) === (lang === 'zh' ? 'zh-Hant' : 'en'));

  await p.setViewportSize({ width: 390, height: 800 });
  await p.waitForTimeout(250);
  ok(`[${lang}] 390px 無水平捲動`,
    !(await p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)));
  await p.setViewportSize({ width: 1280, height: 900 });

  const badHref = await p.evaluate(() => {
    const o = [];
    document.querySelectorAll('a').forEach(a => {
      const h = a.getAttribute('href') || '';
      if (!h) o.push('(空 href)');
      else if (!h.startsWith('#') && h !== '../index.html' && !h.startsWith('/') && !/^https?:\/\//.test(h)) o.push(h);
    });
    return o;
  });
  ok(`[${lang}] href 皆有效`, badHref.length === 0, badHref.slice(0, 4).join(' '));

  ok(`[${lang}] Google Analytics`, (await p.content()).includes('G-HJLDQZDK5V'));

  const icon = await p.locator('link[rel="icon"]').count();
  const ati = await p.locator('link[rel="apple-touch-icon"]').count();
  ok(`[${lang}] favicon + apple-touch-icon`, icon === 1 && ati === 1, `icon=${icon} ati=${ati}`);

  const can = await p.locator('link[rel="canonical"]').evaluateAll(e => e.map(x => x.getAttribute('href')));
  const og = await p.locator('meta[property="og:url"]').evaluateAll(e => e.map(x => x.content));
  ok(`[${lang}] canonical / og:url 指自己`,
    can.length === 1 && og.length === 1 && can[0] === canon && og[0] === canon, `${can} | ${og}`);

  const hl = await p.locator('link[rel="alternate"][hreflang]').evaluateAll(
    e => e.map(x => `${x.hreflang}=${x.getAttribute('href')}`));
  const want = [`zh-Hant=${SITE}/reports/${DATE}.html`, `en=${SITE}/en/reports/${DATE}.html`,
                `x-default=${SITE}/reports/${DATE}.html`];
  ok(`[${lang}] 三行 hreflang`, hl.length === 3 && want.every(w => hl.includes(w)), hl.join(' '));

  const cssLink = await p.locator('link[rel="stylesheet"][href="/assets/report.css"]').count();
  const fw = await p.evaluate(() => getComputedStyle(document.querySelector('.brand')).fontWeight);
  const inline = await p.evaluate(() =>
    [...document.querySelectorAll('style')].reduce((a, s) => a + s.textContent.length, 0));
  ok(`[${lang}] 外部 CSS 生效且無殘留 inline`,
    cssLink === 1 && fw === '700' && inline < 500 && http4xx.length === 0,
    `link=${cssLink} fw=${fw} inline=${inline} 4xx=${http4xx.join(',')}`);

  const seg = await p.locator('.seg a').evaluateAll(e => e.map(x => x.getAttribute('href')));
  ok(`[${lang}] 語言切換是真連結且指對`,
    seg.length === 2 && seg.includes(`/reports/${DATE}.html`) && seg.includes(`/en/reports/${DATE}.html`),
    seg.join(' '));

  const nav = await p.evaluate(() => ({
    gh: document.querySelectorAll('a.gh-star[href*="tingwei161803/ai-medical-daily"]').length,
    home: document.querySelectorAll('footer a[href="https://www.peteraim.com"]').length,
    li: document.querySelectorAll('footer a[href="https://www.linkedin.com/in/ai-med/"]').length,
    brand: document.querySelector('a.brand')?.getAttribute('href') === '../index.html',
    fab: document.querySelectorAll('a.home-fab[href="../index.html"]').length,
  }));
  ok(`[${lang}] 導覽元件齊全`,
    nav.gh === 1 && nav.home === 1 && nav.li === 1 && nav.brand && nav.fab === 1, JSON.stringify(nav));

  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight - 1500));
  await p.waitForTimeout(500);
  const g = await p.evaluate(() => {
    const u = document.getElementById('up').getBoundingClientRect();
    const h = document.querySelector('.home-fab').getBoundingClientRect();
    return { u: [u.top, u.bottom, u.right], h: [h.top, h.bottom, h.right], vw: innerWidth, vh: innerHeight };
  });
  ok(`[${lang}] ↑ 與 home 不重疊且在畫面內`,
    (g.u[1] <= g.h[0] + 1 || g.h[1] <= g.u[0] + 1) &&
    g.u[1] <= g.vh && g.h[1] <= g.vh && g.u[2] <= g.vw && g.h[2] <= g.vw, JSON.stringify(g));

  const cards = await p.evaluate(() => {
    const bad = [];
    const all = document.querySelectorAll('#top .card');
    all.forEach((c, i) => { if (!c.querySelector('a[href^="http"]')) bad.push(i + 1); });
    return { n: all.length, bad };
  });
  ok(`[${lang}] 新聞卡片皆有外部連結（5–8 則以上）`,
    cards.n >= 5 && cards.bad.length === 0, `卡片=${cards.n} 無連結的=${cards.bad.join(',') || '無'}`);

  await p.close();
}

/* ---------- 兩份首頁 ---------- */
const counts = [];
for (const [lang, path] of [['zh', '/index.html'], ['en', '/en/index.html']]) {
  const p = await browser.newPage();
  await p.goto(BASE + path, { waitUntil: 'networkidle' });
  const items = await p.locator('a.item').count();
  const today = (await p.content()).includes(DATE);
  counts.push(items);
  ok(`[${lang} 首頁] 有今天的靜態卡片`, today, `卡片數=${items}`);
  await p.close();
}
ok('兩份首頁的日報數一致', counts[0] === counts[1] && counts[0] > 0, counts.join(' vs '));

await browser.close();
server?.close();

/* ---------- 收尾 ---------- */
const fail = R.filter(r => !r.c);
for (const r of R) console.log(`${r.c ? 'PASS' : 'FAIL'} | ${r.n}${r.d ? ' | ' + r.d : ''}`);
console.log(`\n${R.length - fail.length}/${R.length} 通過`);
if (fail.length) { console.log(`\n未通過：\n  ` + fail.map(r => r.n).join('\n  ')); process.exit(1); }
