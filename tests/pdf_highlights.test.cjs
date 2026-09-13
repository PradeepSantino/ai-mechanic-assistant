const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('docker/pdf_highlights.js', 'utf8');
function setup() {
  const timers = [];
  let spans = [];
  const layer = {querySelectorAll: () => spans, getAttribute: () => '0'};
  const context = {
    document: {querySelector: () => ({contentDocument: {querySelector: () => layer}})},
    setTimeout: fn => timers.push(fn),
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  return {context, timers, set: texts => {
    spans = texts.map(textContent => ({textContent, children: [], style: {}}));
    return spans;
  }};
}
test('waits for target text layer and matches across spans', () => {
  const x = setup();
  x.context.compareText(['Torque: 21 N*m for bolt A'], 10);
  assert.equal(x.timers.length, 1);
  const spans = x.set(['Torque: 21 N*m ', 'for bolt A']);
  x.timers.shift()();
  assert.ok(spans.every(s => s.style.backgroundColor));
});
test('matches two values without highlighting a different value', () => {
  const x = setup();
  const spans = x.set(['21 N*m for bolt A', '52 N*m for bolt B', '64 N*m for bolt C']);
  x.context.compareText(['21 N*m for bolt A', '52 N*m for bolt B'], 10);
  assert.ok(spans[0].style.backgroundColor);
  assert.ok(spans[1].style.backgroundColor);
  assert.equal(spans[2].style.backgroundColor, '');
});
test('old work is cancelled on citation switch', () => {
  const x = setup();
  x.context.compareText(['21 N*m for bolt A'], 10);
  vm.runInContext('highlightGeneration++', x.context);
  const spans = x.set(['21 N*m for bolt A']);
  x.timers.shift()();
  assert.equal(spans[0].style.backgroundColor, undefined);
});
test('missing text stops retrying within a fixed limit', () => {
  const x = setup();
  x.context.compareText(['21 N*m for bolt A'], 10);
  let calls = 0;
  while (x.timers.length && calls < 110) { x.timers.shift()(); calls++; }
  assert.equal(calls, 100);
  assert.equal(x.timers.length, 0);
});
