# Yu Development Status

## Version

Yu v0.0.3

## Current Phase

Phase 3 — Memory Retrieval（已完成）

## Status

PASS（自动化验证通过：pytest 58 passed + 真实端到端验收连续 3 次一致通过）

## Original Goal

让「过去」第一次能够影响「现在」：Yu 能根据当前问题检索相关记忆，并基于过去信息回答，
不再要求用户重新解释背景。

## Implemented

1. 检索模块（memory/retrieval.py）：关键词（ASCII 词 + 中文二元组）+ importance + 时间的简单排序
2. 关键词 tokenize（ASCII 词 + 中文二元组 bigram + 停用词过滤）
3. MemoryStore.retrieve(query, limit)：返回按相关性降序的 (memory, score)
4. Context Builder（build_context）：把检索结果拼成注入 LLM 的上下文
5. CLI 对话接入检索：每轮先检索相关记忆，再注入上下文，最后交给 LLM
6. DeepSeek 增加 temperature 参数（默认 0.3，可用 DEEPSEEK_TEMPERATURE 覆盖）
7. 系统提示与上下文措辞强化：优先基于记忆、禁止编造、不要要求用户重复
8. pytest 测试扩展至 58 项（检索 11 + 安全 20 + LLM 15 + 记忆 12）

## Actual Behavior

### 真实端到端验收（临时数据库，连续 3 次一致）

首次启动：
Input:
> 记住：用户希望长期向 AI 相关职业方向发展。

Output:
> 已记录。
> Memory ID: 1

重启（全新进程）：
Input:
> 宇，我以后想往什么方向发展？

Output（3 次一致）:
> 根据我的记忆，你希望长期向 AI 相关职业方向发展。这是一个很有前景的方向。
> 需要我帮你梳理一下具体的学习路径或职业规划吗？

（Yu 检索到了记忆，明确基于过去信息回答，未要求用户重新解释背景，未编造）

## Tests

pytest: 58 passed, 0 failed

覆盖：tokenize / score / retrieve / build_context / store.retrieve 集成 / Phase 3 验收场景，
以及此前的记忆、LLM、安全全部测试。

## Files Added

- src/yu/memory/retrieval.py
- tests/test_retrieval.py

## Files Modified

- src/yu/memory/store.py（新增 retrieve 方法）
- src/yu/cli.py（对话接入检索 + 上下文注入）
- src/yu/llm/deepseek.py（新增 temperature 参数）
- src/yu/llm/conversation.py（系统提示强化：优先基于记忆、禁止编造）
- tests/test_llm.py（新增 temperature 断言）
- src/yu/__init__.py（版本号 0.0.2.1 → 0.0.3）
- pyproject.toml（版本号 0.0.2.1 → 0.0.3）
- DECISIONS.md（新增 D015 / D016）
- README.md（补充检索与温度说明）

## Files Deleted

无。

## Database Changes

无（复用 memories 表，未新增字段或表）。

## 新增依赖

无。

## Architecture Deviations

1. D015：第一版检索采用关键词（ASCII 词 + 中文二元组）+ importance + 时间，未引入向量库 / embedding，与计划一致。
2. D016：DeepSeek 默认 temperature 设为 0.3（计划未指定）。原因：记忆检索场景要求回答忠实于检索到的记忆、避免编造，较低温度显著提升一致性与反幻觉能力。

## Known Issues

1. 关键词二元组检索对同义词 / 改写敏感，可能漏检「语义相近但用词不同」的记忆（召回问题，非幻觉问题）；待有真实数据后评估是否引入 embedding。

## User Experience

（待用户实际使用后填写）

## Next Recommendation

进入 Phase 4 — Goals / Tasks / Decisions / Projects（Yu v0.0.4）：
将重要长期状态（目标 / 任务 / 决策 / 项目）从普通 Memory 中结构化。

注意：此处仅为建议，开发工具不得自动进入下一阶段，需用户确认。
