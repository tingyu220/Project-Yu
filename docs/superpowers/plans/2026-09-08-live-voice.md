# 余音持续实时语音 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 开启一次后实时接收语音、句尾自动执行、继续监听，停止后释放麦克风且不执行剩余识别结果。

**Architecture:** 浏览器 AudioWorklet 输出单声道 16 kHz PCM，经本机 WebSocket 转发到北京地域 Qwen 实时 ASR。只将最终识别结果串行送入原有聊天及安全动作链；中间字幕绝不执行。会话归 Cockpit 持有，不随 Composer 布局切换销毁。

**Tech Stack:** React / TypeScript、AudioWorklet、FastAPI、websockets、Qwen3-ASR-Flash-Realtime。

**Spec:** 本任务中用户已批准的持续语音交互方案（2026-09-08）。

## Global Constraints

- 中国大陆优先，默认北京；不跨地域自动重试，不向浏览器泄露 Key，不保存录音。
- 不包含浏览器关闭后的常驻唤醒；危险动作仍按现有权限拒绝或确认。
- 不自动重放断线前命令；限制队列、帧大小和会话时长；提供明确错误及结束入口。
- 保留现有未提交修改；未获得确认不提交、不推送。
- SQLite 操作留在创建连接的线程；耗时网络与系统执行不能堵塞实时收音。

### Task 1: 实时 ASR 边界

Files: `src/yu/voice/realtime.py`、`src/yu/api/voice_live.py`、`src/yu/api/voice.py`、`tests/test_voice_live.py`、`pyproject.toml`。

Interfaces: `normalize_event(event: dict) -> dict | None` 返回 ready/partial/final/speech/error；`relay(websocket, provider)` 转发 PCM 并清理双向任务。

- [x] 先写测试：部分识别 text+stash 只作字幕，completed 才 final；未知事件忽略，原始错误不得泄漏；跨站连接拒绝。
- [x] 运行 `.venv/Scripts/python.exe -m pytest tests/test_voice_live.py`，确认缺少实时能力导致失败。
- [x] 实现 provider 会话配置及双向转发；连接、帧格式、过载、断线均稳定失败，结束丢弃在途句子。
- [x] 运行新旧语音测试，检查协议配置与本机 WebSocket 生命周期。

### Task 2: 持续接收和串行执行

Files: `apps/web/src/lib/liveVoiceSession.ts`、`useLiveVoice.ts`、`liveVoiceQueue.ts`、`apps/web/public/voice-capture.js`、`useConversation.ts`、`apps/web/tests/liveVoice.test.mjs`。

Interfaces: 会话 `start()/stop()`；队列 `add(id,text)/clear()`；`submit(text)` 返回 Promise，禁止忙时静默丢弃。

- [x] 测试连续两句按顺序执行、相同 item_id 不重复、清空后不执行待处理句、PCM 分块和幅值编码。
- [x] 运行 Node 测试确认失败，然后实现稳定会话和清理逻辑。
- [x] 配置完成才启动音频转发；结束/拒绝授权/失联释放资源；不自动重连。

### Task 3: 非阻塞执行与界面接入

Files: `src/yu/api/app.py`、`src/yu/actions/service.py`、`apps/web/src/pages/Cockpit.tsx`、`Composer.tsx`、`ConversationPanel.tsx`、`apps/web/vite.config.ts`。

- [x] 增加慢执行时事件循环仍可工作的回归测试，保留权限与审计断言。
- [x] 仅将耗时 I/O 移出事件循环；SQLite 不跨线程。
- [x] 采用现有黑金视觉：开始/结束语音、连接中/持续监听/断连反馈、实时字幕；窄屏换行，不添加无关视觉重构。
- [ ] 执行完整 pytest、Node 测试、npm build，检查桌面和窄屏、首句切换后会话保留。

### Task 4: 交付与真人验证

Files: `start-voice.ps1`、`docs/voice-china.md`、`DEV_STATUS.md`。

- [x] 启动检查新增依赖，更新持续发送音频和费用隐私说明。
- [x] 模拟服务验证 ready/partial/final、多句、退出、重复、断连，不调用付费云服务或真实动作。
- [ ] 用户本机配置 Key 后，验收真实麦克风“打开QQ音乐并播放→下一首→暂停”。未经真实验证不称完整目标完成。

验证备注：构建、后端全量测试及 Node 模拟测试通过；已检查默认页面和首句后的页面入口、390px DOM 无横向溢出。浏览器截图本次不可用；完整实时监听 UI 仍需真人麦克风验收，因此 Task 3 最后一项暂不勾选。
