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

`v0.0.0 Bootstrap → v0.0.1 Memory Kernel → v0.0.2 LLM Conversation → v0.0.3 Memory Retrieval → v0.0.4 Goals/Tasks/Decisions/Projects → v0.0.5 Daily Planner → v0.0.6 Daily Summary → v0.0.7 Computer Context → v0.0.8 Desktop UI → Production Test → v0.1.0`

## 运行

```bash
python -m yu.cli
```

详见 `DEV_STATUS.md`（当前进度）、`DECISIONS.md`（架构决策）、`RESEARCH_BACKLOG.md`（未来方向）。
