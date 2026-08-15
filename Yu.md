\# Project Yu / 宇 — V0.1 开发计划



> \*\*项目名称：\*\* 宇

> \*\*英文名称：\*\* Yu

> \*\*当前目标版本：\*\* Yu v0.1.0

> \*\*开发平台：\*\* Windows PC

> \*\*主要开发方式：\*\* AI Coding Agent + 人工验收

> \*\*当前开发工具：\*\* DeepSeek V4 Pro

> \*\*项目定位：\*\* 长期个人决策助手



\---



\# 1. 项目目标



Yu 的长期方向，是逐步发展成为一个类似 JARVIS 的个人 AI 系统。



但 V0.1 不追求完整的 JARVIS，也不追求 AGI、自主进化、多 Agent 或复杂自动化。



V0.1 只解决一个核心问题：



> \*\*让 Yu 能够长期认识用户、记住过去、理解当前目标和任务，并基于这些长期信息帮助用户规划生活、学习和工作。\*\*



最终希望达到以下最小体验：



```text

用户

&#x20;↓

Yu

&#x20;↓

知道用户是谁

&#x20;↓

知道最近发生了什么

&#x20;↓

知道用户当前目标

&#x20;↓

知道有哪些任务没有完成

&#x20;↓

结合历史信息进行判断

&#x20;↓

给出今天最值得做的事情

```



同时，Yu 可以读取基础电脑状态，为用户提供电脑状态分析和优化建议。



\---



\# 2. V0.1 产品定义



Yu v0.1 是一个：



> \*\*运行于 Windows PC 的本地优先长期个人决策助手。\*\*



它应该具备以下核心能力：



```text

长期记忆

\+

持续对话

\+

目标管理

\+

任务管理

\+

决策记录

\+

每日规划

\+

每日总结

\+

基础电脑状态读取

```



\---



\# 3. V0.1 开发边界



\## 3.1 V0.1 必须实现



\* 长期保存用户记忆

\* 程序重启后记忆仍然存在

\* 与 LLM 进行连续对话

\* 根据当前问题检索相关记忆

\* 管理用户长期目标

\* 管理用户任务

\* 保存重要决策

\* 记录项目基本信息

\* 根据长期目标和当前状态生成每日计划

\* 生成 Daily Summary

\* 查看 CPU、内存、磁盘、电池、进程等电脑状态

\* 基于电脑状态给出建议

\* 提供一个能够日常使用的 Windows 桌面界面



\---



\## 3.2 V0.1 明确不实现



以下功能禁止在 V0.1 中提前加入：



\* 语音交互

\* 手机 App

\* Web 多端同步

\* 摄像头

\* 实时屏幕视觉

\* 自动控制鼠标键盘

\* 自动删除文件

\* 自动关闭程序

\* 自动修改 Windows

\* 多 Agent 系统

\* 自主编程

\* 自主修改 Yu 核心代码

\* 自主进化

\* AGI

\* 大型本地模型

\* 复杂知识图谱

\* 复杂 RAG

\* 自建向量数据库

\* 智能家居

\* 3D Avatar

\* 情绪识别



如果开发过程中发现这些方向有价值，应记录到：



```text

RESEARCH\_BACKLOG.md

```



而不是直接加入当前版本。



\---



\# 4. 核心设计原则



\## 4.1 Local First



Yu 的核心数据优先保存在本地。



包括：



\* Memory

\* Events

\* Goals

\* Tasks

\* Decisions

\* Projects

\* Daily Logs



模型可以来自云端，但 Yu 的身份和长期数据不能依赖某一个模型供应商。



\---



\## 4.2 模型不等于 Yu



设计上必须保持：



```text

Yu

≠

DeepSeek

≠

OpenAI

≠

任何单一模型

```



模型只是 Yu 当前使用的推理能力。



未来模型应该可以替换，而不影响 Yu 的记忆和身份连续性。



\---



\## 4.3 Memory First



V0.1 的第一优先级永远是：



> \*\*记忆是否可靠。\*\*



如果记忆系统不可靠，不允许通过增加更多功能来掩盖问题。



\---



\## 4.4 Small Steps



开发必须按版本推进。



禁止直接要求 AI：



> “把整个 Yu 做出来。”



每一个阶段：



```text

设计

&#x20;↓

开发

&#x20;↓

测试

&#x20;↓

实际体验

&#x20;↓

验收

&#x20;↓

Git Commit

&#x20;↓

下一阶段

```



\---



\## 4.5 AI 不负责自己宣布成功



DeepSeek 可以：



\* 开发

\* Debug

\* 写测试

\* 执行测试

\* 提出建议



但不能仅凭自己的判断宣布阶段完成。



最终验收依据：



```text

实际运行结果

\+

pytest

\+

用户体验

\+

开发状态报告

```



\---



\# 5. 初始技术栈



V0.1 优先保持简单。



建议：



```text

Language

Python



Database

SQLite



Testing

pytest



Computer Monitoring

psutil



Desktop UI

PySide6



Version Control

Git



Remote Repository

GitHub



LLM

Provider abstraction

```



暂时不使用：



```text

LangChain

复杂 Agent Framework

Redis

PostgreSQL

大型 Vector DB

Kubernetes

Docker 微服务架构

```



除非后续出现明确需求。



\---



\# 6. 初始项目结构



建议第一阶段保持：



```text

yu/

│

├── README.md

├── DEV\_STATUS.md

├── DECISIONS.md

├── RESEARCH\_BACKLOG.md

├── pyproject.toml

├── .gitignore

│

├── src/

│   └── yu/

│       ├── \_\_init\_\_.py

│       ├── cli.py

│       │

│       ├── memory/

│       │   ├── \_\_init\_\_.py

│       │   ├── models.py

│       │   └── store.py

│       │

│       └── ...

│

├── tests/

│

└── data/

&#x20;   └── .gitkeep

```



后续目录只允许根据已经出现的真实需求增加。



禁止为了“未来可能扩展”提前建立大量空模块。



\---



\# 7. 版本开发路线



\---



\# Phase 0 — Project Bootstrap



\## 版本



```text

Yu v0.0.0

```



\## 目标



建立一个：



> 可以正常运行、测试和版本管理的最小 Python 项目。



\## 实现内容



创建：



```text

README.md

DEV\_STATUS.md

DECISIONS.md

RESEARCH\_BACKLOG.md

pyproject.toml

.gitignore

src/yu/

tests/

data/

```



初始化：



```text

Git

Python environment

pytest

SQLite

```



\---



\## README 必须记录



项目目标：



> Yu v0.1 是一个运行于 Windows PC 的长期个人决策助手，通过持续记忆用户的目标、任务、经历和决策，帮助用户规划生活、学习与工作，并能够读取基础计算机状态。



同时明确：



```text

V0.1 DOES

```



和：



```text

V0.1 DOES NOT

```



\---



\## 验收条件



\* Python 项目能够正常安装或运行

\* `pytest` 可以正常启动

\* Git 仓库初始化完成

\* `.gitignore` 正确

\* data 中的私人数据库不会被提交到 GitHub

\* README 已记录项目边界



完成后进入：



```text

Yu v0.0.1

```



\---



\# Phase 1 — Memory Kernel



\## 版本



```text

Yu v0.0.1

```



\## 核心目标



> \*\*让 Yu 第一次拥有能够跨越程序生命周期而持续存在的记忆。\*\*



也就是：



```text

告诉 Yu 一件事

&#x20;↓

保存

&#x20;↓

关闭程序

&#x20;↓

重新启动

&#x20;↓

仍然能够找到

```



\---



\# 8. Memory Kernel 数据模型



第一版只设计两个核心对象：



```text

Event

Memory

```



\---



\## 8.1 Event



Event 表示：



> \*\*真正发生过的事情。\*\*



例如：



```text

用户说：

“记住，我正在开发 Yu。”

```



这是一个 Event。



Event 必须采用：



```text

Append Only

```



原则。



即：



```text

只能创建

不能修改历史 Event

不能覆盖历史 Event

```



如果未来发现过去信息错误，应新增新的 Correction Event。



不能直接修改历史。



\---



\## 8.2 Memory



Memory 表示：



> Yu 从经历中保存下来的有效信息。



例如：



```text

type:

fact



content:

用户正在开发 Yu 项目。



importance:

high

```



第一版 Memory 支持：



\* Create

\* Read

\* Archive



暂时不需要复杂生命周期机制。



\---



\# 9. Phase 1 CLI



第一版不开发 GUI。



使用 CLI：



```text

python -m yu.cli

```



启动：



```text

宇 Yu v0.0.1



>

```



支持最基本命令：



```text

记住：xxxx

```



例如：



```text

记住：我正在开发属于自己的 Yu。

```



返回：



```text

已记录。

Memory ID: xxx

```



查看：



```text

记忆

```



返回：



```text

\[1]

我正在开发属于自己的 Yu。

```



退出：



```text

exit

```



\---



\# 10. Phase 1 测试要求



必须实际测试：



\* 数据库首次启动自动创建

\* Event 可以写入

\* Memory 可以写入

\* Memory 可以读取

\* 多条 Memory 正确保存

\* 程序重新实例化后数据仍然存在

\* 程序关闭后重新打开数据仍然存在

\* Event 不允许直接 update

\* Archive Memory 不删除原始历史

\* 数据库异常拥有基本错误处理

\* 测试数据库和真实数据库隔离



必须实际运行：



```text

pytest

```



不能只生成测试文件而不执行。



\---



\# 11. Phase 1 验收标准



用户实际执行：



```text

记住：我正在开发 Yu。

```



关闭程序。



重新启动。



输入：



```text

记忆

```



仍然能够看到：



```text

我正在开发 Yu。

```



则 Persistence 基础验收通过。



\---



\# Phase 2 — LLM Conversation



\## 版本



```text

Yu v0.0.2

```



\## 目标



为 Yu 接入第一颗可以替换的“大脑”。



流程：



```text

User

&#x20;↓

Yu Core

&#x20;↓

LLM Provider

&#x20;↓

DeepSeek

&#x20;↓

Response

```



\---



\# 12. LLM Provider 设计



禁止把 DeepSeek API 写死在业务逻辑中。



必须存在类似：



```text

LLMProvider

```



抽象。



未来允许：



```text

DeepSeekProvider

OpenAIProvider

OtherProvider

LocalProvider

```



业务层只能依赖统一接口。



原则：



> 模型可以替换，Yu 不随模型一起更换。



\---



\# 13. Phase 2 功能



实现：



\* 用户输入

\* LLM 请求

\* LLM 返回

\* 多轮当前对话

\* 基础错误处理

\* API Key 使用环境变量

\* Provider 可替换



当前阶段：



> Memory 不需要自动影响回答。



先验证 Conversation 层。



\---



\# Phase 3 — Memory Retrieval



\## 版本



```text

Yu v0.0.3

```



\## 核心目标



让：



> \*\*过去第一次能够影响现在。\*\*



流程：



```text

Current Question

&#x20;↓

Memory Retrieval

&#x20;↓

Relevant Memories

&#x20;↓

Context Builder

&#x20;↓

LLM

&#x20;↓

Answer

```



\---



\# 14. 第一版 Retrieval



暂时不要上复杂 Vector DB。



可以先使用：



```text

关键词

\+

Memory Type

\+

时间

\+

Importance

```



实现简单排序。



以后有真实数据以后，再判断是否增加 embedding。



\---



\# 15. Phase 3 验收场景



此前保存：



```text

用户希望长期向 AI 相关职业方向发展。

```



几天以后询问：



```text

宇，我以后想往什么方向发展？

```



Yu 应该能够检索相关 Memory，并明确基于过去信息回答。



不能要求用户重新解释背景。



\---



\# Phase 4 — Goals / Tasks / Decisions / Projects



\## 版本



```text

Yu v0.0.4

```



\## 目标



将重要长期状态从普通 Memory 中结构化。



增加：



```text

Goal

Task

Decision

Project

```



\---



\# 16. Goal



记录：



> 用户长期或阶段性希望达到什么。



例如：



```text

学习 AI

进入 AI 相关行业

完成 Yu V0.1

```



\---



\# 17. Task



记录：



> 需要完成的具体行动。



建议包含：



```text

title

status

priority

created\_at

due\_date

related\_goal

related\_project

```



第一版保持简单。



\---



\# 18. Decision



保存：



```text

做了什么决定

为什么这样决定

有什么约束

有哪些替代方案

```



例如：



```text

Decision:

Yu V0.1 暂时只开发 Windows PC。



Reason:

减少开发成本和复杂度。

```



\---



\# 19. Project



记录用户当前真实项目。



例如：



```text

Yu

Creative OS

其他长期项目

```



第一版只保留：



```text

name

status

current\_goal

next\_step

notes

```



\---



\# Phase 5 — Daily Planner



\## 版本



```text

Yu v0.0.5

```



\## 核心目标



> \*\*让 Yu 第一次真正参与用户每天的决策。\*\*



用户：



```text

宇，我今天应该干什么？

```



Yu 读取：



```text

Goals

\+

Tasks

\+

Projects

\+

Recent Memories

\+

Yesterday Status

\+

Available Time

```



生成：



```text

今天最重要的一件事

第二优先级

可选任务

今天不要做什么

原因

```



\---



\# 20. Planner 原则



Daily Planner 不是：



```text

Todo Generator

```



而是：



```text

Priority Decision System

```



必须尽可能回答：



> 为什么今天应该做这件事？



基础原则：



1\. 优先完成，而不是不断开启新项目。

2\. 每天最多 3 个核心任务。

3\. 核心任务必须现实可完成。

4\. 长期目标优先于短期冲动。

5\. 已经长期拖延的任务需要显式处理。

6\. 必须说明安排理由。

7\. 可以明确告诉用户“今天不要做什么”。



\---



\# Phase 6 — Daily Summary



\## 版本



```text

Yu v0.0.6

```



\## 目标



让 Yu 每一天都有一个清晰的状态快照。



格式类似：



```text

Date:

2026-08-15



今日计划：

\- ...



实际完成：

\- ...



未完成：

\- ...



新增记忆：

\- ...



重要决策：

\- ...



遇到的问题：

\- ...



当前项目状态：

\- ...



明天建议：

\- ...

```



\---



\# 21. Daily Summary 作用



第二天启动时：



```text

Yesterday Summary

\+

Long-term Memory

\+

Current Tasks

\+

Goals

```



能够快速恢复当前 Context。



Daily Summary 不是原始 Event 的替代。



原始事件仍然永久保留。



\---



\# Phase 7 — Computer Context



\## 版本



```text

Yu v0.0.7

```



\## 核心目标



让 Yu 第一次拥有有限的：



> \*\*环境感知能力。\*\*



当前只允许读取。



禁止操作。



\---



\# 22. 第一版电脑状态



通过系统接口或 `psutil` 获取：



```text

CPU Usage

RAM Usage

Disk Usage

Disk Free

Battery

System Uptime

Network

Running Processes

```



可以适当记录占用较高的程序。



\---



\# 23. 使用场景



用户：



```text

宇，我电脑现在为什么这么卡？

```



Yu：



```text

获取系统状态

&#x20;↓

整理结构化数据

&#x20;↓

LLM 分析

&#x20;↓

给出原因

&#x20;↓

提供建议

```



例如：



```text

当前 CPU 正常，但内存占用达到 86%。



Chrome 当前占用约 4GB，

VS Code 占用约 1.4GB。



系统盘剩余空间较低。



建议优先处理内存和系统盘空间。

```



\---



\# 24. 当前禁止行为



Yu v0.0.7 禁止自动：



\* 删除文件

\* 清理注册表

\* 关闭软件

\* 修改系统配置

\* 安装软件

\* 卸载软件

\* 修改启动项

\* 操作鼠标键盘



当前只有：



```text

Read

Analyze

Recommend

```



\---



\# Phase 8 — Desktop UI



\## 版本



```text

Yu v0.0.8

```



\## 目标



让 Yu 从开发工具变成：



> \*\*用户愿意每天打开的程序。\*\*



建议使用：



```text

PySide6

```



第一版只需要简单界面。



例如：



```text

┌──────────────────────────────┐

│ 宇 Yu                        │

│ CPU 18% | RAM 63%            │

├──────────────────────────────┤

│                              │

│        Conversation          │

│                              │

│                              │

├──────────────────────────────┤

│ 输入消息...                  │

└──────────────────────────────┘

```



\---



\# 25. 第一版 UI 原则



优先：



\* 快

\* 稳定

\* 清楚

\* 不影响电脑性能

\* 能快速打开

\* 能快速关闭



不优先：



\* 动画

\* 3D

\* Avatar

\* 科幻视觉效果

\* 大量 Dashboard

\* 极复杂设计系统



\---



\# Phase 9 — Production Usage Test



\## 目标版本



```text

Yu v0.1.0

```



完成 v0.0.8 后：



> 暂停开发新能力。



进入真实使用测试。



建议：



```text

7～14 天

```



至少覆盖：



\* 每日计划

\* Daily Summary

\* 多次 Memory 保存

\* 多日 Memory Retrieval

\* Goals

\* Tasks

\* Projects

\* 电脑状态

\* 日常闲聊



\---



\# 26. Production Test 核心观察指标



重点观察：



\## Memory



\* 会不会忘记重要信息？

\* 会不会记录错误信息？

\* 会不会重复记录？

\* 旧信息是否能正确更新？

\* 是否能找到真正相关的 Memory？



\## Context



\* 是否经常需要用户重新解释背景？

\* 是否能够知道用户最近在做什么？



\## Planner



\* 每日建议是否真正有价值？

\* 是否过度生成任务？

\* 是否符合真实可用时间？

\* 是否能够阻止无价值的新项目扩张？



\## Experience



\* 是否愿意每天打开 Yu？

\* 是否感觉它越来越了解用户？

\* 哪些操作最麻烦？

\* 哪些功能实际上没人使用？



\---



\# 27. Yu v0.1.0 成功标准



满足以下条件，可以认为 Yu V0.1 成立：



\### 1. Persistent Memory



今天告诉 Yu 的重要信息，几天后仍然存在。



\### 2. Useful Retrieval



Yu 能够在适当的时候重新找到这些信息。



\### 3. Context Continuity



用户不需要每天重新解释：



> “我现在在干什么。”



\### 4. Useful Planning



用户愿意定期问：



> “宇，我今天应该干什么？”



并认为答案具有现实价值。



\### 5. Model Independence



更换 LLM Provider 后：



> Yu 仍然认识用户。



\### 6. Stable Local Data



程序升级、模型切换和电脑重启不会导致主要长期数据丢失。



\---



\# 28. 开发交接机制



为了保证 DeepSeek、Codex、Claude Code 或未来其他开发工具之间能够无缝切换，每一个开发阶段完成后必须更新：



```text

DEV\_STATUS.md

```



\---



\# 29. DEV\_STATUS.md 模板



```markdown

\# Yu Development Status



\## Version



Yu v0.0.x



\## Current Phase



当前开发阶段。



\## Status



PASS / PARTIAL / FAIL



\## Original Goal



本次原本准备实现什么。



\## Implemented



1\.

2\.

3\.



\## Actual Behavior



真实运行效果。



\### Example



Input:



> 记住：我正在开发 Yu



Output:



> 已记录。



重新启动程序。



Input:



> 记忆



Output:



> 我正在开发 Yu。



\## Tests



pytest:



XX passed

XX failed



失败项目：



\- ...



\## Files Added



\- xxx.py



\## Files Modified



\- xxx.py



\## Files Deleted



\- xxx.py



\## Database Changes



新增：



\- xxx table

\- xxx field



如果没有：



无。



\## Architecture Deviations



说明实际实现是否与原设计不同。



例如：



原设计：

SQLite



实际：

SQLite + Redis



Reason:

...



\## Known Issues



1\.

2\.

3\.



\## User Experience



由实际使用者填写：



\- 是否能正常使用

\- 是否慢

\- 是否麻烦

\- 是否符合预期

\- 是否感觉自然

\- 是否存在明显问题



\## Next Recommendation



开发工具认为下一步应该做什么。



注意：



这里只是建议。



不得自动开始下一阶段。

```



\---



\# 30. DECISIONS.md



所有重要架构决策必须保存。



格式建议：



```markdown

\# Architecture Decisions



\## D001 — Python



Decision:



Yu V0.1 使用 Python。



Reason:



开发成本低，Windows 支持良好，AI Coding 工具支持成熟。



\---



\## D002 — SQLite



Decision:



Yu V0.1 使用 SQLite。



Reason:



单用户、本地优先，不需要独立数据库服务器。



\---



\## D003 — Event Append Only



Decision:



原始 Event 不允许直接修改。



Reason:



保证历史事件完整，为未来长期记忆和身份连续性保留真实历史。

```



开发工具不能随意推翻已经确定的 Decision。



如果认为需要修改：



必须新增 Decision。



例如：



```text

D017 supersedes D003

```



并说明原因。



\---



\# 31. RESEARCH\_BACKLOG.md



所有超出 V0.1 的想法统一记录。



例如：



```markdown

\# Yu Research Backlog



\## R001 — Voice



未来研究实时语音交互。



Status:

Backlog



\---



\## R002 — Screen Understanding



按需获取屏幕截图，并通过视觉模型理解当前界面。



Status:

Backlog



\---



\## R003 — Computer Control



研究安全的 Computer Use。



Status:

Backlog



\---



\## R004 — Continuous Learning



研究 Memory → Reflection → Strategy Update 的长期学习闭环。



Status:

Research



\---



\## R005 — AGI Minimum Loop



研究最小可验证 AGI 正向循环。



Status:

Long-term Research

```



原则：



> \*\*思想允许向上扩展，开发必须严格控制当前版本。\*\*



\---



\# 32. DeepSeek 开发规则



DeepSeek V4 Pro 当前负责：



```text

Implementation

Testing

Debugging

Code Analysis

```



必须遵循：



1\. 一次只开发当前阶段。

2\. 不得自动继续下一阶段。

3\. 不得未经说明增加重大依赖。

4\. 不得为了“未来扩展”提前创建大量架构。

5\. 不得改变项目核心设计而不记录。

6\. 必须实际运行测试。

7\. 必须报告测试真实结果。

8\. 必须更新 DEV\_STATUS.md。

9\. 必须记录数据库 Schema 变化。

10\. 必须报告新增、修改、删除的文件。

11\. 必须报告与原计划不一致的实现。

12\. 遇到问题优先修复当前阶段，而不是绕过问题开发下一功能。



\---



\# 33. 每个阶段的统一开发流程



```text

读取 README

&#x20;↓

读取 DECISIONS

&#x20;↓

读取 DEV\_STATUS

&#x20;↓

确认当前 Phase

&#x20;↓

分析当前代码

&#x20;↓

实现当前任务

&#x20;↓

写测试

&#x20;↓

运行测试

&#x20;↓

修复失败

&#x20;↓

重新测试

&#x20;↓

更新 DEV\_STATUS

&#x20;↓

停止

```



开发工具不得在完成后自动进入下一 Phase。



\---



\# 34. 用户向架构审查方反馈的内容



每次阶段开发完成以后，应提供：



```text

DEV\_STATUS.md

\+

pytest 实际结果

\+

真实运行输入/输出

\+

自己的实际体验

```



如果出现 Bug，再提供：



```text

完整报错

\+

触发步骤

```



如果涉及 UI，则增加：



```text

Screenshot

```



如果架构变得复杂，可以直接提供：



```text

项目源码

或

项目压缩包

```



用于源码级审查。



\---



\# 35. 开发工具分工



当前建议：



```text

用户

│

├── 最终决策

├── 实际使用

└── 产品反馈



ChatGPT

│

├── Architecture

├── Planning

├── Review

├── Memory Design

└── Acceptance



DeepSeek V4 Pro

│

├── Coding

├── Testing

├── Debugging

└── Implementation



Git / GitHub

│

├── Version History

├── Commit

├── Branch

├── Tag

└── Rollback

```



\---



\# 36. 第一阶段立即执行内容



当前不要把整份计划直接作为“一次完成全部功能”的开发任务。



DeepSeek 第一轮只允许执行：



```text

Phase 0

\+

Phase 1

```



也就是：



\# Yu v0.0.1 — Memory Kernel



\---



\# 37. 第一轮开发任务



目标：



> 实现一个最小、可靠、持久化的 Yu Memory Kernel。



技术要求：



```text

Python

SQLite

pytest

Git

```



实现：



\* Event

\* Memory

\* SQLite persistence

\* Append-only Event

\* 基础 CLI

\* `记住：xxx`

\* `记忆`

\* `exit`



必须实际测试：



\* 数据库创建

\* Event 写入

\* Memory 写入

\* Memory 读取

\* 重启持久化

\* Event 不可修改

\* 错误处理

\* 测试环境隔离



禁止：



\* LLM

\* Agent

\* GUI

\* Web

\* FastAPI

\* Vector DB

\* LangChain

\* RAG

\* Knowledge Graph

\* Voice

\* Computer Control

\* AGI

\* Self Evolution



开发结束后：



```text

运行完整 pytest

&#x20;↓

更新 DEV\_STATUS.md

&#x20;↓

报告文件变化

&#x20;↓

报告数据库变化

&#x20;↓

报告架构偏差

&#x20;↓

停止开发

```



不得进入 Phase 2。



\---



\# 38. Yu 当前版本路线



```text

Yu v0.0.0

Project Bootstrap



↓



Yu v0.0.1

Memory Kernel



↓



Yu v0.0.2

LLM Conversation



↓



Yu v0.0.3

Memory Retrieval



↓



Yu v0.0.4

Goals / Tasks / Decisions / Projects



↓



Yu v0.0.5

Daily Planner



↓



Yu v0.0.6

Daily Summary



↓



Yu v0.0.7

Computer Context



↓



Yu v0.0.8

Desktop UI



↓



Production Test



↓



Yu v0.1.0

First Usable Yu

```



\---



\# 39. 项目当前最高原则



Yu 的 V0.1 不追求：



> 做一个看起来很厉害的 AI Demo。



而追求：



> \*\*做一个用户真正愿意每天使用，并且随着时间推移越来越了解用户的个人 AI。\*\*



第一阶段真正需要证明的不是：



```text

Yu 有多聪明

```



而是：



```text

Yu 能不能拥有昨天。

```



当：



```text

程序关闭

↓

重新启动

↓

过去仍然存在

```



Yu 才第一次真正拥有连续性。



而当：



```text

过去的经历

↓

能够在正确的时候被重新找到

↓

影响今天的判断

```



Yu 才开始从一个普通 AI 客户端，逐渐成为真正属于一个人的长期个人智能系统。



