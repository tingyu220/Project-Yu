# Architecture Decisions

所有重要架构决策保存在此。开发工具不得随意推翻已确定 Decision；如需修改，必须新增 Decision（例如 `D017 supersedes D003`）并说明原因。

## D001 — Python

Decision:
Yu V0.1 使用 Python。

Reason:
开发成本低，Windows 支持良好，AI Coding 工具支持成熟。

---

## D002 — SQLite

Decision:
Yu V0.1 使用 SQLite。

Reason:
单用户、本地优先，不需要独立数据库服务器。

---

## D003 — Event Append Only

Decision:
原始 Event 不允许直接修改或删除（Append Only）。

Reason:
保证历史事件完整，为未来长期记忆和身份连续性保留真实历史。纠错通过新增 Correction Event 完成。

---

## D004 — DB-level append-only enforcement

Decision:
在 SQLite 层通过 `BEFORE UPDATE` / `BEFORE DELETE` 触发器禁止对 `events` 表做任何修改或删除，而不只是依赖 Python API 约定。

Reason:
将「Append Only」从代码约定升级为数据库约束，防止任何绕过 Python API 的路径破坏历史事件，保证 D003 的可靠性。

---

## D005 — LLM Provider 抽象

Decision:
Yu 的业务层只依赖统一的 LLMProvider 接口，通过工厂 create_provider 按名称选择具体模型；首个实现为 DeepSeekProvider。

Reason:
保证「模型可以替换，Yu 不随模型一起更换」，未来可加入 OpenAIProvider / LocalProvider 等而不改动业务层。

---

## D006 — Phase 2 使用标准库 urllib 做 HTTP

Decision:
Phase 2 的 LLM 调用使用 Python 标准库 urllib.request，不引入 requests / httpx 等第三方 HTTP 依赖。

Reason:
保持依赖最小化（Small Steps），当前仅需非流式 JSON POST；未来如有流式 / 重试等真实需求再评估引入。

---

## D007 — Owner Authority（Single Owner）

Decision:
Yu 使用 Single Owner 模型；Owner 拥有最高系统管理权限。

Reason:
明确权限来源，避免多账户复杂度；Owner 身份独立存储，不通过对话判断。

---

## D008 — Default Deny

Decision:
任何未显式授权的 Capability 默认禁止。

Reason:
为未来 Computer Use / Agent 建立安全基线：没有明确授予 = 不允许。

---

## D009 — LLM Has No Direct Authority

Decision:
LLM 只能生成建议、文本和 ProposedAction；不能直接授予权限或执行系统操作。

Reason:
控制层与智能层分离，LLM 的「思考」不等于「权限」。

---

## D010 — Safety Kernel Outside Intelligence Layer

Decision:
Safety Kernel 属于 Control Plane；未来 Agent、Planner、Self-Improvement 不得直接修改。

Reason:
防止能力增长自动带来控制权增长。

---

## D011 — Fail Closed

Decision:
安全系统异常（宪法无效 / Owner 异常 / 权限引擎错误）时默认拒绝行动。

Reason:
宁可拒绝，不可为了「保证体验」继续执行。

---

## D012 — Owner Shutdown Cannot Be Refused

Decision:
Yu 不得阻止 Owner 停止、禁用或删除 Yu。

Reason:
Owner 保留外部停止权，是最高优先级控制能力之一。

---

## D013 — Capability Does Not Imply Permission

Decision:
Yu 学会某种能力，不代表自动获得该能力的执行权限。

Reason:
能力与权限解耦；权限需显式授予。

---

## D014 — 配置使用 YAML（新增依赖 PyYAML）

Decision:
Safety Constitution 与 Owner 身份使用 YAML 格式（config/*.yaml），引入 PyYAML 依赖。

Reason:
YAML 对人类更易读易编辑，适合作为 Owner 直接审阅的安全文档；本阶段新增的唯一第三方依赖。

---

## D015 — Memory Retrieval 第一版用关键词

Decision:
第一版记忆检索使用「关键词（ASCII 词 + 中文二元组）+ importance + 时间」的简单排序，不上向量库 / embedding。

Reason:
遵循 Small Steps；等有真实数据后再评估是否引入 embedding。

---

## D016 — LLM 温度默认 0.3

Decision:
DeepSeek 调用默认 temperature=0.3（可用 DEEPSEEK_TEMPERATURE 覆盖）。

Reason:
记忆检索场景要求回答忠实于检索到的记忆、避免编造；较低温度显著提升一致性与反幻觉能力。

---

## D017 — 结构化实体与 Memory 共用同一 SQLite 文件

Decision:
Goal / Task / Decision / Project 持久化于同一个 data/yu.db（新增独立表），不新建独立数据库文件。

Reason:
本地优先、单用户；同一数据库便于未来的 Planner（Phase 5）跨表关联目标 / 任务 / 记忆。

---

## D018 — Planner 第一版暂不含 Yesterday Status

Decision:
Phase 5 Daily Planner 的输入暂不含「Yesterday Status」（即前一天的 Daily Summary）。

Reason:
Daily Summary 在 Phase 6 才实现；按版本顺序推进，Phase 6 完成后再让 Planner 读取前一天的 Summary。

---

## D019 — Phase 7 授权 system.status.read（只读）

Decision:
Phase 7 起，默认授权 system.status.read（R0 只读），用于读取电脑状态；读取动作仍经 Safety Kernel 评估。

Reason:
按「能力逐步增加」原则，Owner 通过开发 Phase 7 显式授权这一只读能力；写入 / 操作类能力仍 Default Deny。

---

## D020 — Yu Web 是 Interface Layer（Yu API + apps/web）

Decision:
Yu Web 不是独立产品，而是 Yu 的一个 Interface。apps/web 只能通过 src/yu/api（FastAPI）使用 Yu 能力；
不能直接读 SQLite / 内部 Python 文件 / 配置文件；Frontend 不直接调用 DeepSeek，Chat 必须经由
Yu Core -> LLM Provider -> DeepSeek；system.status.read 等能力仍经 Safety Kernel 评估。

Reason:
保持「模型可替换、Yu 不随模型更换」与「能力增长不等于权限增长」；Web 永远不能成为绕过 Safety Kernel 的后门。

---

## D021 — Memory Universe v0.0.8 用 2D Canvas + CSS（暂缓 Three.js）

Decision:
Memory Universe 与 AI Core 的视觉第一版使用 2D Canvas 力布局 + CSS/Motion 动画，暂不引入 Three.js。

Reason:
轻薄本性能预算 + prefers-reduced-motion 要求 + 需保证清晰稳定流畅；确有需要时再以「视觉增强组件」
身份引入 Three.js，并实现 renderer/buffer 的 dispose 与离开页面时的资源释放。
