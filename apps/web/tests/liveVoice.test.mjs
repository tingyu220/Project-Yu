import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source = readFileSync(new URL('../src/lib/liveVoiceQueue.ts', import.meta.url), 'utf8');
const sandbox = { exports: {} };
vm.runInNewContext(ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS}}).outputText, sandbox);
const { LiveVoiceQueue } = sandbox.exports;
const called = [];
let resolve;
const queue = new LiveVoiceQueue(async text => { called.push(text); await new Promise(r => resolve = r); });
assert.equal(queue.add('1', '下一首'), true);
assert.equal(queue.add('1', '下一首'), false);
assert.equal(queue.add('2', '暂停'), true);
assert.deepEqual(called, ['下一首']);
resolve();
await new Promise(r => setTimeout(r, 0));
assert.deepEqual(called, ['下一首', '暂停']);
queue.add('3', '播放');
queue.clear();
resolve();
await new Promise(r => setTimeout(r, 0));
assert.deepEqual(called, ['下一首', '暂停']);
assert.equal(queue.add('4', '播放'), false);
console.log('Live queue: sequential execution, duplicate rejection, stop cleanup passed');

let Processor;
vm.runInNewContext(readFileSync(new URL('../public/voice-capture.js', import.meta.url), 'utf8'), {
  AudioWorkletProcessor: class { constructor() { this.port = {postMessage: frame => frames.push(frame)}; } },
  registerProcessor: (_name, value) => Processor = value, sampleRate: 16000,
});
const frames = [];
const processor = new Processor();
processor.process([[new Float32Array(800).fill(1)]]);
assert.equal(frames.length, 0);
processor.process([[new Float32Array(800).fill(-1)]]);
assert.equal(frames[0].byteLength, 3200);
assert.equal(new DataView(frames[0]).getInt16(0, true), 32767);
assert.equal(new DataView(frames[0]).getInt16(1600, true), -32768);
console.log('PCM capture: 100ms framing and signed little-endian encoding passed');
