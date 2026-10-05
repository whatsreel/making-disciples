// Render every view and every argument sheet of the built page in a minimal DOM shim.
// No browser: this is what smoke_hub.js and the gate's text checks read.
//
//   node render_views.js <page.html>        prints {"tabs","views":{id:html},"sheets":{id:html}}
//   require('./render_views').render(path)  returns the same object
//
// Views are discovered, not listed: every element the page script asks for whose id starts
// with "v-" is a view. So adding or removing a tab needs no edit here (counts are computed).
const fs = require('fs');

function render(pagePath) {
  const h = fs.readFileSync(pagePath, 'utf8');
  const pm = h.match(/<script id="payload"[^>]*>([\s\S]*?)<\/script>/);
  const jm = h.match(/<script>\n([\s\S]*)<\/script>/);
  if (!pm || !jm) throw new Error('page has no payload or no inline script: ' + pagePath);
  const payload = pm[1].split('<\\/script>').join('</script>');

  const els = {};
  const handlers = {};
  // Views are the static <div id="v-..."> elements; asking for any other v- id gets null,
  // as in a browser (the page uses that to validate a #view in the URL).
  const staticViews = new Set([...h.matchAll(/<div class="view" id="(v-[a-z]+)"/g)].map(m => m[1]));
  function el(id) {
    if (/^v-/.test(id) && !staticViews.has(id)) return null;
    return els[id] || (els[id] = {
      id, innerHTML: '', textContent: '', value: '', scrollTop: 0, open: false,
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      setAttribute() {}, getAttribute() { return null; },
      scrollIntoView() {}, querySelectorAll() { return []; }, querySelector() { return null; },
      onclick: null, oninput: null, onchange: null, addEventListener() {}, style: {},
    });
  }
  const doc = {
    getElementById: el,
    addEventListener(type, fn) { (handlers[type] = handlers[type] || []).push(fn); },
    querySelectorAll() { return []; }, querySelector() { return null; },
    createTreeWalker() { return { nextNode() { return null; } }; },
    body: { classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } }, setAttribute() {} },
  };
  const g = { document: doc, window: { scrollTo() {}, addEventListener() {} }, NodeFilter: { SHOW_TEXT: 4, FILTER_ACCEPT: 1, FILTER_REJECT: 2 }, location: { href: 'file:///local', hash: '' } };
  el('payload').textContent = payload;
  new Function('document', 'window', 'NodeFilter', 'location', jm[1])(g.document, g.window, g.NodeFilter, g.location);

  const views = {};
  Object.keys(els).filter(k => /^v-/.test(k)).forEach(k => { views[k] = els[k].innerHTML; });

  // open every argument sheet through the page's own click handler
  const ids = JSON.parse(payload).args.map(a => a.id);
  const sheets = {};
  ids.forEach(id => {
    const target = { id: '', tagName: 'BUTTON',
      closest(sel) { return sel === '[data-id]' ? { tagName: 'BUTTON', getAttribute: () => id } : null; } };
    (handlers.click || []).forEach(fn => fn({ target, preventDefault() {} }));
    sheets[id] = el('detailInner').innerHTML;
  });
  // lists drawn into a child element of a view (the arguments list is redrawn on search)
  const lists = { argslist: (els.argslist || { innerHTML: '' }).innerHTML };
  return { tabs: el('tabs').innerHTML, views, sheets, lists, foot: el('foot').innerHTML };
}

// visible text of an HTML fragment: tags and their attributes removed, common entities decoded
function text(html) {
  return String(html).replace(/<style[\s\S]*?<\/style>/g, ' ').replace(/<[^>]*>/g, ' ')
    .replace(/&middot;/g, '·').replace(/&mdash;/g, '—').replace(/&nbsp;/g, ' ')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&')
    .replace(/[ \t]+/g, ' ');
}

module.exports = { render, text };

if (require.main === module) {
  const p = process.argv[2];
  if (!p) { console.error('usage: node render_views.js <page.html>'); process.exit(2); }
  process.stdout.write(JSON.stringify(render(p)));
}
