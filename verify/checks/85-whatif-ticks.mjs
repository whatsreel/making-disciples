// 85 what-if ticks: What if, with its boxes ticked in a real browser, lists exactly the arguments
// the build computed, gives every one a reason that is true, and pins the right count.
//
// WHY: check 80 proves the build's table (fallsAll) against a fresh computation, but not the page's
// reading of it. If the page decoded the table wrongly (bit order, argument order) every tick would
// name the wrong arguments, and no other check renders What if with a box ticked (code review of
// chunk E, round 7). Round 8 found that ticking each box alone and then all of them never reached
// the joint reason that counts a premise-argument fallen with a kind (B2: A2 and the Twelve kind,
// A4 unticked), and that a reason naming the wrong premise still passed. So:
//   - each box is ticked alone by a real click, then EVERY combination is set in one page through
//     the same change event the boxes fire;
//   - the expected list is decoded here, in Node, independently of the page's decoder;
//   - a reason is true only if every premise it names is down (ticked, or a premise-argument that
//     fell), and setting aside just those premises makes that argument fall by the table.
// Counts:
//   ticks whose "What fell" list differs from the table                     must be 0
//   ticks whose pinned "N of 45 still stand" is wrong                         must be 0
//   fallen rows with no reason, the fallback reason, or a reason that is untrue  must be 0
//   page errors                                                                must be 0
//
// Local only, like check 90: it needs Playwright from digital-comms and FAILS rather than skips.
import { createRequire } from 'module';
import { existsSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const PAGE = join(ROOT, 'outputs', 'argument-map.html');
const PW = 'C:/dev/claude/digital-comms/node_modules/playwright';
const FALLBACK = 'fell with what it rests on';   // the page's last-resort reason: valid data never reaches it
const SELF = 'is itself set aside';

// The expected answer, decoded here: fallsAll[mask] is a hex bitmask over the arguments in page order.
function expected(D, mask) {
  const bits = BigInt('0x' + (D.fallsAll[mask] || '0'));
  return D.args.filter((a, i) => (bits >> BigInt(i)) & 1n).map(a => a.id).sort();
}

// Why a row's reason is untrue, or '' if it is true. ticks: the ticked premise ids; got: the ids listed.
function untrue(row, ticks, got, D) {
  const t = (row.why || '').trim();
  if (!t) return 'no reason';
  if (t.includes(FALLBACK)) return 'the fallback reason';
  if (t === SELF) return ticks.includes(row.id) ? '' : 'says it is itself set aside, but its box is not ticked';
  // the page's three forms, each a list of premise names and nothing else
  const KIND = 'is one of a kind set aside: ', ON = 'rested on ', TOG = ', together';
  const form = t.startsWith(KIND) ? ['kind', t.slice(KIND.length), '; ']
             : t.startsWith(ON) && t.endsWith(TOG) ? ['joint', t.slice(ON.length, -TOG.length), ' and ']
             : t.startsWith(ON) ? ['alone', t.slice(ON.length), '; and on '] : null;
  if (!form) return 'is not one of the page\'s reason forms';
  // every premise, the held-fixed ones included: those are never set aside, so naming one is untrue
  const named = names(D, form[1], form[2]);
  if (!named) return 'contains text that is not a premise name';
  // the kind form claims membership; the "rested on" forms claim it is NOT a member of a kind they name
  const own = (D.args.find(a => a.id === row.id) || {}).kinds || [];
  if (form[0] === 'kind') {
    const not = named.filter(p => !own.includes(p));
    if (not.length) return 'says it is one of ' + not.join(', ') + ', which it is not';
  } else {
    const of = named.filter(p => own.includes(p));
    if (of.length) return 'says it rested on ' + of.join(', ') + ', which it is one of';
  }
  const up = named.filter(p => !D.premOrder.includes(p) || (!ticks.includes(p) && !got.includes(p)));
  if (up.length) return 'names ' + up.join(', ') + ', which is not set aside';
  const fells = ps => expected(D, ps.reduce((m, p) => m | (1 << D.premOrder.indexOf(p)), 0)).includes(row.id);
  // a joint set must fell it as a whole; otherwise each name is a reason on its own and must fell it by itself
  if (form[0] === 'joint') return named.length > 1 && fells(named) ? '' : 'names ' + named.join(' + ') + ', which together do not make it fall';
  const weak = named.filter(p => !fells([p]));
  return weak.length ? 'names ' + weak.join(', ') + ', which alone does not make it fall' : '';
}
// Read `s` as premise names joined by `sep`, longest name first at each step (a name may itself contain
// " and "). Returns the ids, or null if anything in `s` is not a whole premise name.
function names(D, s, sep) {
  const shown = D.deps.premises.flatMap(p => [[p.name, p.id], [p.name.replace(/^The /, 'the '), p.id]])
    .sort((a, b) => b[0].length - a[0].length);
  const ids = [];
  let i = 0;
  while (true) {
    const hit = shown.find(([n]) => s.startsWith(n, i));
    if (!hit) return null;
    ids.push(hit[1]); i += hit[0].length;
    if (i === s.length) return ids;
    if (!s.startsWith(sep, i)) return null;
    i += sep.length;
  }
}
function pname(D, id) { const p = (D.deps.premises || []).find(x => x.id === id); return p ? p.name : id; }

// THE detection rule, used by the real run and the selftest alike.
function judge(results, D) {
  let wrong = 0, count = 0, reasons = 0, errors = 0, partly = 0;
  const samples = [];
  for (const r of results) {
    const want = r.want.join(' '), gotIds = r.rows.map(x => x.id), got = [...gotIds].sort().join(' ');
    if (want !== got) { wrong++; samples.push(`${r.label}: page lists [${got}], table says [${want}]`); }
    if (r.standing !== r.total - r.want.length) { count++; samples.push(`${r.label}: pinned line says ${r.standing} stand, table says ${r.total - r.want.length}`); }
    for (const row of r.rows) {
      const why = untrue(row, r.ticks, gotIds, D);
      if (why) { reasons++; samples.push(`${r.label}: ${row.id} ${why} ("${row.why}")`); }
    }
    const pw = partlyWant(D, r.ticks, r.want), pg = partlyKey(r.partly || []);
    if (pw !== pg) { partly++; samples.push(`${r.label}: "only partly" list [${pg}], should be [${pw}]`); }
    errors += r.errors.length;
    r.errors.slice(0, 1).forEach(e => samples.push(`${r.label}: page error ${e}`));
  }
  console.log(`COUNT ticks ${results.length}; lists that differ from the table ${wrong} · wrong pinned counts ${count} · rows without a true reason ${reasons} · wrong "only partly" lists ${partly} · page errors ${errors}`);
  samples.slice(0, 10).forEach(s => console.log('SAMPLE ' + s));
  return results.length > 0 && !wrong && !count && !reasons && !partly && !errors;
}

// The "only partly" list a ticked kind promises (its 'partly' entry), computed here from the payload.
// One list per label, each argument once within it: "label: ids | label: ids", sorted.
function partlyWant(D, ticks, fell) {
  const out = {};
  for (const p of D.deps.premises) {
    const q = p.partly;
    if (!q || !ticks.includes(p.id)) continue;
    const L = out[q.say] || (out[q.say] = new Set());
    D.args.forEach(a => { if (!fell.includes(a.id) && a[q.field] === q.value) L.add(a.id); });
  }
  return partlyKey(Object.entries(out).map(([say, ids]) => ({ say, ids: [...ids] })));
}
const partlyKey = blocks => blocks.filter(b => b.ids.length).map(b => b.say.trim() + ': ' + [...b.ids].sort().join(' ')).sort().join(' | ');

const READ = () => ({
  partly: [...document.querySelectorAll('#fell .partly')].map(b => ({
    say: (b.querySelector('p') || {}).textContent || '',
    ids: [...b.querySelectorAll('[data-id]')].map(x => x.getAttribute('data-id')) })),
  rows: [...document.querySelectorAll('#fell .fellrow')].map(r => {
    const w = r.querySelector('.w');
    return { id: r.querySelector('[data-id]').getAttribute('data-id'), why: w ? w.textContent : '' };
  }),
  bar: (document.getElementById('standbar') || {}).textContent || '',
});
const standing = bar => { const m = /(\d+) of (\d+) still stand/.exec(bar); return m ? +m[1] : -1; };

async function measure(url) {
  const require = createRequire(import.meta.url);
  const { chromium } = require(PW);
  const browser = await chromium.launch();
  const out = [];
  let D;
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = [];
    page.on('pageerror', e => errors.push(String(e).slice(0, 160)));
    await page.goto(url + '#rests');
    D = JSON.parse(await page.$eval('#payload', s => s.textContent));
    const order = D.premOrder;
    // 1. each box alone, by a real click (the previous box unticked by a click too, not a reload)
    for (const [k, p] of order.entries()) {
      if (k) await page.uncheck(`input[data-c="${order[k - 1]}"]`);
      await page.check(`input[data-c="${p}"]`);
      const s = await page.evaluate(READ);
      out.push({ label: 'click ' + p, ticks: [p], want: expected(D, 1 << k), rows: s.rows, partly: s.partly,
                 standing: standing(s.bar), total: D.args.length, errors: errors.splice(0) });
    }
    // 2. every combination, through the change event the boxes fire
    await page.goto(url + '#rests');
    await page.reload();
    const all = await page.evaluate(([order, READ]) => {
      const read = eval(READ), res = [];
      for (let mask = 0; mask < 1 << order.length; mask++) {
        order.forEach((p, k) => {
          const cb = document.querySelector(`input[data-c="${p}"]`), want = !!(mask >> k & 1);
          if (cb.checked !== want) { cb.checked = want; cb.dispatchEvent(new Event('change', { bubbles: true })); }
        });
        res.push({ mask, ...read() });
      }
      return res;
    }, [order, '(' + READ.toString() + ')']);
    for (const s of all) {
      const ticks = order.filter((p, k) => s.mask >> k & 1);
      out.push({ label: 'set aside [' + ticks.join(', ') + ']', ticks, want: expected(D, s.mask), rows: s.rows, partly: s.partly,
                 standing: standing(s.bar), total: D.args.length, errors: errors.splice(0) });
    }
  } finally { await browser.close(); }
  return [out, D];
}

async function main() {
  if (process.argv[2] === '--selftest') {
    // a two-box fixture: r1 takes X; k1 is a kind whose member P is a premise-argument; Y falls only
    // with r1 and P together; W rests on P, so it falls with k1 without being one of it; Z never falls,
    // and k1 names it as standing only in part. Hex bit i = args[i]: X=1, P=2, Y=4, Z=8, W=16.
    const D = { premOrder: ['r1', 'k1', 'P'],
                args: [{ id: 'X' }, { id: 'P', kinds: ['k1'] }, { id: 'Y' }, { id: 'Z', s: 'part' }, { id: 'W' }],
                fallsAll: ['0', '1', '12', '17', '12', '17', '12', '17'],
                deps: { premises: [{ id: 'r1', name: 'Rule one' },
                                   { id: 'k1', name: 'Kind one', partly: { field: 's', value: 'part', say: 'Only partly:' } },
                                   { id: 'P', name: 'The method (P)' }, { id: 'F', name: 'Held fixed (F)' }] } };
    // r1 and k1 ticked: X, P, Y fall; Y's reason is the joint set, P counted through the kind
    const ok = { label: 'clean', ticks: ['r1', 'k1'], want: ['P', 'W', 'X', 'Y'], standing: 1, total: 5, errors: [],
                 partly: [{ say: 'Only partly:', ids: ['Z'] }],
                 rows: [{ id: 'X', why: 'rested on Rule one' }, { id: 'P', why: 'is one of a kind set aside: Kind one' },
                        { id: 'Y', why: 'rested on Rule one and the method (P), together' },
                        { id: 'W', why: 'rested on the method (P)' }] };
    const row = (i, why) => ({ ...ok, rows: ok.rows.map((x, k) => k === i ? { ...x, why } : x) });
    const planted = {
      'wrong list': { ...ok, rows: ok.rows.slice(0, 2), want: ok.want },
      'wrong pinned count': { ...ok, standing: 3 },
      'missing "only partly" list': { ...ok, partly: [] },
      '"only partly" under the wrong label': { ...ok, partly: [{ say: 'Something else:', ids: ['Z'] }] },
      // W falls with the kind (through P) but is not one of it; P is one of it, so "rested on" is false
      'kind form for a non-member': row(3, 'is one of a kind set aside: Kind one'),
      'rested on a kind it is one of': row(1, 'rested on Kind one'),
      'not a reason form': row(0, 'fell because of Rule one'),
      'unknown name beside a true one': row(0, 'rested on Rule one; and on rule-6'),
      'fallback reason': row(2, FALLBACK),
      'empty reason': row(2, ' '),
      'row with no reason span': row(0, ''),
      // only the kind ticked: P falls, but its reason names Rule one, which is not set aside
      'names a premise not set aside': { ...ok, ticks: ['k1'], want: ['P', 'W'], standing: 3,
                                         rows: [{ id: 'P', why: 'rested on Rule one' }, { id: 'W', why: 'rested on the method (P)' }] },
      'names the premise held fixed': row(0, 'rested on Held fixed (F); and on Rule one'),
      // X falls with r1 alone; P is down, but does not fell X: two single reasons, one of them untrue
      'two single reasons, one untrue': row(0, 'rested on Rule one; and on the method (P)'),
      'joint set that does not fell it': row(0, 'rested on Kind one and the method (P), together'),
      'names a premise that alone does not fell it': row(2, 'rested on Rule one'),
      'itself set aside, box not ticked': row(1, SELF),
      'page error': { ...ok, errors: ['TypeError: x is undefined'] },
    };
    const missed = Object.entries(planted).filter(([, r]) => judge([r], D)).map(([k]) => k);
    if (judge([], D)) missed.push('no ticks at all');
    const clean = judge([ok], D);
    console.log(`COUNT selftest faults caught ${Object.keys(planted).length + 1 - missed.length}/${Object.keys(planted).length + 1}; clean passes ${clean}` + (missed.length ? ' (missed: ' + missed.join(', ') + ')' : ''));
    process.exit(missed.length || !clean ? 0 : 1);   // exit 0 = something slipped = the runner fails this check
  }
  if (!existsSync(PW)) { console.log('COUNT ticks 0'); console.log('SAMPLE Playwright not found at ' + PW + ': this check cannot run here'); process.exit(1); }
  if (!existsSync(PAGE)) { console.log('COUNT ticks 0'); console.log('SAMPLE outputs/argument-map.html missing: check 10 must run first'); process.exit(1); }
  const [results, D] = await measure(pathToFileURL(PAGE).href);
  process.exit(judge(results, D) ? 0 : 1);
}
// A crash must never read as a detection: print the stack (the runner recognizes it as a crash) and
// exit 126, which the runner treats as a crash in either mode.
main().catch(e => { console.log('COUNT ticks 0'); console.log(String(e && e.stack || e)); process.exit(126); });
