# Yu Development Status

## Version

Yu v0.0.2

## Current Phase

Phase 2 — LLM Conversation（已完成）

## Status

PASS（自动化验证通过：pytest 27 passed + 无 Key 优雅降级验证通过；真实 LLM 调用待用户配置 DEEPSEEK_API_KEY 后验收）

## Original Goal

为 Yu 接入第一颗可以替换的「大脑」：实现用户输入 → LLM 请求 → LLM 返回 → 多轮对话，
且业务层与具体模型解耦（模型可替换，Yu 不随模型一起更换）。

## Implemented

1. LLMProvider 抽象接口（base.py）：ChatMessage / LLMResponse / LLMError / LLMProvider(ABC)
2. DeepSeekProvider（deepseek.py）：OpenAI 兼容 chat/completions，标准库 urllib 实现
3. Provider 工厂（factory.py）：create_provider 按名称选择，默认 deepseek，可用 YU_LLM_PROVIDER 覆盖
4. 多轮对话状态（conversation.py）：Conversation，含 system 提示，支持 add/clear
5. API Key 使用环境变量 DEEPSEEK_API_KEY（可选 DEEPSEEK_MODEL / DEEPSEEK_BASE_URL）
6. CLI 升级为对话 REPL：默认输入走 LLM，保留 记住：/ 记忆，新增 重置，exit 退出
7. 基础错误处理：缺 Key / HTTP 错误 / 网络错误 / 非 JSON / 响应结构异常均转为 LLMError 且不崩溃
8. pytest 测试套件扩展至 27 项（LLM 层 15 项 + 记忆层 12 项）

## Actual Behavior

### 无 API Key 时（真实运行，优雅降级）

Input:
> 你好，介绍一下你自己
> 记忆

Output:
> 宇 Yu v0.0.2
> [警告] 缺少 API Key：请设置环境变量 DEEPSEEK_API_KEY
> 未配置 LLM，本轮仅支持记忆命令（记住：/ 记忆 / 重置 / exit）。
> 未配置 LLM Provider（缺少 DEEPSEEK_API_KEY），无法对话。
> [1] 我正在开发属于自己的 Yu。

（记忆命令在无 Key 时依然可用，程序不崩溃）

### LLM 请求 / 解析 / 错误处理（pytest mock 覆盖）

- 请求 URL 为 https://api.deepseek.com/chat/completions
- 请求头含 Authorization: Bearer <key> 与 Content-Type: application/json
- 请求体含 model / messages / stream=false，多轮消息按 system/user/assistant 序列化
- 正确解析 choices[0].message.content，并携带 model 与 finish_reason
- HTTP 401 / 网络错误 / 非 JSON / 结构异常 均抛出带上下文的 LLMError

## Tests

pytest: 27 passed, 0 failed

## Files Added

- src/yu/llm/__init__.py
- src/yu/llm/base.py
- src/yu/llm/deepseek.py
- src/yu/llm/factory.py
- src/yu/llm/conversation.py
- tests/test_llm.py

## Files Modified

- src/yu/cli.py（升级为对话 REPL）
- src/yu/__init__.py（版本号 0.0.1 → 0.0.2）
- pyproject.toml（版本号 0.0.1 → 0.0.2）
- README.md（补充环境变量说明）
- DECISIONS.md（新增 D005 / D006）

## Files Deleted

无。

## Database Changes

无（复用 events / memories 表，未新增或修改表结构）。

## Architecture Deviations

无。实现与原设计一致：LLMProvider 抽象 + DeepSeekProvider 实现 + API Key 环境变量 + Provider 可替换。

## Known Issues

1. 真实 LLM 端到端调用未验证：当前环境未设置 DEEPSEEK_API_KEY，无法发起真实请求，需用户配置 Key 后验收。

## User Experience

（待用户配置 DEEPSEEK_API_KEY 并实际使用后填写）

## Next Recommendation

建议进入 Phase 3 — Memory Retrieval（Yu v0.0.3）：让「过去」第一次能够影响「现在」。

注意：此处仅为建议，开发工具不得自动进入下一阶段，需用户确认。
