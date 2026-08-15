# Yu Development Status

## Version

Yu v0.0.4

## Current Phase

Phase 4 — Goals / Tasks / Decisions / Projects（已完成）

## Status

PASS（自动化验证通过：pytest 67 passed + CLI 实体命令冒烟验证通过）

## Original Goal

将重要长期状态（目标 / 任务 / 决策 / 项目）从普通 Memory 中结构化，建立独立的数据模型与持久化。

## Implemented

1. 结构化实体模型（entities/models.py）：Goal / Task / Decision / Project
2. SQLite 持久化（entities/store.py），与 Memory 共用 data/yu.db，新增独立表
3. Goal：创建 / 列出 / 状态更新（active / completed / archived）
4. Task：创建 / 列出 / 状态更新（todo / doing / done），含 priority、due_date、related_goal、related_project 外键
5. Project：创建 / 列出 / 更新（status、current_goal、next_step、notes）
6. Decision：创建 / 列出（decision / reason / constraints / alternatives）
7. CLI 新增命令：目标 / 任务 / 项目 / 决策 的创建与列出，完成目标 <id> / 完成任务 <id>
8. pytest 测试扩展至 67 项（实体 9 + 检索 11 + 安全 20 + LLM 15 + 记忆 12）

## Actual Behavior

### CLI 冒烟测试（真实运行，临时数据库）

Input:
> 目标：学习 AI
> 任务：完成 pytest 测试
> 项目：Yu
> 决策：Yu V0.1 暂时只开发 Windows PC
> 目标
> 任务
> 项目
> 决策
> 完成任务 1
> 任务

Output:
> 已记录目标。Goal ID: 1
> 已记录任务。Task ID: 1
> 已记录项目。Project ID: 1
> 已记录决策。Decision ID: 1
> [1] (active) 学习 AI
> [1] (todo/medium) 完成 pytest 测试
> [1] (active) Yu
> [1] Yu V0.1 暂时只开发 Windows PC
> 任务 [1] 已标记为 done。
> [1] (done/medium) 完成 pytest 测试

## Tests

pytest: 67 passed, 0 failed

覆盖：Goal/Task/Decision/Project 的创建、列出、持久化、状态更新、外键约束，
以及实体与 Memory 共用同一数据库的隔离性。

## Files Added

- src/yu/entities/__init__.py
- src/yu/entities/models.py
- src/yu/entities/store.py
- tests/test_entities.py

## Files Modified

- src/yu/cli.py（新增 目标/任务/项目/决策 命令与处理函数）
- src/yu/__init__.py（版本号 0.0.3 → 0.0.4）
- pyproject.toml（版本号 0.0.3 → 0.0.4）
- DECISIONS.md（新增 D017）
- README.md（本地命令补充实体命令）

## Files Deleted

无。

## Database Changes

新增（data/yu.db，复用同一文件）：
- goals 表（id / title / status / created_at / updated_at）
- projects 表（id / name / status / current_goal / next_step / notes / created_at / updated_at）
- tasks 表（id / title / status / priority / due_date / related_goal / related_project / created_at / updated_at，外键指向 goals / projects）
- decisions 表（id / decision / reason / constraints / alternatives / created_at）

## 新增依赖

无。

## Architecture Deviations

D017：结构化实体与 Memory 共用同一 SQLite 文件（data/yu.db），新增独立表而非独立数据库文件。原因：便于 Phase 5 Planner 跨表关联目标 / 任务 / 记忆。

## Known Issues

无（Phase 4 范围内）。

## User Experience

（待用户实际使用后填写）

## Next Recommendation

进入 Phase 5 — Daily Planner（Yu v0.0.5）：让 Yu 第一次真正参与用户每天的决策——
结合 Goals / Tasks / Projects / Recent Memories / Yesterday Status 生成「今天最值得做的事」。

注意：此处仅为建议，开发工具不得自动进入下一阶段，需用户确认。
