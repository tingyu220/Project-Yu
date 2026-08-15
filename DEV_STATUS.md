# Yu Development Status

## Version

Yu v0.0.5

## Current Phase

Phase 5 — Daily Planner（已完成）

## Status

PASS（自动化验证通过：pytest 72 passed + 真实 LLM 规划冒烟验证通过）

## Original Goal

让 Yu 第一次真正参与用户每天的决策：结合 Goals / Tasks / Projects / Recent Memories，
生成「今天最值得做的事」，并说明理由。

## Implemented

1. Planner 模块（planner.py）：Priority Decision System（非 Todo 生成器）
2. 上下文汇总（gather_context）：目标 + 任务 + 项目 + 近期记忆
3. 规划原则注入（PLANNER_SYSTEM_PROMPT）：完成优先 / 最多 3 个核心任务 / 现实可完成 /
   长期目标优先 / 显式处理拖延 / 说明理由 / 明确「今天不要做什么」
4. 自然语言识别（is_plan_request）：检测「我今天应该干什么」等规划请求
5. CLI 新增 规划 / 今日计划 / 计划 命令，并把自然语言规划请求路由到 Planner
6. pytest 测试扩展至 72 项（planner 5 + 实体 9 + 检索 11 + 安全 20 + LLM 15 + 记忆 12）

## Actual Behavior

### 真实端到端（临时数据库，真实 LLM）

Input:
> 目标：学习 AI
> 任务：完成 pytest 测试
> 项目：Yu
> 记住：用户希望长期向 AI 相关职业方向发展。
> 我今天应该干什么？

Output（要点）:
> 今天最重要的一件事：完成 pytest 测试（任务列表中唯一的具体任务）。
> 第二优先级：为「学习 AI」这个长期目标投入至少 30 分钟……
> 可选任务：整理 Yu 项目下一步 / 浏览一篇 AI 文章……
> 今天不要做什么：不要开启新的课程或新项目……
> 原因：1. 完成优先于开启 … 2. 长期目标需要每日微投入 … 3. 避免拖延陷阱 …

（Planner 正确识别自然语言请求，结合目标/任务/项目/记忆生成结构化计划，并说明理由）

## Tests

pytest: 72 passed, 0 failed

覆盖：is_plan_request 识别、gather_context 汇总、build_plan 注入原则与数据、规划原则完整性。

## Files Added

- src/yu/planner.py
- tests/test_planner.py

## Files Modified

- src/yu/cli.py（新增 规划 命令 + 自然语言规划识别 + _plan 函数）
- src/yu/__init__.py（版本号 0.0.4 → 0.0.5）
- pyproject.toml（版本号 0.0.4 → 0.0.5）
- DECISIONS.md（新增 D018）
- README.md（本地命令补充 规划）

## Files Deleted

无。

## Database Changes

无。

## 新增依赖

无。

## Architecture Deviations

D018：Planner 第一版输入暂不含「Yesterday Status」（前一天 Daily Summary），因 Daily Summary 在 Phase 6 才实现；Phase 6 完成后再接入。

## Known Issues

1. 自然语言规划识别基于简单关键词（今天 + 干什么/做什么/该做/计划/规划），可能误判或漏判；后续可扩展为更稳健的意图识别。

## User Experience

（待用户实际使用后填写）

## Next Recommendation

进入 Phase 6 — Daily Summary（Yu v0.0.6）：让 Yu 每一天都有一个清晰的状态快照
（今日计划 / 实际完成 / 未完成 / 新增记忆 / 重要决策 / 问题 / 项目状态 / 明天建议），
并作为次日恢复 Context 的基础。

注意：此处仅为建议，开发工具不得自动进入下一阶段，需用户确认。
