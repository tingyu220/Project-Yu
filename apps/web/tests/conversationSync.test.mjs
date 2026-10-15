import test from "node:test";
import assert from "node:assert/strict";
import { mergeTurns, pollDelay } from "../src/lib/conversationSync.ts";

test("later revision replaces pending turn without duplicate", () => {
  const first = {seq: 1, revision: 1, state: "queued"};
  const done = {...first, revision: 2, state: "completed"};
  assert.deepEqual(mergeTurns([first], [done, done]), [done]);
});

test("background polling is slower", () => {
  assert.equal(pollDelay(false), 1000);
  assert.equal(pollDelay(true), 5000);
});
