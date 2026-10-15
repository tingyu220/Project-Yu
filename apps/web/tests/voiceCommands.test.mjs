import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const scope = {exports: {}};
vm.runInNewContext(ts.transpileModule(readFileSync(new URL('../src/lib/voiceCommands.ts', import.meta.url), 'utf8'),
  {compilerOptions: {module: ts.ModuleKind.CommonJS}}).outputText, scope);
for (const text of ['OK，结束。', '结束语音', '好的，停止监听！', '结束']) assert.equal(scope.exports.isVoiceStopCommand(text), true);
for (const text of ['结束会议后去西湖', '帮我结束任务', '结束了吗']) assert.equal(scope.exports.isVoiceStopCommand(text), false);
console.log('Voice stop commands passed');
