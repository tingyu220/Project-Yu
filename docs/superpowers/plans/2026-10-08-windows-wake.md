# Windows 免点击语音唤醒实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans（当前会话执行）或 superpowers:subagent-driven-development（分任务执行）；按下面复选框逐项推进。

**Goal:** 启动 Yu 后无需网页和按钮即可说“嘿，宇”唤醒，对话结束后自动回到本地待唤醒。

**Architecture:** 独立本地语音进程拥有麦克风，以本地关键词模型检测唤醒；只在唤醒后通过既有本机 WebSocket 使用阿里云实时识别，通过 `/api/chat` 执行已授权动作。启动入口协调 API 与语音进程，网页不参与监听生命周期。

**Tech Stack:** Python 3.12（本机既有环境）、sherpa-onnx、sounddevice、numpy、websockets 15、Windows SAPI 本地朗读、PowerShell 7。

**Spec:** `docs/superpowers/specs/2026-10-08-windows-wake-design.md`（用户已批准）。

**批准后的调整：** 用户批准将任务 1 的 sherpa-onnx 模型替换成 Windows System.Speech 固定中文语法；不下载模型、不装 numpy。新增 `native-wake.ps1` 和 `PcmPipeStream.cs` 为检测器实现，`AudioCapture`/`KeywordDetector` 接口保持不变。任务 5 的进程协调实现位于 Python `launcher.py`，PowerShell 入口调用它，避免多套子进程生命周期逻辑。执行记录见 `.superpowers/sdd/2026-10-08-windows-wake/progress.md`，未自动提交。

## Global Constraints

- 待唤醒不上传音频、不连接付费识别服务、不保存录音；默认关键词“嘿，宇”。
- 单声道 16 kHz PCM16；ready 前不上传；朗读期间丢弃输入，不支持语音打断。
- 连续闲置 30 秒结束对话；单次最长 600 秒；执行和朗读不计入闲置时间。
- 不自动重连、不重发动作；结束取消未执行队列，已执行动作保留真实回执。
- 首阶段不做托盘、开机自启、EXE、手机、网页历史同步或识别供应商替换。
- 保留原网页语音功能及单会话锁；本地客户端不放宽 Origin 检查、不获取服务端 Key。
- 不覆盖用户已有修改和 `.env`；不打印密钥。Commit/Push 必须另行征求用户确认，本计划不自动提交。
- 命令使用动态解析的 PowerShell 7；代码和文档编辑使用 apply_patch；代码注释中文。

## Review Focus

1. 麦克风不支持 16 kHz 或热拔插：明确报错并释放资源，不假装待唤醒（任务 1、4）。
2. 浏览器正在语音对话：本地唤醒提示忙且不提交指令，不抢锁（任务 3）。
3. 慢网络和麦克风队列溢出：取消会话，不积压和重放音频（任务 1、3）。
4. 结束指令与正在执行动作交错：未执行队列清空，已发生效果记录回执（任务 2、3）。
5. Windows 没有中文音色或朗读失败：显示文本并提示，继续可用，不切换云端 TTS（任务 4）。

## 文件与接口边界

新增 `src/yu/voice/wake/` 包，配置、采集、检测、状态、传输、反馈、运行入口分别独立。修改启动脚本而不改动作业务层；测试只替代麦克风、网络、时钟和音频输出边界。既有实时识别协议和授权执行链路继续复用。

### 任务 1：本地采集与关键词检测

**Files:** 新增 `config/voice_wake.yaml`、`src/yu/voice/wake/{__init__,config,capture,detector}.py`、`tests/test_wake_capture.py`、`tests/test_wake_detector.py`；修改 `pyproject.toml`（新增可选 wake 依赖）、`.gitignore`（仅新增专用模型目录忽略规则）。

**Interfaces:** `WakeConfig.load(path: Path) -> WakeConfig`；`AudioCapture(config)` 作为上下文管理器，`read(timeout: float) -> bytes`；`KeywordDetector(config)` 提供 `accept(pcm: bytes) -> bool`、`reset() -> None`。配置默认 sample_rate=16000、channels=1、frame_ms=100、queue_frames=20、idle_seconds=30、max_session_seconds=600、cooldown_seconds=1；不接受任意网络服务地址。

- [ ] 编写失败测试：未检测到关键词时 `accept` 返回 False；一次命中后 reset 才允许下一次；非偶数 PCM 拒绝；队列超过 20 帧报错；退出采集上下文关闭输入流；非法采样率配置报错。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_wake_capture.py tests/test_wake_detector.py -v`，确认预期失败。
- [ ] 核对官方中文 KWS `sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01` 的资产大小、模型许可证和 API 示例；记录来源与完整性校验信息。缺少许可证或无法校验则先报告，不盲目下载。核对兼容 Python 3.12 的依赖版本，再安装至现有虚拟环境并记录实际版本；不更改原 API 依赖版本。
- [ ] 实现配置校验、sounddevice 输入、有界队列和 sherpa-onnx 检测。录音回调不进行解码、网络、磁盘写入；使用模型对应的官方 tokenizer 生成“嘿，宇”关键词，不手写猜测 token。
- [ ] 重跑任务测试；列出设备但不开始常驻采集。模型仅在执行阶段下载到专用被忽略目录，不写入 Git。

### 任务 2：唤醒会话状态机

**Files:** 新增 `src/yu/voice/wake/state.py`、`tests/test_wake_state.py`。

**Interfaces:** `WakeState` 为 WAITING、CONNECTING、LISTENING、BUSY、STOPPED；`WakeController(config, clock)` 提供 `wake() -> bool`、`ready() -> None`、`speech() -> None`、`set_busy(value: bool) -> None`、`final(item_id: str, text: str) -> str | None`、`expired() -> bool`、`end() -> None`、`stop() -> None`。返回 None 表示重复、结束命令或当前状态不接受指令；协调器检查状态决定关闭会话。结束回 WAITING，stop 为彻底退出。

- [ ] 编写失败测试：WAITING 不接收指令；连续两次 wake 只接受一次；ready 后才 LISTENING；同 id 不重复提交；“OK，结束。”返回 WAITING，“结束会议”不是结束；30 秒闲置和 600 秒会话边界；BUSY 不累计闲置但仍受 600 秒上限；end 清空本次去重数据并进入 1 秒冷却。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_wake_state.py -v`，确认失败。
- [ ] 实现纯状态逻辑和 Python 整句结束匹配，与现有 TypeScript 命令语义一致。时钟由外部传入，测试不用真实 sleep。
- [ ] 重跑状态测试，检查结束后可以再唤醒，不以永久关闭采集替代结束对话。

### 任务 3：复用实时识别和动作链路

**Files:** 新增 `src/yu/voice/wake/session.py`、`tests/test_wake_session.py`；不修改原 `src/yu/api/voice_live.py` 的锁和来源权限。

**Interfaces:** `VoiceSession(base_url: str)` 仅允许明确的 loopback 8792 服务；`run(capture: AudioCapture, controller: WakeController, feedback: Feedback) -> None` 在一次唤醒周期内运行，结束必关闭连接；`submit(text: str, history: list[dict[str, str]]) -> dict` 使用 ChatRequest 既有 `message/history` 结构。网络传输与控制逻辑分开，便于测试。

- [ ] 编写失败测试：没有 wake 时零网络连接；WS ready 前零音频上传；provider error、网页占锁、断连和帧溢出都取消本次会话；重复 final 一次提交；三个等待指令为队列上限；结束清掉尚未提交指令；HTTP/业务失败取消积压指令；已执行动作回执仍展示，不重发。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_wake_session.py -v`，确认失败。
- [ ] 实现本机 WS 客户端，Origin 与同一 base_url 一致，100 ms PCM 帧在 ready 后发送；连接超时 12 秒，关闭超时 2 秒。循环同时监控读音频、识别事件、串行动作和超时，任一失败取消其他任务并释放资源；不自动重连。
- [ ] 实现最多 20 条 user/assistant history，只有实际 API 回复加入 assistant；partial 仅打印字幕，final 才执行。超时检查覆盖握手和 BUSY 状态；停止命令在接收 final 时立即生效，不等待动作队列排到它。
- [ ] 重跑任务测试，并运行原 `tests/test_voice_live.py`、`tests/test_voice_nonblocking.py`，确保网页语音和权限链路未回归。

### 任务 4：本地反馈与独立入口

**Files:** 新增 `src/yu/voice/wake/feedback.py`、`src/yu/voice/wake/__main__.py`、`tests/test_wake_runtime.py`。

**Interfaces:** `Feedback.cue() -> None`、`Feedback.speak(text: str) -> None` 在线程中同步执行；`run_wake(config_path: Path, base_url: str) -> None` 拥有检测和会话生命周期。Windows 本地朗读通过 PowerShell 7 调用系统 SAPI，输入走 stdin，不拼接用户文本为 shell 命令，不增加付费 TTS 依赖。

- [ ] 编写失败测试：启动后自动 WAITING，无网页按钮；唤醒提示音期间不上传；朗读期间输入丢弃；朗读失败回到可监听状态；无中文音色仅展示文本和提示；麦克风断开进入 STOPPED；Ctrl+C 关闭所有资源；缺失模型不能显示待唤醒。
- [ ] 运行 `.venv/Scripts/python.exe -m pytest tests/test_wake_runtime.py -v`，确认失败。
- [ ] 实现启动预检、关键词检测循环、提示音、本地朗读和中文状态输出。检测与识别共用一个采集流；结束后清空采集积压帧、重置检测流，再待唤醒。朗读期间丢弃帧，结束后 1 秒冷却；所有进程调用 shell=False，朗读失败不启用云端替代。
- [ ] 重跑测试；通过 `python -m yu.voice.wake --check` 检查模型、设备、依赖而不常驻录音、不产生 API 费用。

### 任务 5：单入口启动和实际验收

**Files:** 修改 `start-voice.ps1`、`docs/voice-china.md`、`DEV_STATUS.md`；新增 `tests/test_wake_launcher.py`（脚本运行行为测试）；已有 `start-voice.cmd` 保持兼容。

**Interfaces:** 启动脚本成功时管理本次 API 和 wake 子进程；API 8792 已占用则明确报告且不自动附着不明服务。使用本机命名互斥保护本地语音入口，不创建多个监听器。

- [ ] 编写脚本边界失败测试：第二次启动不创建监听器；缺模型/设备时在启动采集前失败；任一子进程退出时清理本次拥有的另一子进程；Ctrl+C 不终止不属于本次启动的进程；已有 `.env` 不改写、不打印。
- [ ] 用 PowerShell 7 运行脚本测试并确认预期失败，再实现协调逻辑。保留原 Key 读取方式；替换“点击开始语音”提示为待唤醒说明，不再要求网页参与。
- [ ] 运行全部 `.venv/Scripts/python.exe -m pytest`，记录真实结果和既有警告；若前端没有改动，不重复构建前端。
- [ ] 启动后请用户真人测试：关闭网页 → “嘿，宇” → 提示音 → “打开微信” → 确认恢复现有窗口而非登录实例 → “结束” → 再次唤醒。检查结束后供应商连接关闭。
- [ ] 补测播放音乐时误唤醒、普通对话、连续唤醒、耳机/扬声器、网络中断与麦克风断开。记录误唤醒次数和唤醒响应延迟；没有真人证据不能宣布体验验收完成。
- [ ] 更新 DONE/CURRENT/TODO；未解决问题明确列为部分完成。提交或推送仅在用户单独确认后执行。

## 计划自检

目标、隐私、闲置和结束由任务 1—3 覆盖；反馈和无网页运行由任务 4 覆盖；启动互斥和退出清理由任务 5 覆盖。五项 Review Focus 均有对应测试；边界命名和接口在各任务中一致。当前未安装依赖、下载模型、开始监听或修改启动脚本。

## 执行选择

推荐当前会话按任务执行：各模块接口紧密相连，便于沿用现有链路，降低重复上下文和费用。也可选择分任务子代理执行；以实际可用调度能力为准，不默认升级模型。计划待用户审阅并选择执行方式后实施。
