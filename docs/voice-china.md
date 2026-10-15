# Yu 持续实时语音：中国大陆

## 选型（2026-09-08）

| 环节 | 当前实现 | 选择与限制 |
| --- | --- | --- |
| 语音识别 | qwen3-asr-flash-realtime，北京地域 | 16 kHz PCM 流式识别，服务端 VAD 自动断句；密钥只在后端 |
| 指令执行 | Yu 本地 ActionService | 最终识别自动串行提交，复用权限及审计链路；中间字幕不执行 |
| 普通对话 | 现有 DeepSeek Provider | 独立于语音服务，识别 Key 不代替对话 Key |
| 播报 | 浏览器本地中文音色 | 只选 localService 音色；缺少中文语音包时明确提示；音质取决于系统 |

阿里云北京与新加坡使用各自地域的 Key；当前默认北京，可用 YU_VOICE_REGION=singapore 显式切换。
该切换会改变语音发送地域，不按 IP 自动切换，不自动跨境重试。当前适配器未开放美国地域。
地域接口可用不等于所有国家的账号都可购买；海外部署前须核对账号资格、模型开通情况、当地条款和实测网络。

豆包语音具备独立识别、合成服务，适合后续同样本对比。首版选择千问是接入复杂度和现有链路的工程选择，
尚无真实麦克风 A/B 数据，不宣称千问音质或时延优于豆包。当前没有实现豆包适配器。
境外服务和浏览器在线 SpeechRecognition 不作为中国大陆默认依赖。

官方资料：
- [千问 ASR 协议、北京/新加坡地址与地区限制](https://help.aliyun.com/zh/model-studio/qwen-asr-api-reference)
- [实时 ASR WebSocket 与地域](https://help.aliyun.com/en/model-studio/qwen-asr-realtime-interaction-process)
- [自动断句配置](https://help.aliyun.com/en/model-studio/qwen-asr-realtime-client-events)
- [中间字幕与最终结果](https://help.aliyun.com/en/model-studio/qwen-asr-realtime-server-events)
- [百炼模型价格](https://help.aliyun.com/zh/model-studio/model-pricing)（按当前地域、模型实时核对，首版不承诺固定费用）
- [豆包语音产品](https://www.volcengine.com/products/Audio-editing-and-sound-processing)

## 本机运行

推荐双击 `start-voice.cmd`，它从 PATH 查找 PowerShell 7，并保留报错窗口。
也可以在已打开的 PowerShell 7 中进入 D:\田雨\Yu，运行 `./start-voice.ps1`。
脚本隐藏输入北京地域 API Key，密钥只进入当前进程环境，不写入文件。
本次启动显式开启 process.start，退出后恢复之前的环境变量。
访问 http://127.0.0.1:8792，点击“开始语音”并允许麦克风。出现“持续监听”后直接说话，
边说边显示字幕，句尾静音约 800 毫秒由云端断句并自动提交；这是断句阈值，不是端到端延迟承诺。
说完可继续下一句，无须点击、编辑或重新录音；执行中最多保留三句待处理指令。
点击或说“结束语音”停止收音并清空未执行队列；已发出的操作不能保证撤回，仍显示实际结果。
连接失败、过载、断线均结束监听，不自动重连或重发旧指令。一次最多 10 分钟，避免遗忘开启。
注意：监听期间包括静音在内的音频会持续发送至指定地域，按供应商规则计费；建议用耳机，避免音乐或旁人说话误触发。
本版不默认自动播报；监听时禁用“朗读回复”并停止正在进行的播报，防止自身回复被当作新指令。

## 验收状态

- 已实现：持续 PCM 采集、WebSocket 中转、流式字幕、自动断句、串行提交、句子编号去重、结束回收资源。
- 已验证：后端协议与非阻塞回归；浏览器资源生命周期与指令队列模拟测试。
- 待本机真实验证：Key 模型权限、麦克风实际采样、中文/中英混合识别、音乐环境误触发、端到端延迟。
- 未实现：唤醒词、浏览器关闭后常驻、可打断的全双工自动播报、云端 TTS。

音频只在内存处理，不在 Yu 落盘。云服务自身的数据保留规则以供应商服务条款为准。
验收语句建议：“打开QQ音乐”“打开Chrome”“打开下载文件夹”“打开我昨天那个项目”。
最后一句不应猜路径执行。尚未完成真人语音验收，不能把代码测试通过当作语音体验验收通过。

## QQ音乐真实控制（2026-09-08）

2026-10-08 更新：QQ音乐、微信开启 `auto_discover`，不再固定版本目录。
每次打开会在配置路径失效或未指定时，读取 Windows App Paths / 安装登记并验证启动文件存在。
升级后登记更新即可自动使用新路径，无需修改配置或重启 Yu。
未登记安装或存在多份有效安装时，需在 `config/windows_apps.yaml` 显式指定 `executable`；有效的指定路径优先。

支持“播放QQ音乐”“暂停”“播放下一首歌”“上一首”“打开QQ音乐并播放”。
“打开QQ音乐”本身只负责启动；组合指令分别检查打开权限和媒体权限。
start-voice.ps1 本次会话显式授予 media.control，其他启动方式需设置 YU_ALLOW_MEDIA_CONTROL=1。
新环境安装：`python -m pip install -e ".[api,media]"`。
使用 Windows GSMTC，仅匹配 QQMusic.exe 媒体会话；不发送全局媒体键，不误控浏览器。
播放/暂停需回读状态，切歌需回读歌名变化，接受请求但未验证变化返回 MEDIA_NOT_VERIFIED。
已在本机验证真实播放和下一首，以及 API → 权限 → 媒体控制的实际播放。
刚启动软件会等待媒体会话最多约八秒；仍未发布会话时明确提示未找到会话，不谎报成功。
暂不支持按歌名检索、指定歌单、登录、付费解锁；这些请求走本地不支持提示，不由 LLM 冒充执行。
# 2026-10-08：免点击 Windows 唤醒

现在 `start-voice.cmd` / PowerShell 7 的 `start-voice.ps1` 启动 API 和独立本地监听器，无需打开网页或点击“开始语音”。首次在 Windows 设置中允许桌面应用访问麦克风。

- 说“嘿，宇”，听到短提示音后说指令；“嘿，宇打开微信”不间断连说暂不保证完整接收。
- 说“结束”回到本地待唤醒；连续 30 秒无语音也会结束云端会话。执行/朗读不计闲置，单次对话仍最多 10 分钟。
- 待唤醒使用 Windows 中文本地引擎，不上传、不保存音频；唤醒后的识别仍是阿里云北京，按供应商计费，不自动重连或重发旧指令。
- 回复本地朗读，期间不会上传真实麦克风声音，首版不支持打断；无中文音色或播放失败时查看终端文字，不转付费 TTS。
- 页面手动语音保留，但与本地云端对话互斥；首阶段终端对话不自动同步进网页历史。
- Ctrl+C 完全停止本次监听和 API。重复启动会报错，不生成第二个监听器，也不会关闭微信等已打开应用。

本机已安装 sounddevice 0.5.6（cffi 2.1.1、pycparser 3.0），不需要下载唤醒模型。其他电脑需先安装 wake 可选依赖，并安装 Windows 中文语音识别功能：

```powershell
& .venv/Scripts/python.exe -m pip install '.[api,wake]'
& .venv/Scripts/python.exe -m yu.voice.wake --check
```

预检不开始录音、不连接云端。需改麦克风时调整 `config/voice_wake.yaml` 的 `device`；阈值为 Windows 固定语法置信度，不是专用 KWS 模型阈值。真人误唤醒率和音乐环境效果仍需验收。

