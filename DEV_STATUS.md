# Yu Development Status

## Version

Yu v0.0.8.1 —— Memory Grounding & Provenance + Memory Reliability（Core 修复，对应方案里程碑 v0.0.7.2）。

## Current Phase

Phase 8 — Web Experience（Yu Web）。本阶段**暂停新增功能**（新 UI / Agent / Planner / Voice / Computer Control / Self Improvement），
只修 Memory 核心可靠性；Memory Universe 仅增加 Debug 信息（provenance 字段），不做视觉重构。

## Status

PASS（自动化验证：pytest **133 passed, 0 failed** + 前端 tsc --noEmit 通过 + vite build 通过 + API 端到端冒烟通过）。
真实 data/yu.db 迁移验证通过（2 条旧记忆回填为 USER_EXPLICIT + 证据）。

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
