import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import ts from 'typescript';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

const require = createRequire(import.meta.url);
let response;
const scope = {exports: {}, window: {setTimeout() {}}, require: name => name === './api'
  ? {api: {chat: async () => response}} : require(name)};
vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/lib/useConversation.ts', import.meta.url), 'utf8'),
  {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}}).outputText, scope);
let conversation;
function Harness() { conversation = scope.exports.useConversation(true); return null; }
for (const value of [
  {kind: 'action', allowed: false, reply: '执行失败', retrieved: []},
  {kind: 'error', allowed: true, reply: '模型失败', retrieved: []},
  {kind: 'chat', allowed: true, reply: '记忆保存失败', retrieved: [], memory_result: {success: false}},
]) {
  response = value;
  renderToStaticMarkup(createElement(Harness));
  await assert.rejects(conversation.submit('测试'), {message: value.reply});
}
response = {kind: 'action', allowed: true, reply: '已播放', retrieved: []};
renderToStaticMarkup(createElement(Harness));
await conversation.submit('播放');
console.log('Conversation: business failures reject queue submission; success permits next command');
