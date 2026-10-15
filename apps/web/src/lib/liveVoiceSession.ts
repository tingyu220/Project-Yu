/** 浏览器资源生命周期；停止立即丢弃迟到的授权、字幕和最终识别事件。 */
export type LiveEvent = { type: "ready" | "speech" | "partial" | "final" | "error"; id?: string; text?: string; message?: string };

export class LiveVoiceSession {
  private active = true;
  private socket?: WebSocket;
  private stream?: MediaStream;
  private context?: AudioContext;
  private node?: AudioWorkletNode;
  private timer?: ReturnType<typeof setTimeout>;

  constructor(private onEvent: (event: LiveEvent) => void, private onError: (message: string) => void) {}

  async start(): Promise<void> {
    try {
      this.context = new AudioContext({sampleRate: 16000});
      await this.context.resume();
      if (!this.active) return;
      if (this.context.sampleRate !== 16000) throw new Error("当前浏览器不支持 16 kHz 实时音频，请使用新版 Chrome 或 Edge。");
      this.timer = setTimeout(() => this.fail("麦克风授权或连接超时，请重新开启。"), 30000);
      const stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}});
      if (!this.active) { stream.getTracks().forEach(track => track.stop()); return; }
      this.stream = stream;
      stream.getAudioTracks().forEach(track => track.addEventListener("ended", () => this.fail("麦克风已断开，请重新开启。")));
      await this.context.audioWorklet.addModule("/voice-capture.js");
      if (!this.active) return;
      const socket = new WebSocket(`${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/voice/live`);
      this.socket = socket;
      socket.onmessage = event => {
        if (!this.active) return;
        try {
          const data = JSON.parse(event.data) as LiveEvent;
          if (data.type === "error") { this.fail(data.message || "实时识别失败。"); return; }
          if (data.type === "ready") {
            if (this.node) return;
            clearTimeout(this.timer);
            this.timer = setTimeout(() => this.fail("本次语音已满 10 分钟，请重新开启。"), 600000);
            const node = new AudioWorkletNode(this.context!, "voice-capture");
            this.node = node;
            node.onprocessorerror = () => this.fail("音频处理失败，请重新开启。");
            node.port.onmessage = audio => {
              if (!this.active || socket.readyState !== WebSocket.OPEN) return;
              if (socket.bufferedAmount > 64000) { this.fail("网络发送拥堵，已停止监听，不会重发旧指令。"); return; }
              socket.send(audio.data);
            };
            this.context!.createMediaStreamSource(stream).connect(node);
            // 处理器输出静音，让音频图持续工作且不将麦克风回放到扬声器。
            node.connect(this.context!.destination);
          }
          this.onEvent(data);
        } catch { this.fail("实时语音数据异常，请重新开启。"); }
      };
      socket.onerror = () => this.fail("无法连接实时语音服务，请检查启动窗口和网络。");
      socket.onclose = () => this.fail("语音连接已结束，请重新开启；不会重发旧指令。");
    } catch (error) {
      this.fail(error instanceof Error && error.name === "NotAllowedError" ? "麦克风权限被拒绝，请在浏览器中允许后重试。" : error instanceof Error ? error.message : "无法开启麦克风。");
    }
  }

  stop(): void {
    this.active = false;
    clearTimeout(this.timer);
    this.node?.disconnect();
    this.node?.port.close();
    this.stream?.getTracks().forEach(track => track.stop());
    if (this.context && this.context.state !== "closed") void this.context.close().catch(() => {});
    if (this.socket) {
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      this.socket.close();
    }
  }

  private fail(message: string): void {
    if (!this.active) return;
    this.stop();
    this.onError(message);
  }
}
