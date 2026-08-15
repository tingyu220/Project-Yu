# Yu Development Status

## Version

Yu v0.0.7

## Current Phase

Phase 7 — Computer Context（已完成）

## Status

PASS（自动化验证通过：pytest 84 passed + 真实电脑状态读取与 LLM 分析冒烟验证通过）

## Original Goal

让 Yu 第一次拥有有限的「环境感知能力」：通过 psutil 读取 CPU / 内存 / 磁盘 / 电池 /
系统运行时间 / 高占用进程，并基于状态给出原因与建议。当前只允许读取、分析、建议，禁止任何操作。

## Implemented

1. 电脑状态读取（computer.py：read_computer_status）——psutil 读取 CPU/内存/磁盘/电池/运行时间/高占用进程
2. 状态格式化（format_status）与 LLM 分析（build_computer_advice，系统提示强调「只读、禁止操作」）
3. 自然语言识别（is_computer_request）：检测「我电脑为什么卡」等请求
4. CLI 新增 电脑状态 / 系统状态 命令，并把读取动作经 Safety Kernel 评估
   （ProposedAction[system.status.read] → Risk R0 → Permission → ALLOW → 读取 → 审计）
5. 默认授权 system.status.read（R0 只读，D019），写入/操作类能力仍 Default Deny
6. 新增依赖 psutil；pytest 扩展至 84 项（computer 5 + daily 7 + planner 5 + 实体 9 + 检索 11 + 安全 20 + LLM 15 + 记忆 12）

## Actual Behavior

### 真实端到端（真实 LLM + 真实系统状态）

Input:
> 权限
> 电脑状态
> 我电脑为什么卡？
> 审计

Output（要点）:
> system.status.read   GRANTED   （其余操作类 DENIED）
> 电脑状态：CPU 6.3% 正常；内存 86.8% 偏高（DeepSeek Harness 759.8MB、Feishu ~1GB…）；
>           建议仅指向用户自行处理（关闭不必要程序 / 重启），不执行任何操作
> 审计：[4] ACTION_ALLOWED actor=yu risk=R0 授权通过：system.status.read
>        [3] ACTION_PROPOSED actor=yu risk=R0 用户请求电脑状态分析

（读取动作经 Safety Kernel 评估并审计；LLM 分析遵守「只读、禁止操作」原则）

## Tests

pytest: 84 passed, 0 failed

覆盖：read_computer_status 字段、format_status、is_computer_request 识别、
build_computer_advice 注入、system.status.read 默认授权。

## Files Added

- src/yu/computer.py
- tests/test_computer.py

## Files Modified

- src/yu/cli.py（新增 电脑状态/系统状态 命令 + 自然语言识别 + Safety Kernel 路由）
- src/yu/safety/permissions.py（默认授权 system.status.read）
- tests/test_safety.py（grant/revoke 测试改用 file.read 作为未授权示例）
- src/yu/__init__.py（版本号 0.0.6 → 0.0.7）
- pyproject.toml（版本号 + 新增依赖 psutil）
- DECISIONS.md（新增 D019）
- README.md（本地命令补充 电脑状态）

## Files Deleted

无。

## Database Changes

无。

## 新增依赖

- psutil>=5.9（读取 CPU / 内存 / 磁盘 / 电池 / 进程）

## Architecture Deviations

D019：默认授权 system.status.read（R0 只读）。这是按安全阶段「能力逐步增加」原则，
由 Owner 通过开发 Phase 7 显式授权；操作类能力（process.stop / system.modify 等）仍 Default Deny。

## Known Issues

1. 电脑状态读取的 CPU 使用率采用短采样（interval=0.1s），可能波动；如需更稳定读数可加长采样窗口。

## User Experience

（待用户实际使用后填写）

## Next Recommendation

进入 Phase 8 — Desktop UI（Yu v0.0.8）：让 Yu 从开发工具变成用户愿意每天打开的程序，
建议使用 PySide6 实现一个简单、快速、稳定的桌面界面（对话 + 状态栏）。

注意：此处仅为建议，开发工具不得自动进入下一阶段，需用户确认。
