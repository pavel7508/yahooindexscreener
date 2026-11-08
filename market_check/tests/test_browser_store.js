// Run with: node market_check/tests/test_browser_store.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const html = fs.readFileSync(path.join(__dirname, "../components/browser_store/index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
function browser(initial, blocked = false) {
  let saved = initial;
  let render;
  const messages = [];
  const parent = {postMessage: value => messages.push(value)};
  const context = {
    window: {parent, addEventListener: (_, fn) => { render = fn; }},
    localStorage: {
      getItem() { if (blocked) throw Error("blocked"); return saved; },
      setItem(_, value) { if (blocked) throw Error("blocked"); saved = value; },
    },
  };
  vm.runInNewContext(script, context);
  return {
    render(items) { render({source: parent, data: {type: "streamlit:render", args: {items}}}); },
    values() { return messages.filter(m => m.type === "streamlit:setComponentValue").map(m => m.value); },
    saved() { return saved; },
  };
}
const first = browser('["AAPL"]');
first.render(null);
assert.equal(JSON.stringify(first.values()[0].items), '["AAPL"]');
assert.equal(first.saved(), '["AAPL"]'); // Initialization must never overwrite storage.
first.render(["AAPL", "BRK.B"]);
assert.equal(first.saved(), '["AAPL","BRK.B"]');
const count = first.values().length;
first.render(["AAPL", "BRK.B"]);
assert.equal(first.values().length, count); // No infinite rerun loop.
const reopened = browser(first.saved());
reopened.render(null);
assert.equal(JSON.stringify(reopened.values()[0].items), '["AAPL","BRK.B"]');
reopened.render([]);
assert.equal(reopened.saved(), '[]');
const blocked = browser(null, true);
blocked.render(null);
assert.ok(blocked.values()[0].error);
blocked.render(["AAPL"]);
assert.ok(blocked.values().at(-1).error);
const corrupt = browser('{broken');
corrupt.render(null);
assert.ok(corrupt.values()[0].error);
console.log("OK: browser restore, save, removal, blocked/corrupt storage and rerun loop protection");
