# Yu Development Status

## Version

Yu v0.0.8（Web Experience）— Yu Core 能力保持 v0.0.7（无退化），新增 Interface Layer。

## Current Phase

Phase 8 — Web Experience（Yu Web）：Life Cockpit + Memory Universe。

## Status

PASS（自动化验证通过：pytest 90 passed + 前端 tsc/vite 构建通过 + API 端到端冒烟通过）

## Original Goal

把 Yu 已拥有的「智能」可视化：让一个不认识 Project Yu 的人，在几十秒内理解——
它认识一个人、记得过去、知道今天该做什么、知道电脑发生了什么。

## Implemented

1. Yu API Adapter（src/yu/api，FastAPI，最薄的 Interface Layer）：
   GET /api/status、/api/today、/api/goals、/api/tasks、/api/memories、/api/memories/recent、
   /api/memory/stats、/api/system/status，POST /api/memories/query、POST /api/chat。
   Chat 经意图路由（规划 / 电脑状态 / 记忆对话）；system.status.read 经 Safety Kernel 评估。
   端点均为 async def，使 SQLite 访问保持在 lifespan 所在事件循环线程（不修改 Core 的 check_same_thread）。
2. apps/web（React 19 + TypeScript + Vite + framer-motion）：
   - / Life Cockpit：日期/问候、AI Core 状态机（idle/listening/thinking/remembering/answering/error）、
     「今天最重要的一件事」（真实 top_priority）、Memory/Today/System 概览、Ask Yu。
   - /memory Memory Universe：2D Canvas 星座（话题聚类、importance→大小、查询命中聚合、
     拖拽平移/滚轮缩放/点击详情、离开页面释放 RAF/监听器）。
3. Presentation / Demo 模式（?demo=true 或导航栏切换）：隐藏私人记忆内容，适合录屏。
4. prefers-reduced-motion 支持：动画/粒子自动降低或停止。

## Tests

pytest: 90 passed, 0 failed（84 项 Yu Core 回归 + 6 项 API Adapter 冒烟）

- 前端：tsc --noEmit 通过；vite build 通过（410 modules，产物 dist/index.html + assets，gzip 118.6 kB）
- 端到端：python -m yu.api 启动后，/api/status、/api/today、/api/memories、/api/memory/stats、
  /api/system/status（Safety Kernel → ALLOW）、/api/memories/query、/api/chat 均 200；
  GET / 与 /memory 返回 SPA index.html（单进程托管构建产物）

## Architecture（验收点）

- Frontend 不直接访问 SQLite / 内部 Python 文件 / 配置文件
- Frontend 不直接调用 DeepSeek（经 Yu Core -> LLM Provider -> DeepSeek）
- API 不绕过 Safety Kernel（system.status.read 仍经 kernel.evaluate，实测 ALLOW）
- Yu Core 不依赖 Web 才能运行（src/yu/api 是可选入口，CLI 不受影响）

## 验收命令（复现）

    pip install -e ".[dev,api]"
    pytest -q                                  # 90 passed
    python -m yu.api                           # http://127.0.0.1:8787
    cd apps/web && npm install && npm run dev  # http://localhost:5173（代理 /api）
    cd apps/web && npm run build               # 生产构建，之后 python -m yu.api 单进程托管

## Files Added

- src/yu/api/{__init__,app,context,schemas,__main__}.py
- tests/test_api.py
- apps/web/**（React + Vite 前端全部源码 + package-lock.json）

## Files Modified

- pyproject.toml（版本 0.0.7→0.0.8；新增 api 可选依赖 fastapi/uvicorn；dev 增 httpx）
- src/yu/__init__.py（版本号 0.0.8）
- .gitignore（新增 node_modules）
- DECISIONS.md（新增 D020、D021）
- README.md（新增 Yu Web 说明与运行方式）

## Known Issues / 已知限制

1. 真实对话（/api/chat 经 LLM）需要环境变量 DEEPSEEK_API_KEY；未设置时降级为本地只读回答。
2. 记忆检索为关键词（中文 bigram）匹配；demo 场景「为什么开始做你」需已有相关记忆才会命中节点。
3. pytest 会打印一条 starlette「httpx→httpx2」弃用告警（非阻塞，可忽略）。

## Next Recommendation

已建 feat/yu-web-v0.0.8 分支并提交。剩余为用户侧验收：设置 DEEPSEEK_API_KEY、浏览器视觉检查、
用 Demo 模式录制「宇，你还记得我们为什么开始做你吗？」场景，验收通过后再 Merge 到 master。
