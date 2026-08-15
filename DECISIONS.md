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
