# 共享会话与语音控制实施计划

> **执行代理要求：** 使用 superpowers:executing-plans（当前会话执行，推荐）或 superpowers:subagent-driven-development 逐任务实施；以下复选框记录进展。

**Goal：** 网页与本地语音共享持久会话，并能可靠展示状态、结束对话和中断朗读。

**Architecture：** 后端是唯一上下文所有者，SQLite 轮次记录提供持久历史和幂等回执，单会话工作队列统一调用既有路由。客户端只负责输入和展示，语音运行时保留单采集流与受管播放进程。先完成共享会话，再调整语音行为；不大规模重构原路由。

**Tech Stack：** Python 3.12、SQLite 标准库、FastAPI、asyncio、React/TypeScript、System.Speech、sounddevice、现有北京实时 ASR。

**Spec：** docs/superpowers/specs/2026-10-09-shared-conversation-design.md（已批准）。

## 全局约束

- 实际仓库 D:/田雨/Yu；保留全部用户未提交修改，未经确认不 Commit/Push。
- 所有终端命令使用动态解析的 PowerShell 7；编辑使用 apply_patch，中文注释和工作记录。
- 迁移前用 sqlite3.Connection.backup 备份实际 YU_DB_PATH；不删除、改写原记忆表；测试仅使用临时数据库。
- 本轮一个默认持久会话、最多 3 条等待消息、模型最近 20 条已完成消息、增量每页最多 100 轮。
- 网页轮询前台 1 秒、后台 5 秒；监听心跳超过 5 秒未知；音频超过 2 秒过期。
- 不保存录音，不向普通诊断日志写聊天正文；不新增云服务、声纹、手机或 EXE。
- 未经真人验证只称部分完成；实施不自动启动真实麦克风或收费连接。

## 文件职责

- 新 src/yu/conversation/models.py、store.py、service.py：精确轮次类型、持久存储、队列与上下文。
- 新 src/yu/api/conversation.py：查询共享会话/回执的薄路由；原 app.py 仅调整聊天入口和组装。
- 修改 api/context.py、schemas.py：生命周期与共享请求字段。
- 新 apps/web/src/lib/conversationSync.ts：增量游标与编号归并；原 useConversation.ts 不再拥有权威历史。
- 新 src/yu/voice/wake/control.py、api/voice_control.py：状态、心跳、控制鉴权与运行时命令通道。
- 修改 wake/session.py、runtime.py、capture.py、feedback.py、detector.py、native-wake.ps1：共享提交、单请求门控、帧时效、受管播放和本地控制语法。
- 修改网页 api.ts、types.ts、useLiveVoice.ts、Composer.tsx：共享数据与状态展示，不重新设计界面。

## 审查重点

1. 回执查询后再次请求同一编号不得再次打开应用；内容冲突须返回 409（任务 2/3）。
2. 轮次由 queued 改为 completed 时，不能因创建序号未变化而漏同步（任务 1/4）。
3. 省略记忆引用与显式空引用须区分；旧 history 中 system 文本不能控制后端（任务 3）。
4. 其他网站伪造停止请求、旧令牌和无心跳状态不得被当作合法控制（任务 5）。
5. 停止朗读必须终止真实播放进程，不只取消协程；背景音不能在控制期间成为普通动作（任务 6/7）。

## 任务 1：持久轮次和迁移

Files：新 conversation/models.py、store.py；新 tests/test_conversation_store.py。

Interfaces：Turn 含 seq、session_id、request_id、source、message、state、created_at、completed_at、result、revision；ConversationStore(db_path: str)，default_session() -> str，get_request(session_id: str, request_id: str) -> Turn | None，insert_turn(session_id, request_id, source, message) -> Turn，set_state(seq: int, state: str, result: dict | None = None) -> Turn，changes(after: int, limit: int = 100) -> dict，history(session_id: str) -> list[dict[str,str]]，references(session_id: str) -> list[int]，close() -> None。

revision 为每次轮次插入/更新单调递增的同步游标；seq 仅排序。changes 按 revision 返回最新轮次和 next_cursor，客户端按 seq 归并；queued→completed 必须生成新 revision。分页 limit 校验 1..100。

- [ ] 写测试 test_restart_keeps_completed_history、test_running_becomes_unknown_without_replay、test_updates_advance_cursor、test_backup_preserves_existing_memories：重开临时库后默认编号相同，历史是字面 user/assistant 对；未完成轮次 unknown；同一 seq 更新后能被新游标读取；备份仍含原 memories 内容。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_conversation_store.py -v`，确认因行为缺失失败。
- [ ] 实现新增表、唯一约束、迁移前唯一命名备份与逐次 revision；数据库操作不跨 await。恢复 unknown 只在服务启动执行一次。
- [ ] 同一命令通过；验证 history 最多 20 条、failed/unknown 不入历史、completed 业务失败保留真实失败结果。
- [ ] 记录完成证据，不自动提交。

## 任务 2：后端统一执行队列

Files：新 conversation/service.py；新 tests/test_conversation_service.py。

Interfaces：ConversationService(store: ConversationStore, handler: Callable[[str, list[dict], list[int]], Awaitable[dict]])；async submit(session_id: str, request_id: str, source: str, message: str, references: list[int] | None = None) -> dict；async close() -> None。产出原业务回复加 session_id、request_id、seq、state。SessionConflict、QueueCapacityError 为独立异常。

- [ ] 写 test_duplicate_request_executes_once（handler 执行次数 1）、test_conflicting_payload_rejected、test_fourth_waiter_rejected（1 条正在处理 + 3 等待，第 4 等待不入库）、test_second_turn_reads_first_result（第二 handler 收到第一轮真实回复）、test_client_cancel_does_not_cancel_accepted_work。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_conversation_service.py -v`，确认 RED。
- [ ] 用一个后台 worker、asyncio.Queue(maxsize=3)、受 shield 保护的等待结果；去重和入队容量判断无 await 间隙。重复编号包含 session/source/message/显式引用内容校验。业务回复完整保存，异常标记 failed；关闭不重放队列，未确认结果标 unknown。
- [ ] 同命令 GREEN，且超时回执查询不触发 handler。
- [ ] 记录完成证据，不自动提交。

## 任务 3：接入 API 与已有路由

Files：新 api/conversation.py；修改 api/app.py、context.py、schemas.py；新 tests/test_conversation_api.py；保留原动作/记忆测试。

Interfaces：保留 POST /api/chat 原业务字段，增加 session_id/request_id/source；references 缺省为 None，显式 [] 不恢复旧引用。GET /api/conversation -> {session_id}；GET /api/conversation/turns?after=N -> {turns,next_cursor,has_more}；GET /api/conversation/requests/{request_id} -> 完整轮次，缺失 404。队列满 429、内容冲突 409、非法默认会话 404。

- [ ] 写 test_web_and_voice_share_history、test_client_system_history_ignored、test_reference_omitted_vs_empty、test_receipt_lookup_never_reexecutes、test_conflict_http_409；通过临时 AppContext 注入确定性 provider，断言模型收到的 user/assistant 内容及动作执行次数，不调真实服务。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_conversation_api.py -v` 确认 RED。
- [ ] 提取原 chat 的路由决策为 handler，由 ConversationService 调用；不重写业务功能。lifespan 负责 worker/store 回收；SQLite 原连接仍在正确线程使用，不为方便开启不受控跨线程写入。
- [ ] 同命令 GREEN；运行 `.venv/Scripts/python.exe -m pytest tests/test_action_api.py tests/test_memory_api.py tests/test_api.py -v`，明确报告任何旧测试契约变化。
- [ ] 记录完成证据，不自动提交。

## 任务 4：网页与本地语音共享客户端

Files：修改 wake/session.py、网页 api.ts、types.ts、useConversation.ts；新 conversationSync.ts、tests/test_shared_voice_client.py、apps/web/tests/conversationSync.test.mjs。

Interfaces：网页 api.conversation()、api.conversationChanges(after: number, signal?: AbortSignal)、api.chat(message, session_id, request_id, source)、api.receipt(request_id)。sync.mergeTurns(existing: Turn[], incoming: Turn[]) -> Turn[]；pollDelay(hidden: boolean) -> 1000 | 5000。VoiceSession 获取默认编号，submit 不再发送 self.history；超时查询原编号，不自动重发。

- [ ] 写 test_merge_revision_replaces_pending_without_duplicate、test_old_poll_cannot_overwrite_new_reply、test_refresh_restores_voice_turn、test_background_delay、test_unmount_aborts_poll；本地 Python 测试断言请求没有 history、同一 request_id 查询回执、无法确认时不重发。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_shared_voice_client.py -v` 和 `node --test apps/web/tests/conversationSync.test.mjs` 确认 RED；沿用项目现有 TS 测试编译方式。
- [ ] 实现增量加载直到 has_more=false，按 revision 忽略旧响应；加载错误保留已有消息并显示离线。网页乐观输入按 request_id 归并，不再维护权威历史或引用。本地消息移除正文终端输出，保留无正文状态诊断。
- [ ] 同命令 GREEN；在 apps/web 运行 `npm run build`，确认 TypeScript/Vite 成功。
- [ ] 记录阶段一完成：两个入口契约已统一；不以自动测试替代真人接续验收。

## 任务 5：统一语音状态与控制

Files：新 wake/control.py、api/voice_control.py；修改 wake/launcher.py、runtime.py、api/app.py、网页 useLiveVoice.ts、Composer.tsx；新 tests/test_voice_control.py、apps/web/tests/voiceControl.test.mjs。

Interfaces：VoiceControlState.publish(phase: str, heartbeat: float) -> None，snapshot(now: float) -> dict，enqueue(command: str) -> None，take() -> str | None；phase 使用 waiting/connecting/listening/busy/speaking/paused/stopped/error/unknown。GET /api/voice/control/status，POST /api/voice/control/command {command: pause_speech|end_session|stop_service}；本地内部心跳 POST 同一路由子路径 /heartbeat。

鉴权：launcher 每次生成 secrets.token_urlsafe(32)，只经环境传给 API/监听；网页从同源 GET /api/voice/control/token 取令牌，该接口校验 Host 回环、Origin（存在时必须同源）及 Sec-Fetch-Site，不向第三方跨域开放。所有控制写操作要求匹配 Origin 和 X-Yu-Control-Token；仅本机 listener 可带令牌和固定同源 Origin 发布心跳。不新增 CORS 通配。不记录令牌。

- [ ] 写 test_foreign_origin_cannot_stop、test_old_token_rejected、test_heartbeat_older_than_five_seconds_is_unknown、test_stop_command_has_priority、test_local_listener_disables_web_capture。同步客户端也须把 unknown 当不可确认状态，不能默默抢麦克风。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_voice_control.py -v` 与 `node --test apps/web/tests/voiceControl.test.mjs` 确认 RED。
- [ ] 实现一秒心跳、控制轮询和优先级 stop_service > end_session > pause_speech；控制无需等待普通聊天队列。网页显示状态并禁止双入口同时采集；launcher 对正常停止回收 API。
- [ ] 同命令 GREEN；既有 WebSocket 同源/单会话回归测试通过。
- [ ] 记录完成证据，不自动提交。

## 任务 6：单请求唤醒和音频时效

Files：修改 wake/config.py、state.py、capture.py、session.py、runtime.py、config/voice_wake.yaml；扩展 tests/test_wake_capture.py、test_wake_session.py、test_wake_cleanup.py。

Interfaces：WakeConfig.continuous_mode: bool=False；AudioCapture.read(timeout: float) -> bytes 保持调用契约，内部队列保存 (monotonic_time, pcm)，新增 StaleAudioError(CaptureError)；recover_backlog() -> None 仅清理过期/容量故障，不清除设备或格式故障。

- [ ] 写 test_first_final_closes_audio_and_ignores_background_final、test_explicit_continuous_mode_accepts_next_turn、test_two_second_old_audio_is_not_sent、test_decoder_shutdown_does_not_fill_queue、test_backlog_ends_only_current_round、test_device_failure_does_not_restart。明确两秒边界为年龄 >2 秒过期。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_wake_capture.py tests/test_wake_session.py tests/test_wake_cleanup.py -v` 确认 RED。
- [ ] 默认第一条有效 final 后立即关云端上传、冻结普通请求，等待真实回执并进入本地播放控制阶段，保留已收到控制的优先性。无消费者的关闭/重建阶段暂停入队；容量/过期终止当前轮，实际 stream.active 和输入设置确认后才恢复待唤醒；设备错误关闭采集并发布 error。
- [ ] 同命令 GREEN；重复识别句、终止时队列、已执行回执不重发的旧测试继续有效。
- [ ] 记录完成证据，不自动提交。

## 任务 7：可打断朗读与本地控制词

Files：修改 feedback.py、detector.py、native-wake.ps1、runtime.py；扩展 tests/test_wake_runtime.py、test_wake_detector.py；新 tests/test_interruptible_speech.py。

Interfaces：SpeechPlayback.start(text: str) -> None，poll() -> int | None，stop() -> None，close() -> None；只管理自己 Popen 的朗读进程。KeywordDetector(config, phrases: tuple[str,...] | None=None)，accept(pcm: bytes) 仍返回唤醒 bool；take_command() -> str | None 为控制模式独立结果，不使普通唤醒语法接受控制。

- [ ] 写 test_cancel_terminates_owned_speech_process、test_control_phrase_never_becomes_chat、test_stop_service_during_speech_closes_capture、test_pause_keeps_service_waiting、test_exact_control_phrase_not_read_aloud、test_playback_failure_keeps_text_receipt。采用可控子进程模拟真实阻塞，断言退出与资源释放，不只断言 cancel。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_interruptible_speech.py tests/test_wake_runtime.py tests/test_wake_detector.py -v` 确认 RED。
- [ ] 用 Popen/stdin 提供本地朗读文本，取消 terminate/wait/kill 只针对自身子进程。朗读期间唯一采集流交给本地固定暂停/关闭语法，不云上传、不执行普通句子；暂停后默认回待唤醒。未连接时停止依赖网页/Ctrl+C，不虚报口头控制覆盖。
- [ ] 同命令 GREEN；音色缺失保留真实文字回执，不切换收费 TTS。控制词整句不得自动朗读；回声和音乐误触发仍列真人验收。
- [ ] 记录完成证据，不自动提交。

## 任务 8：整体验证与交付

Files：更新 DEV_STATUS.md、docs/voice-china.md、本计划复选框；新增 tests/test_shared_conversation_flow.py。

- [ ] 写跨入口集成测试 test_web_then_voice_then_web、test_restart_retains_context_without_replaying_actions、test_voice_then_web_memory_reference，使用临时 SQLite 与确定性 provider，不录音。
- [ ] 执行完整 `.venv/Scripts/python.exe -m pytest`，预期零失败，报告既有弃用告警；在 apps/web 执行全部 `node --test tests/*.test.mjs` 和 `npm run build`，任一失败不得宣称完成。
- [ ] 一个独立审查检查共享上下文权威性、线程生命周期、控制鉴权、重复动作及音频清理；修复重要问题并补回归，再运行受影响测试和全套验证。
- [ ] 在请求真人测试前保持服务停止。启动验证时说明麦克风采集、默认单请求行为和唤醒后费用；分别验收两方向接续、刷新/重启、微信主窗口、朗读暂停/关闭、背景音乐、重新唤醒与持续运行。
- [ ] 最终明确已完成/部分完成/待处理以及证据和局限；没有真人证据不勾选真人验收。无授权不提交或推送。

## 计划自审与交接

设计覆盖：持久化/备份→任务1；顺序与幂等→任务2/3；两入口历史、刷新→任务4；状态互斥与安全→任务5；背景句门控与积压→任务6；朗读控制→任务7；独立审查和真人验证→任务8。五个审查风险均有具名测试。

已明确修订游标与创建序号分离，避免状态更新漏同步；引用 None 与 [] 分离；一致 request_id 查询不触发重放。默认不引入多会话 UI 或新基础设施。

推荐继续当前会话由主代理逐任务执行，末尾做一次独立审查；任务接口强依赖，逐任务分发会增加上下文和协调成本。计划审核后使用 executing-plans，沿用此前当前会话执行偏好。尚未修改运行代码或执行本计划。
