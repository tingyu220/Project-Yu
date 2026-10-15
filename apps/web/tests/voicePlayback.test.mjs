import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import ts from 'typescript';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

const source = readFileSync(new URL('../src/components/SpeakButton.tsx', import.meta.url), 'utf8');
const scope = {exports: {}, require: createRequire(import.meta.url)};
vm.runInNewContext(ts.transpileModule(source, {compilerOptions: {
  module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX,
}}).outputText, scope);
const markup = renderToStaticMarkup(createElement(scope.exports.default, {text: '下一首', disabled: true}));
assert.match(markup, /<button[^>]+disabled/);
const idle = renderToStaticMarkup(createElement(scope.exports.default, {text: '你好'}));
assert.doesNotMatch(idle, /<button[^>]+disabled/);
console.log('Playback: live voice disables assistant speech to prevent self-triggering');
