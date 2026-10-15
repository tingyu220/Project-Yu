import { useState } from "react";
import type { LiveVoice } from "../lib/useLiveVoice";

interface ComposerProps {
  onSubmit: (text: string) => void;
  busy: boolean;
  showHint?: boolean;
  voice: LiveVoice;
}

export default function Composer({ onSubmit, busy, voice, showHint = false }: ComposerProps) {
  const [value, setValue] = useState("");
  const voiceBusy = voice.phase !== "idle";
  const localActive = !["unknown", "stopped", "error"].includes(voice.localPhase);

  const send = () => {
    if (value.trim() && !busy && !voiceBusy) {
      onSubmit(value);
      setValue("");
    }
  };

  return (
    <>
      <div className="ask">
        <input
          className="ask__input"
          value={value}
          placeholder="Ask Yu…"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing) send();
          }}
          disabled={busy || voiceBusy}
          aria-label="Ask Yu"
        />
        <button className="ask__send" onClick={send} disabled={busy || voiceBusy || !value.trim()} aria-label="发送">
          {busy ? "…" : "↑"}
        </button>
      </div>
      <div className="voice-controls">
        <button className="voice-button" disabled={!voiceBusy && (busy || !voice.status.available || localActive)}
          aria-pressed={voiceBusy} onClick={() => voiceBusy ? voice.stop() : voice.start()}>
          {voiceBusy ? "结束语音" : "开始语音"}
        </button>
        {localActive && <>
          <span role="status">本地语音：{voice.localPhase}</span>
          <button onClick={() => void voice.control("pause_speech")}>暂停朗读</button>
          <button onClick={() => void voice.control("end_session")}>结束对话</button>
          <button onClick={() => void voice.control("stop_service")}>关闭服务</button>
        </>}
        <span role="status" aria-live="polite">{voice.error || (voice.phase === "connecting" ? "正在连接 · 等待麦克风与实时识别服务…" : voice.phase === "listening" ? "● 持续监听 · 说完自动执行 · 也可说“结束语音”" : voice.status.message)}</span>
      </div>
      {voiceBusy && voice.caption && <p className="voice-caption">{voice.caption}</p>}
      {showHint && <div className="ask__hint">Enter 发送 · 试试「宇，我今天该做什么？」</div>}
    </>
  );
}
