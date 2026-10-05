// Render every view of the hub in a minimal DOM shim; fail loudly on runtime errors.
// Views are discovered by render_views.js, so the count below is computed, never typed.
const path = require('path');
const { render } = require(path.join(__dirname, 'render_views.js'));
const page = (process.env.OUT || '/mnt/user-data/outputs') + '/argument-hub.html';

try {
  const r = render(page);
  const names = Object.keys(r.views);
  const lens = {};
  names.forEach(k => { lens[k] = r.views[k].length; });
  console.log('rendered chars per view:', JSON.stringify(lens));
  const empty = names.filter(k => lens[k] < 200);
  console.log(empty.length ? 'EMPTY VIEWS: ' + empty.join(', ') : 'all ' + names.length + ' views rendered');
  const thinSheets = Object.keys(r.sheets).filter(k => r.sheets[k].length < 200);
  console.log(thinSheets.length ? 'EMPTY SHEETS: ' + thinSheets.join(', ') : 'all ' + Object.keys(r.sheets).length + ' argument sheets rendered');
  // the summary must name all three changes, the read-three and the limit
  const s = r.views['v-brief'] || '';
  const miss = ['Mission', 'Prayer', 'Equipping', 'data-id="C4"', 'data-id="C17"', 'data-id="C16"', 'What this does not show']
    .filter(t => !s.includes(t));
  // Start's big buttons (the golist only: the "How this page works" text link under them is not one of them),
  // and every control on Start, buttons or link, opens a view that exists
  const vs = r.views['v-start'] || '';
  const gl = (vs.match(/<div class="golist">([\s\S]*?)<\/div>/) || ['', ''])[1];
  const goes = [...gl.matchAll(/data-go="([a-z]+)"/g)].map(m => m[1]);
  const all = [...vs.matchAll(/data-go="([a-z]+)"/g)].map(m => m[1]);
  console.log('start buttons: ' + goes.length + ' (' + goes.join(', ') + '); other start links: ' + (all.length - goes.length));
  if (goes.length < 5) miss.push('Start has fewer than five buttons');
  all.filter(g => !r.views['v-' + g]).forEach(g => miss.push('Start control opens a missing view: ' + g));
  // The positions tab lists every position
  const rows = ((r.lists && r.lists.argslist) || '').match(/<details class="rd" data-v=/g) || [];
  console.log('arguments listed: ' + rows.length + ' of ' + Object.keys(r.sheets).length);
  if (rows.length !== Object.keys(r.sheets).length) miss.push('The positions tab does not list every position');
  // Sources and method carries the byline and the sources; the common questions live in In brief
  // (moved on Jon's comment "this doesn't belong in this tab", the evening of 2026-10-04)
  const src = r.views['v-source'] || '';
  ['By ', 'Sources cited', 'How Scripture is read here'].filter(t => !src.includes(t)).forEach(t => miss.push('Sources and method lacks: ' + t));
  if (src.includes('Common questions')) miss.push('Sources and method still carries the common questions');
  if (!(r.views['v-brief'] || '').includes('Common questions')) miss.push('In brief lacks: Common questions');
  miss.forEach(t => console.log('MISS ' + t));
  const acc = (r.views['v-board'] || '').includes('<details class="col2"');
  if (!acc) console.log('MISS board accordion for mobile');
  process.exit(empty.length || thinSheets.length || miss.length || !acc ? 1 : 0);
} catch (e) {
  console.log('RUNTIME ERROR:', String(e.stack || e).split('\n').slice(0, 4).join(' | '));
  process.exit(1);
}
