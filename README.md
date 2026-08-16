# Yu (宇)

Yu 是一个运行于 Windows PC 的长期个人决策助手，通过持续记忆用户的目标、任务、经历和决策，帮助用户规划生活、学习与工作，并能够读取基础计算机状态。

当前目标版本：**Yu v0.1.0**（开发中，当前处于 Memory Kernel 阶段）。

## 项目定位

本地优先（Local First）的长期个人决策助手，长期方向是逐步发展成为一个类似 JARVIS 的个人 AI 系统。

## 核心设计原则

- **Local First**：Memory / Events / Goals / Tasks / Decisions / Projects / Daily Logs 全部本地保存；模型可来自云端，但 Yu 的身份与长期数据不绑定任何单一模型供应商。
- **模型 ≠ Yu**：`Yu ≠ DeepSeek ≠ OpenAI ≠ 任何单一模型`。模型只是可替换的推理能力。
- **Memory First**：第一优先级永远是「记忆是否可靠」。
- **Small Steps**：按版本小步推进，每阶段：设计 → 开发 → 测试 → 体验 → 验收 → Git Commit。
- **AI 不负责自己宣布成功**：验收依据 = 实际运行结果 + pytest + 用户体验 + 开发状态报告。

## V0.1 DOES（必须实现）

- 长期保存用户记忆，程序重启后仍存在
- 与 LLM 连续对话
- 根据当前问题检索相关记忆
- 管理长期目标 / 任务 / 决策 / 项目基本信息
- 根据长期目标和当前状态生成每日计划，并生成 Daily Summary
- 查看 CPU、内存、磁盘、电池、进程等电脑状态，并基于状态给出建议
- 提供一个能够日常使用的 Windows 桌面界面

## V0.1 DOES NOT（明确不实现）

语音交互、手机 App、Web 多端同步、摄像头、实时屏幕视觉、自动控制鼠标键盘、自动删除文件、自动关闭程序、自动修改 Windows、多 Agent 系统、自主编程、自主修改 Yu 核心代码、自主进化、AGI、大型本地模型、复杂知识图谱、复杂 RAG、自建向量数据库、智能家居、3D Avatar、情绪识别。

> 若开发中发现上述方向有价值，记录到 `RESEARCH_BACKLOG.md`，不加入当前版本。

## 技术栈

Python · SQLite · pytest · psutil · PySide6 · Git · GitHub · LLM Provider 抽象。

暂不使用：LangChain、复杂 Agent 框架、Redis、PostgreSQL、大型 Vector DB、Kubernetes、Docker 微服务架构。

## 版本路线

`v0.0.0 Bootstrap → v0.0.1 Memory Kernel → v0.0.2 LLM Conversation → v0.0.2.1 Authority & Safety Kernel → v0.0.3 Memory Retrieval → v0.0.4 Goals/Tasks/Decisions/Projects → v0.0.5 Daily Planner → v0.0.6 Daily Summary → v0.0.7 Computer Context → v0.0.8 Desktop UI → Production Test → v0.1.0`

## 安全控制层（Authority & Safety Kernel）

Yu v0.0.2.1 建立独立于 LLM 的控制层（Control Plane）：Owner 身份、Safety Constitution、Permission（Default Deny）、Risk Engine、Audit Log（append-only）、Shutdown。

原则：能力增长不等于权限增长；LLM 只能提出 ProposedAction，不能直接获得执行权限。

配置：config/safety_constitution.yaml（安全宪法 SAFE-001~010）、config/owner.yaml（单一 Owner）。

## 运行

```bash
python -m yu.cli
```

本地命令：记住：/ 记忆 / 目标 / 任务 / 项目 / 决策 / 规划 / 总结 / 日报 / 电脑状态 / 权限 / 安全状态 / 审计 / 重置 / exit（或 关闭Yu）。对话功能需要设置环境变量 `DEEPSEEK_API_KEY`；可选 `DEEPSEEK_MODEL`（默认 deepseek-chat）、`DEEPSEEK_BASE_URL`、`YU_LLM_PROVIDER`（默认 deepseek）。对话时会自动检索相关长期记忆并注入上下文（v0.0.3）。可选 DEEPSEEK_TEMPERATURE（默认 0.3，越低越忠实于记忆、越少编造）。未设置 Key 时仅本地命令可用。

## Yu Web（v0.0.8 Web Experience）

Yu Web 是 Yu 的「身体」与交互入口（Interface Layer），不是另一个 Yu。两个页面：

- `/` Life Cockpit —— 今天最重要的一件事 + 概览 + Ask Yu（对话 / 规划 / 电脑状态）。
- `/memory` Memory Universe —— 长期记忆的可视化星座（2D Canvas：话题聚类 / 缩放 / 平移 / 选中）。

架构：Browser → Yu Web（React + Vite）→ HTTP → Yu API（FastAPI）→ Yu Core → LLM Provider → DeepSeek。
apps/web 只能通过 Yu API 使用 Yu 能力；Frontend 不直接调用 DeepSeek；API 不绕过 Safety Kernel。

运行（先安装 API 依赖）：

```bash
pip install -e ".[api]"     # 或 pip install fastapi uvicorn
python -m yu.api            # 启动 Yu API（默认 http://127.0.0.1:8787）
```

前端（开发）：

```bash
cd apps/web
npm install
npm run dev                 # http://localhost:5173（自动代理 /api）
```

前端（生产，单进程）：`npm run build` 后，`python -m yu.api` 会同时托管 API 与构建产物。

一键启动：双击仓库根目录的 `start.bat`（构建前端 + 启动后端 + 自动打开浏览器）；开发热更新用 `dev.bat`（后端 + Vite 两个窗口）。

演示 / 隐私：导航栏切换「Private / Demo」，或访问 `/?demo=true`（隐藏私人记忆内容，适合录屏）。

详见 `DEV_STATUS.md`（当前进度）、`DECISIONS.md`（架构决策）、`RESEARCH_BACKLOG.md`（未来方向）。
