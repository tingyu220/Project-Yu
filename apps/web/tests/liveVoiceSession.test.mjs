import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const contexts = [], sockets = [], nodes = [];
let grant;
let stops = 0;
const events = [], errors = [];
class Context {
  sampleRate = 16000; state = 'running'; destination = {};
  audioWorklet = {addModule: async () => {}};
  constructor() { contexts.push(this); }
  async resume() {}
  async close() { this.state = 'closed'; }
  createMediaStreamSource() { return {connect() {}}; }
}
class Socket {
  static OPEN = 1; readyState = 1; bufferedAmount = 0; sent = [];
  constructor() { sockets.push(this); }
  send(data) { this.sent.push(data); }
  close() { this.closed = true; }
}
class Node {
  port = {close() {}};
  constructor() { nodes.push(this); }
  connect() {}
  disconnect() { this.disconnected = true; }
}
const track = {stop() { stops++; }, addEventListener() {}};
const stream = {getTracks: () => [track], getAudioTracks: () => [track]};
const scope = {exports: {}, AudioContext: Context, AudioWorkletNode: Node, WebSocket: Socket,
  navigator: {mediaDevices: {getUserMedia: () => new Promise(r => grant = r)}},
  location: {protocol: 'http:', host: 'localhost:8792'}, setTimeout, clearTimeout};
const source = readFileSync(new URL('../src/lib/liveVoiceSession.ts', import.meta.url), 'utf8');
vm.runInNewContext(ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}}).outputText, scope);
const {LiveVoiceSession} = scope.exports;

// 授权窗口迟到返回，也不能重新打开麦克风。
const cancelled = new LiveVoiceSession(e => events.push(e), e => errors.push(e));
const waiting = cancelled.start();
await new Promise(r => setTimeout(r, 0));
cancelled.stop(); grant(stream); await waiting;
assert.equal(stops, 1);
assert.equal(contexts[0].state, 'closed');
assert.equal(sockets.length, 0);

const session = new LiveVoiceSession(e => events.push(e), e => errors.push(e));
const opening = session.start();
await new Promise(r => setTimeout(r, 0)); grant(stream); await opening;
assert.equal(nodes.length, 0);
const socket = sockets[0];
socket.onmessage({data: JSON.stringify({type: 'ready'})});
assert.equal(nodes.length, 1);
nodes[0].port.onmessage({data: new ArrayBuffer(3200)});
assert.equal(socket.sent.length, 1);
socket.onmessage({data: JSON.stringify({type: 'final', id: 'a', text: '下一首'})});
socket.onmessage({data: JSON.stringify({type: 'final', id: 'b', text: '暂停'})});
assert.equal(events.filter(e => e.type === 'final').length, 2);
assert.equal(socket.closed, undefined);
session.stop();
assert.equal(socket.closed, true);
assert.equal(stops, 2);
assert.equal(contexts[1].state, 'closed');
assert.equal(socket.onmessage, null);
assert.equal(errors.length, 0);
console.log('Live session: late permission cleanup, ready gating, consecutive finals and release passed');
