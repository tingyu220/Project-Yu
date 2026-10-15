import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source = readFileSync(new URL('../src/lib/speechEndpoint.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const sandbox = { exports: {} };
vm.runInNewContext(compiled, sandbox);
const { SpeechEndpoint } = sandbox.exports;

// 纯静音和短促噪音不发送。
const silent = new SpeechEndpoint();
assert.equal(silent.feed(0, 8000), 'empty');
const noise = new SpeechEndpoint();
assert.equal(noise.feed(0.03, 40), 'listen');
assert.equal(noise.feed(0, 8000), 'empty');

// 说话期间和短停顿继续听，句尾静音一秒才发送。
const spoken = new SpeechEndpoint();
assert.equal(spoken.feed(0.04, 200), 'listen');
assert.equal(spoken.feed(0, 600), 'listen');
assert.equal(spoken.feed(0.04, 200), 'listen');
assert.equal(spoken.feed(0, 1000), 'submit');
console.log('Speech endpoint: 3 scenarios passed');
