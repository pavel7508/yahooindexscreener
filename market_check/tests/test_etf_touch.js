// Run: node market_check/tests/test_etf_touch.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const html = fs.readFileSync(path.join(__dirname, "../components/watch_table/index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const listeners = {};
const sent = [];
const windowListeners = {};
let htmlWrites = 0;
let retryReady;
let cleared = false;
const scroller = {scrollLeft: 0, scrollTop: 0};
class Element {
  constructor() { this.dataset = {open: "XLK"}; this.disabled = false; }
  closest(selector) { return selector === ".market-table-scroll" ? scroller : this; }
  hasAttribute(name) { return name === "data-open"; }
}
const button = new Element();
const root = {
  addEventListener: (type, fn) => {listeners[type] = fn;}, contains: () => true,
  getBoundingClientRect: () => ({height: 100}),
  set innerHTML(value) {htmlWrites++;},
};
const context = {
  Element, document: {getElementById: () => root},
  window: {parent: {postMessage: value => sent.push(value)}, addEventListener(type, fn) {windowListeners[type] = fn;}, matchMedia: () => ({matches: false})},
  ResizeObserver: class {observe() {}}, MutationObserver: class {}, setTimeout, clearTimeout, setInterval: fn => {retryReady = fn; return 1;}, clearInterval() {cleared = true;},
};
vm.runInNewContext(script, context);
retryReady();
assert.equal(sent.filter(m => m.type === "streamlit:componentReady").length, 2);
const render = {source: context.window.parent, data: {type: "streamlit:render", args: {html: "table"}}};
windowListeners.message(render);
windowListeners.message(render);
assert.equal(cleared, true); // Stop handshake retries after a render acknowledgement.
assert.equal(htmlWrites, 1); // Disabled/theme renders must preserve the active touch target.
const point = (x, y) => ({clientX: x, clientY: y});
const start = () => listeners.touchstart({target: button, touches: [point(20, 20)]});
const end = () => listeners.touchend({target: button, touches: [], changedTouches: [point(20,20)], preventDefault() {}});
const values = () => sent.filter(message => message.type === "streamlit:setComponentValue").map(message => message.value);
start(); end();
assert.equal(values().length, 1);
assert.equal(values()[0].ticker, "XLK");
assert.equal(values()[0].mobile, true);
assert.equal(button.disabled, false);
listeners.click({target: button, detail: 1, preventDefault() {}});
assert.equal(values().length, 1); // Safari compatibility click must not duplicate the tap.
listeners.click({target: button, detail: 0});
assert.equal(values().length, 2); // Keyboard activation still works.
start();
listeners.touchmove({touches: [point(60,20)]});
end();
assert.equal(values().length, 2); // A swipe is not a tap.
start(); scroller.scrollLeft = 50; end();
assert.equal(values().length, 2); // Native scrolling must not open an ETF.
start(); listeners.touchcancel(); end();
assert.equal(values().length, 2);
console.log("OK: handshake retry, stable DOM, single mobile tap, click deduplication, keyboard, swipe, scroll and cancel");
