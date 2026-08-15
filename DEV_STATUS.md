# Yu Development Status

## Version

Yu v0.0.1

## Current Phase

Phase 0（Project Bootstrap）+ Phase 1（Memory Kernel）— 已完成

## Status

PASS（自动化验证通过：pytest 12 passed + 真实运行持久化验证通过；最终验收由用户确认）

## Original Goal

第一阶段：实现一个最小、可靠、持久化的 Yu Memory Kernel（Event + Memory + SQLite + CLI），
并建立一个可正常运行、可测试、可版本管理的最小 Python 项目。

## Implemented

1. 项目骨架：README / DECISIONS / RESEARCH_BACKLOG / DEV_STATUS / pyproject / .gitignore / src / tests / data
2. Git 仓库初始化，.gitignore 排除 data/*.db 与 .venv
3. Python 虚拟环境 + 可编辑安装（pip install -e ".[dev]"）
4. Event 数据模型（append-only）+ Memory 数据模型（Create / Read / Archive）
5. SQLite 持久化，首次启动自动建库
6. 数据库触发器禁止 UPDATE / DELETE events（对应 DECISIONS.md D004）
7. 基础 CLI：记住：xxx / 记忆 / exit
8. pytest 测试套件（12 项）

## Actual Behavior

### Example（真实运行，两次独立进程验证持久化）

首次启动：
Input:
> 记住：我正在开发属于自己的 Yu。
> 记忆

Output:
> 宇 Yu v0.0.1
> 已记录。
> Memory ID: 1
> [1] 我正在开发属于自己的 Yu。

重启程序（全新进程）：
Input:
> 记忆

Output:
> 宇 Yu v0.0.1
> [1] 我正在开发属于自己的 Yu。

## Tests

pytest: 12 passed, 0 failed

## Files Added

- README.md
- DECISIONS.md
- RESEARCH_BACKLOG.md
- DEV_STATUS.md
- pyproject.toml
- .gitignore
- data/.gitkeep
- src/yu/__init__.py
- src/yu/cli.py
- src/yu/memory/__init__.py
- src/yu/memory/models.py
- src/yu/memory/store.py
- tests/test_memory_kernel.py

## Files Modified

无。

## Files Deleted

无。

## Database Changes

新增：
- events 表（id / type / content / created_at）
- memories 表（id / type / content / importance / status / source_event_id / created_at / archived_at）
- 触发器 events_no_update / events_no_delete（禁止修改 / 删除 events）

## Architecture Deviations

原设计：Event Append Only 仅作为设计原则（D003）。
实际：额外在 SQLite 层通过触发器强制实现（D004，见 DECISIONS.md）。
Reason: 把「历史不可变」从代码约定升级为数据库约束，防止绕过 Python API 破坏历史事件。

## Known Issues

无（Phase 1 范围内）。

## User Experience

（待用户实际使用后填写）

## Next Recommendation

建议进入 Phase 2 — LLM Conversation（Yu v0.0.2）。

注意：此处仅为建议，开发工具不得自动进入下一阶段，需用户确认。
