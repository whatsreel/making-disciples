// 90 ux floor: the built page, rendered in a real browser, meets the floor for an elder in
// his 70s reading on a phone (Jon, 2026-10-04: "too small a font, too confusing to navigate").
//
// Renders every view at 390x844 and 1280x800 (and checks overflow at 320), plus an opened
// argument sheet and a scripture popover, and counts:
//   text under 15px (uxui A-floor)          must be 0 at both sizes
//   tap targets under 44x44 at 390          must be 0 (uxui B-target, phone surface)
//   horizontal page overflow at 390 / 320   must be 0
//   Start buttons outside the first phone screen   must be 0
//   distinct font sizes per viewport        at most 6 (one scale)
//
// Local only: it needs the Playwright install in digital-comms. On a machine where that
// cannot load it FAILS rather than skips, so a gate run never passes unseen.
import { createRequire } from 'module';
import { existsSync, mkdtempSync, writeFileSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { tmpdir } from 'os';
import { fileURLToPath, pathToFileURL } from 'url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const PAGE = join(ROOT, 'outputs', 'argument-map.html');
const PW = 'C:/dev/claude/digital-comms/node_modules/playwright';
const VIEWS = ['start', 'board', 'brief', 'args', 'axes', 'rests', 'ask', 'fits', 'source', 'how'];   // how: no tab, opened from Start   // ask: hidden off claude.ai, but it renders
const LIMITS = { small: 0, targets: 0, overflow: 0, startOff: 0, sizes: 6 };

// Runs in the page. Counts only; samples carry a selector-ish label and the size.
const PROBE = () => {
  const vis = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || cs.display === 'none') return false;
    for (let p = el; p; p = p.parentElement) { const c = getComputedStyle(p); if (c.display === 'none' || c.visibility === 'hidden' || +c.opacity === 0) return false; }
    return true; };
  const label = (el) => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : '') +
    ' "' + (el.textContent || el.value || el.placeholder || '').trim().slice(0, 30) + '"';
  const texts = [...document.querySelectorAll('body *')].filter(el =>
    [...el.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim()) && vis(el));
  const small = texts.map(el => [el, parseFloat(getComputedStyle(el).fontSize)]).filter(([, s]) => s < 15)
    .map(([el, s]) => label(el) + ' ' + s + 'px');
  const sizes = [...new Set(texts.map(el => Math.round(parseFloat(getComputedStyle(el).fontSize) * 2) / 2))].sort((a, b) => a - b);
  const inter = [...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,summary')].filter(vis);
  // a checkbox is pressed through its label (the whole row), so the label is the target
  const box = (el) => (el.type === 'checkbox' || el.type === 'radio') && el.closest('label') ? el.closest('label') : el;
  const targets = inter.map(el => [el, box(el).getBoundingClientRect()]).filter(([, r]) => r.height < 43.5 || r.width < 43.5)
    .map(([el, r]) => label(el) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
  const overflow = Math.max(0, document.documentElement.scrollWidth - window.innerWidth);
  const startOff = [...document.querySelectorAll('#v-start.on .golist button')].filter(b => b.getBoundingClientRect().bottom > window.innerHeight).length;
  return { small, sizes, targets, overflow, startOff, interactive: inter.length };
};

// THE detection rule, used by the real run and the selftest alike.
function judge(results) {
  const tally = { small: 0, targets: 0, overflow: 0, startOff: 0 };
  const samples = [];
  const sizesBy = {};
  for (const r of results) {
    tally.small += r.small.length; tally.overflow += r.overflow > 0 ? 1 : 0; tally.startOff += r.startOff;
    if (r.vp === 'phone') tally.targets += r.targets.length;
    (sizesBy[r.vp] = sizesBy[r.vp] || new Set()); r.sizes.forEach(s => sizesBy[r.vp].add(s));
    r.small.slice(0, 2).forEach(s => samples.push(`${r.vp} ${r.view}: small text ${s}`));
    if (r.vp === 'phone') r.targets.slice(0, 2).forEach(s => samples.push(`${r.vp} ${r.view}: target ${s}`));
    if (r.overflow > 0) samples.push(`${r.vp} ${r.view}: page overflows by ${r.overflow}px`);
    if (r.startOff) samples.push(`${r.vp} ${r.view}: ${r.startOff} Start button(s) below the first screen`);
  }
  const pc = results.filter(r => r.view === 'popover-count');
  const popMissing = pc.filter(r => !r.popovers).length;
  if (pc.length) {
    console.log(`COUNT popover renders ${pc.length - popMissing}/${pc.length}`);
    if (popMissing) samples.push(`no key-argument sheet had a scripture reference to open: the popover went unchecked`);
  }
  const vps = Object.keys(sizesBy);
  for (const vp of vps) console.log(`COUNT ${vp}: distinct font sizes ${sizesBy[vp].size} [${[...sizesBy[vp]].join(', ')}] (limit ${LIMITS.sizes})`);
  console.log(`COUNT text-under-15px ${tally.small} · targets-under-44-at-390 ${tally.targets} · overflowing-views ${tally.overflow} · start-buttons-off-screen ${tally.startOff} (across ${results.length} renders)`);
  samples.slice(0, 14).forEach(s => console.log('SAMPLE ' + s));
  const sizesOk = vps.every(vp => sizesBy[vp].size <= LIMITS.sizes);
  return tally.small <= LIMITS.small && tally.targets <= LIMITS.targets && tally.overflow <= LIMITS.overflow
      && tally.startOff <= LIMITS.startOff && sizesOk && results.length > 0 && popMissing === 0;
}

async function measure(url, views, withSheet) {
  const require = createRequire(import.meta.url);
  const { chromium } = require(PW);
  const browser = await chromium.launch();
  const out = [];
  try {
    for (const [vp, w, h] of [['phone', 390, 844], ['desktop', 1280, 800], ['narrow', 320, 640]]) {
      const page = await browser.newPage({ viewport: { width: w, height: h } });
      for (const v of views) {
        await page.goto(url + '#' + v);
        await page.waitForTimeout(150);
        if (v === 'ask') {
          // no chat runs off claude.ai, so plant one answer in the page's own markup (as linkIds() writes it)
          // so the argument chips inside an answer are measured too
          await page.evaluate(() => { const m = document.getElementById('msgs'); if (m) m.innerHTML =
            '<div class="msg"><div class="who">Answer</div><p>The confession names three means [see ' +
            '<button class="chip" data-id="C17" data-v="Strong">C17</button>], and Scripture adds ' +
            '<button class="chip" data-id="C18" data-v="Strong">C18</button>.</p></div>'; });
        }
        const r = await page.evaluate(PROBE);
        if (vp === 'narrow') { r.small = []; r.targets = []; r.sizes = []; r.startOff = 0; }   // 320 is checked for overflow only
        if (vp === 'desktop') r.startOff = 0;                                                 // "the first phone screen"
        out.push({ vp, view: v, ...r });
      }
      if (withSheet && vp !== 'narrow') {
        // open the summary's key-argument sheets until one carries a scripture reference, then open its popover
        await page.goto(url + '#brief');
        const leads = await page.$$eval('button.lead[data-id]', bs => bs.map(b => b.getAttribute('data-id')));
        let popped = false;
        for (const id of leads) {
          // the same #brief again is an in-page jump, not a load: an open sheet and its scrim would stay
          // and block the next click. Reload so every attempt starts from a clean page.
          await page.goto(url + '#brief');
          await page.reload();
          await page.click(`button.lead[data-id="${id}"]`);
          await page.waitForTimeout(150);
          if (!popped) out.push({ vp, view: 'sheet ' + id, ...(await page.evaluate(PROBE)) });
          const ref = await page.$('#detail button.ref');
          if (ref) { await ref.click(); await page.waitForTimeout(100); out.push({ vp, view: 'popover', ...(await page.evaluate(PROBE)) }); popped = true; break; }
        }
        out.push({ vp, view: 'popover-count', popovers: popped ? 1 : 0, small: [], sizes: [], targets: [], overflow: 0, startOff: 0 });
      }
      await page.close();
    }
  } finally { await browser.close(); }
  return out;
}

async function main() {
  if (!existsSync(PW)) { console.log('COUNT renders 0'); console.log('SAMPLE Playwright not found at ' + PW + ': this check cannot run here'); process.exit(1); }
  if (process.argv[2] === '--selftest') {
    // One planted fault per page, so EACH count must catch its own fault: a count that silently
    // returned 0 would let its page pass and break the selftest.
    const dir = mkdtempSync(join(tmpdir(), 'ux90-'));
    const head = '<!doctype html><meta name="viewport" content="width=device-width"><body style="margin:0;font-size:17px">';
    const pages = {
      'small text': '<p style="font-size:11px">tiny</p>',
      'small target': '<button style="height:20px;font-size:17px">x</button>',
      'overflow': '<div style="width:600px">wide</div>',
      'start button off screen': `<div id="v-start" class="on"><div class="golist"><button style="min-height:44px;min-width:44px;font-size:17px;margin-top:900px">late</button></div></div>`,
      'too many font sizes': [15, 16, 17, 18, 19, 20, 21].map(s => `<p style="font-size:${s}px">size ${s}</p>`).join(''),
    };
    const missed = [];
    for (const [name, body] of Object.entries(pages)) {
      const f = join(dir, name.replace(/ /g, '-') + '.html');
      writeFileSync(f, head + body + '</body>');
      if (judge(await measure(pathToFileURL(f).href, ['start'], false))) missed.push(name);
    }
    // the popover rule needs no browser: a run whose sheets had no reference must fail
    const none = { vp: 'phone', view: 'popover-count', popovers: 0, small: [], sizes: [], targets: [], overflow: 0, startOff: 0 };
    if (judge([none])) missed.push('popover never opened');
    console.log(`COUNT selftest faults caught ${6 - missed.length}/6` + (missed.length ? ' (missed: ' + missed.join(', ') + ')' : ''));
    process.exit(missed.length ? 0 : 1);   // exit 0 = some planted fault passed = the runner fails this check
  }
  if (!existsSync(PAGE)) { console.log('COUNT renders 0'); console.log('SAMPLE outputs/argument-map.html missing: check 10 must run first'); process.exit(1); }
  process.exit(judge(await measure(pathToFileURL(PAGE).href, VIEWS, true)) ? 0 : 1);
}
main().catch(e => { console.log('COUNT renders 0'); console.log('SAMPLE ' + String(e && e.message || e).slice(0, 300)); process.exit(1); });
