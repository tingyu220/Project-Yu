# Yu Development Status

## Version

Yu v0.0.9 —— Action MVP / Windows First。

## Current Phase

2026-10-08 真人反馈修复（部分完成）：DONE — 根据实际窗口枚举排除 WxTrayIconMessageWindow 消息辅助窗口；只读实机筛选返回“微信”，未激活窗口。新增“停止本次服务 / 关闭语音服务”等整句停止命令，不交给聊天模型；STOPPED 退出监听循环，启动管理器正常回收 API。修复连接握手期间无消费者却继续积压录音的溢出路径。
CURRENT / TODO — 朗读时仍暂停输入，停止命令须在可听取指令时说；即时打断朗读、背景声音过滤、其他音频积压路径、网页/本地上下文同步及真人关闭验收待处理。保持项目停止，不自动开启麦克风；未提交或推送。

2026-10-08 免点击唤醒：实现已接通，整体部分完成（真人验收待处理）— 用户批准改用 Windows 中文固定语法引擎；本地采集/唤醒、既有云端实时对话与动作、本地朗读、结束回待唤醒和统一启动已实现。没有下载模型或增加云端供应商。
DONE — 内存合成“嘿宇”的真实引擎识别测试、16k 麦克风预检和限时监听通过；独立审查发现的结束竞态、采集故障误报、初始化取消和管道阻塞问题已补回归测试修复。启动脚本现在不要求网页或语音按钮。
DONE — 完整自动测试 240 passed，保留 1 条既有弃用告警；服务已重新启动并进入本地待唤醒。CURRENT / TODO — 真人“唤醒→微信→结束→再唤醒”、音乐干扰及耳机/扬声器误唤醒率验收；暂不宣布全部体验完成。

2026-10-08 重复启动修复：DONE — 统一 app.open 执行层按完整程序路径检查已有进程，优先恢复既有主窗口；恢复失败或多实例歧义时不启动新实例。检查与启动互斥。
验证：pytest 199 passed，保留 1 条 Starlette/httpx 弃用告警；部署后真实 API 打开微信返回“已恢复 微信窗口”，前后进程 ID 完全一致。
CURRENT — Windows 优先的常驻助手设计：复用现有实时语音，评估本地唤醒、中文识别和朗读，DeepSeek 负责对话。TODO — 本地语音性能验证、桌面 EXE 封装；手机与跨端网页延后。尚未替换阿里云，也未实现常驻唤醒。

2026-10-08 应用升级适配：DONE — QQ音乐、微信通过 Windows 安装登记动态定位，移除固定版本路径，14 项相关测试通过。
DONE — 服务已重启，真实 API 调用打开 QQ音乐、微信均成功。TODO — 持续语音完整真人验收及尚未接入的天气能力。

2026-09-08：持续实时语音目标进行中。开启一次后持续识别、自动断句并串行执行，无需编辑或手动发送。
北京实时 ASR、本机 WebSocket、音频生命周期和非阻塞动作已实现；真实 Key/麦克风端到端仍待验收。
独立审查的业务失败后继续执行、连接中停止未释放两项问题已修复并补测。详见文末最新进展及 docs/voice-china.md。
此前 QQ音乐播放及下一首已核验，但不能代替本轮实时语音验收。不包含关闭浏览器后常驻唤醒。

## Status

自动化验证：pytest **188 passed, 0 failed**；保留 1 条既有 Starlette/httpx 弃用告警。前端五个测试脚本及 TypeScript/Vite 构建通过。
2026-09-07 通过 API 聊天链路实际打开 QQ音乐、Chrome、下载目录、Creative OS、Yu项目；
系统进程窗口及 Explorer 目录核对通过，审计包含 PROPOSED / ALLOWED / EXECUTED。
未知应用返回 APP_NOT_FOUND 并记录 ACTION_FAILED。此处成功表示已提交系统打开请求，
不代表应用内部加载或播放完成。Obsidian 尚未配置和验收。

本机启动时显式设置 YU_ALLOW_LOCAL_OPEN=1 才授予 process.start，未设置仍默认拒绝。
本轮修复空路径变成当前目录的问题，并拒绝通过普通文件打开执行脚本及快捷方式。
真实 data/yu.db 迁移验证通过（2 条旧记忆回填为 USER_EXPLICIT + 证据）。

---

## v0.0.9 Action MVP 实现内容

- `ActionResult` 统一执行结果契约；
- Windows App/Path Registry，配置驱动且不猜测路径；
- Windows Executor，支持 `app.open`、`path.open`、`file.open`，禁止 `shell=True`；
- 本地确定性 Action Router，明确动作不进入 LLM，模糊对象返回普通聊天；
- ActionService 接入 `ProposedAction → SafetyKernel → Permission → Executor → Audit`；
- CLI 与 Web/API 接入，API 同时保留旧 `kind/reply` 字段并提供 `type/content/action`；
- 应用和路径配置：`config/windows_apps.yaml`、`config/windows_paths.yaml`；
- 19 个 Action 专项测试，覆盖权限拒绝、执行失败和审计事件。

明确未实现：

- 语音、唤醒词、手机端、Cloud；
- QQ 音乐内部搜索、歌单、播放控制；
- UI Automation、视觉识别、OCR、鼠标键盘控制；
- 自动猜测应用路径、联网下载、删除/移动/修改文件。

---

## ROOT CAUSE（三个真实 Bug，方案 §7）

### FALSE MEMORY ROOT CAUSE

    A — LLM spontaneous hallucination（主因）+ B/C 纵深防御缺口

链路：User「我要去爬山」→ Retrieved Memories（无膝盖）→ Context Builder（旧版扁平文本无来源分区）→
System Prompt（仅「不要编造」软约束，无历史归因禁令）→ LLM 自发生成「你之前提到过膝盖……」。

### WRONG ROUTING ROOT CAUSE

    Keyword-based system intent override（关键词路由先于显式命令）

「记住：……华硕轻薄本……」未先识别为 MEMORY_CREATE，可能落入 Computer Context / 普通 LLM 路径，
导致「记住」被当成闲聊，LLM 可能口头答应却不写库。

### FAKE UPDATE ROOT CAUSE

    LLM generated success response without tool verification

「修改这条记忆」没有后端 Update 能力，也没有 Read-After-Write；LLM 直接生成「已更新」却未改数据库。

修复原则（方案 §3.7 / §32）：**No Verified Result, No Success Claim**。

---

## 实现内容

### Memory Grounding（上一轮，保留）

- Memory Schema 升级：source_type / source_role / source_event_id / confidence + verified 派生属性；Event 带 role 与 event_id。
- MemoryWriteValidator：Source → Role → Type → Confidence 四道写入门；assistant / 推断 / 摘要 / 无来源 Personal Memory 写入拒绝。
- Retrieval Provenance：build_context 分区 [VERIFIED USER MEMORY] / [UNVERIFIED OBSERVATION]。
- Prompt Grounding + MemoryAttributionGuard + MemoryCorrectionService + No-Evidence 确定性回答。

### Memory Reliability（本轮新增）

1. Intent Router（src/yu/memory/router.py）：确定性识别 MEMORY_CREATE / READ / SEARCH / UPDATE / CORRECT / ARCHIVE，
   先于 Planner / Computer Router 执行。
2. MemoryService（src/yu/memory/service.py）：统一 Create / Update / Archive / Correct，全部 Read-After-Write 验证，
   返回标准化 MemoryResult（operation / memory_id / success / verified / before / after / reason）。
3. Memory Update：store.update_memory（affected_rows=0 → None → 报告失败）；新增 updated_at 列 + 迁移。
4. Reference Resolution：resolve_reference —— 1 条绑定、多条询问「你指的是哪一条」、禁止猜测。
5. Audit 新增：MEMORY_CREATED / MEMORY_UPDATED / MEMORY_ARCHIVED（此前已有 CORRECTED / INVALIDATED /
   HALLUCINATION / WRITE_REJECTED / CLAIM_UNSUPPORTED）。
6. API 新增：POST /api/memories（create）、POST /api/memories/{id}/update、POST /api/memories/{id}/archive，
   均返回 current server state；POST /api/chat 增加 referenced_memory_ids。
7. 前端同步：Chat 记住 / 修改 / 忘掉触发 memory 刷新；Conversation Chip 显示 memory_id + 当前内容；
   Memory Detail 显示 SOURCE / EVENT / VERIFIED / CONFIDENCE / UPDATED。
8. Debug Trace（YU_MEMORY_DEBUG=1）：INPUT / INTENT / ROUTER_RESULT / REFERENCED_MEMORY_IDS /
   RETRIEVED_MEMORY_IDS / SOURCE_TYPES / MEMORY_COMMAND / DATABASE_RESULT / READ_AFTER_WRITE_RESULT /
   CACHE_INVALIDATION / API_REFRESH / FINAL_LLM_CONTEXT（不含 Key/Secret）。

---

## Architecture Report（方案 §80）

### Database Migration
- memories 表新增 updated_at 列（幂等 ALTER + 回填 created_at）；provenance 列沿用上一轮迁移。
- events 表新增 role 列。旧记忆：有 user 事件 → USER_EXPLICIT，无事件 → UNKNOWN（不伪造来源）。

### Memory Schema Changes
- Memory：+ source_type / source_role / confidence / updated_at；verified 为派生属性。
- Event：+ role；event_id 为派生字符串引用。

### Router Changes
- 新增 detect_memory_intent；chat 路由顺序改为 Memory Intent → Planner → Computer → 普通对话。

### CRUD Changes
- 新增 MemoryService.create / update / archive / correct / resolve_reference；Read-After-Write + 审计。
- store 新增 update_memory；archive/invalidate 已有 affected_rows 检查。

### Retrieval Changes
- build_context 按 provenance 分区；retrieve 直接读 SQLite（无缓存）。

### Cache Changes
- 当前无 retrieval cache / embedding / index，故无「旧缓存」问题；更新后检索立即返回新值（Test 009 验证）。
- 若未来引入缓存，更新路径需接 invalidate（已在方案 §42 预留）。

### API Changes
- 新增 memory CRUD 端点 + referenced_memory_ids + memory_result / intent 响应字段。

### Frontend Changes
- types.ts / api.ts 增补 provenance 与 CRUD 客户端；useConversation 记住引用 id 并刷新；
  YuMessage chip 显示 memory_id；MemoryDetail 显示 provenance；Cockpit 记忆变更后刷新 memory count。

### Files Deleted
- 无。

---

## Definition of Done（方案 §82）

- [x] False Memory Grounding / Memory Provenance / Role Separation
- [x] Explicit Memory Routing（Test 003）
- [x] Create / Update / Archive Verification（Read After Write）
- [x] Fake Success Prevention（Test 008）
- [x] Retrieval 无旧数据（Test 009，无缓存直接读库）
- [x] API / Conversation / Memory Universe 同步（test_memory_api + 前端）
- [x] Correction + Audit（Test 012）
- [x] Existing Data Migration（data/yu.db 2 条 → USER_EXPLICIT）
- [x] Restart Persistence（Test 002 / E2E）
- [x] Full pytest（133 passed）

---

## Tests

pytest **133 passed, 0 failed**：84 Yu Core + 11 API Adapter + 14 Memory Grounding + 16 Memory Reliability + 8 Memory API。

- tests/memory_grounding/test_memory_grounding.py：方案 v0.0.7.2 §49-59 Test 001-010 + Validator/Guard。
- tests/memory_reliability/test_memory_reliability.py：方案 §57-73 Test 001-015 + 端到端生命周期。
- tests/test_memory_api.py：CRUD 端点 + chat 显式路由 + 同步 + Fake Update 防护。
- 前端：tsc --noEmit 通过；vite build 通过（668 modules）。

## Known Issues

1. 真实 LLM 复现需设置 DEEPSEEK_API_KEY；未设置时对话降级为本地只读/确定性回答。
2. 记忆检索仍为关键词（中文 bigram），「我最近在做什么」这类无关键词重叠的召回需依赖 LLM 或未来 embedding。
3. 前端未接 TanStack Query；同步采用「写操作成功后 refetch」的显式策略（方案 §46 的 no-query-library 分支）。
4. pytest 打印一条 starlette httpx→httpx2 弃用告警（非阻塞）。

## Architecture Deviations

- 版本号：方案里程碑名为 v0.0.7.2（Core），但包版本沿用 0.0.8.1（Web Experience 主版本 + 补丁），
  避免从 0.0.8 降级；DEV_STATUS 记录 Core 里程碑为 v0.0.7.2。
- Retrieval 无缓存，故 Cache Invalidation 阶段以「无缓存 + 读后即最新」的测试覆盖，而非实现缓存层。

---

## Files Added

- src/yu/memory/router.py（MemoryIntent Router）
- src/yu/memory/service.py（MemoryService CRUD + Read-After-Write + 结果对象）
- src/yu/memory/provenance.py（上轮）+ 本轮增 audit 事件与 memory_debug_emit
- src/yu/memory/validator.py / guard.py / correction.py（上轮）
- tests/memory_grounding/、tests/memory_reliability/、tests/test_memory_api.py

## Files Modified

- src/yu/memory/models.py、store.py、retrieval.py、__init__.py
- src/yu/llm/conversation.py、src/yu/daily.py、src/yu/planner.py
- src/yu/api/app.py、schemas.py、src/yu/cli.py
- apps/web/src/lib/types.ts、api.ts、useConversation.ts
- apps/web/src/components/YuMessage.tsx、MemoryDetail.tsx、apps/web/src/pages/Cockpit.tsx
- DECISIONS.md（D022-D031）、DEV_STATUS.md、pyproject.toml、src/yu/__init__.py

## Next Recommendation

1. 设置 DEEPSEEK_API_KEY 后按方案 §83 做人工验收（Case 1-5）。
2. 开发期用 YU_MEMORY_DEBUG=1 与 Memory Universe Detail 面板抽查记忆 SOURCE / EVENT / CONFIDENCE。
3. 待 Memory Truth 稳定后，再恢复 Yu Web 视觉优化。
## 持续实时语音进展（2026-09-08，最新状态）

- 当前目标：用户已批准开启一次后持续监听、自动断句执行、无编辑发送步骤；目标进行中。
- 识别：北京 Qwen3-ASR-Flash-Realtime，后端保管 Key；16 kHz PCM 每 100 ms 分块、800 ms VAD 断句。
- 会话：Cockpit 持有资源，首句布局切换不重建；最多三句排队、item_id 去重、停止清队列、断线不自动重放。
- 非阻塞：LLM、系统状态及动作执行的耗时 I/O 离开事件循环；权限、SQLite、审计仍在原线程。
- 防误触：监听期间禁用助手朗读；外放音乐、旁人声音仍需真人环境验证，建议耳机。
- 自动检查：pytest 188 passed（1 条既有 Starlette 弃用告警）；Node PCM/队列/会话生命周期/业务失败/朗读禁用/旧句尾检测通过；TypeScript/Vite 构建通过（既有 >500 kB 提醒）。
- 独立审查：两项 P2 已修复。业务失败会结束监听并清空待执行队列；供应商握手期间也读取浏览器断连并取消握手。
- 页面检查：本机隔离数据库服务验证默认未配置提示、首句切换后的入口；390px 下 document 宽度与 scrollWidth 均为390。浏览器截图能力本次不可用，不声称完成视觉截图验收。
- 待验证：真实 Key 开通权限、实际麦克风、持续多句及QQ音乐端到端、延迟与噪声体验。未提交、未推送。
- 不包含：浏览器关闭后的常驻唤醒、可打断全双工自动播报。旧批量转写后端仍保留兼容，但主界面改用实时会话。
