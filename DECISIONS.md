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
