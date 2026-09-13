// Wait for the requested page, never whichever page happens to render first.
let highlightGeneration = 0;
globalThis.compareText = (phrases, page, generation = highlightGeneration, attempt = 0) => {
  if (generation !== highlightGeneration) return;
  const frame = document.querySelector('#pdf-viewer');
  const doc = frame && frame.contentDocument;
  const layer = doc && doc.querySelector(`#viewer .page[data-page-number='${Number(page)}'] .textLayer`);
  const spans = layer ? Array.from(layer.querySelectorAll('span')).filter(s => !s.children.length) : [];
  if (!spans.length || layer.getAttribute('data-main-rotation') === null && !layer.textContent.trim()) {
    if (attempt < 100) setTimeout(() => compareText(phrases, page, generation, attempt + 1), 200);
    return;
  }
  // Match entire normalized quotations across PDF text spans, preserving offsets.
  // Do not fuzzy-match generic units against unrelated torque values.
  const normalize = text => text.normalize('NFKC').toLowerCase().replace(/[^a-z0-9]/g, '');
  let text = '';
  const ranges = spans.map(span => {
    span.style.backgroundColor = '';
    const start = text.length;
    text += normalize(span.textContent);
    return {span, start, end: text.length};
  });
  let found = 0;
  for (const phrase of phrases) {
    const needle = normalize(phrase.replace(/【\d+】/g, ''));
    if (needle.length < 12) continue;
    const start = text.indexOf(needle);
    if (start < 0) continue;
    found++;
    for (const range of ranges) {
      if (range.start < start + needle.length && range.end > start) {
        range.span.style.backgroundColor = 'rgba(40, 200, 80, 0.65)';
      }
    }
  }
  // Text layers may be populated incrementally after the first span appears.
  if (found < phrases.length && attempt < 100) {
    setTimeout(() => compareText(phrases, page, generation, attempt + 1), 200);
  }
};
