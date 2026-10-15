import { useCallback, useEffect, useRef, useState } from "react";
import { LiveVoiceQueue } from "./liveVoiceQueue";
import { LiveVoiceSession } from "./liveVoiceSession";
import { isVoiceStopCommand } from "./voiceCommands";

export function useLiveVoice(submit: (text: string) => Promise<void>) {
  const [phase, setPhase] = useState<"idle" | "connecting" | "listening">("idle");
  const [caption, setCaption] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState({available: false, message: "正在检查语音配置…"});
  const [localPhase, setLocalPhase] = useState("unknown");
  const session = useRef<LiveVoiceSession | null>(null);
  const queue = useRef<LiveVoiceQueue | null>(null);
  const submitRef = useRef(submit);
  submitRef.current = submit;

  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;
    async function poll() {
      try {
        const response = await fetch("/api/voice/control/status", {signal: controller.signal});
        if (!response.ok) throw new Error();
        const data = await response.json();
        setLocalPhase(data.phase);
      } catch { if (!controller.signal.aborted) setLocalPhase("unknown"); }
      if (!controller.signal.aborted) timer = window.setTimeout(poll, 1000);
    }
    void poll();
    return () => { controller.abort(); if (timer) window.clearTimeout(timer); };
  }, []);

  const control = useCallback(async (command: string) => {
    const response = await fetch("/api/voice/control/token");
    const {token} = await response.json();
    const result = await fetch("/api/voice/control/command", {method: "POST",
      headers: {"Content-Type": "application/json", "X-Yu-Control-Token": token},
      body: JSON.stringify({command})});
    if (!result.ok) setError("语音控制失败，请使用启动窗口停止。");
  }, []);

  const stop = useCallback(() => {
    session.current?.stop(); session.current = null;
    queue.current?.clear(); queue.current = null;
    setPhase("idle"); setCaption("");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/voice/status", {signal: controller.signal}).then(r => {
      if (!r.ok) throw new Error();
      return r.json();
    }).then(setStatus).catch(() => {
      if (!controller.signal.aborted) setStatus({available: false, message: "无法读取语音配置，请检查本机服务。"});
    });
    const leave = () => stop();
    window.addEventListener("pagehide", leave);
    return () => { controller.abort(); window.removeEventListener("pagehide", leave); stop(); };
  }, [stop]);

  const start = useCallback(() => {
    if (session.current || !status.available || !["unknown", "stopped", "error"].includes(localPhase)) return;
    setError(""); setCaption(""); setPhase("connecting");
    const fail = (message: string) => {
      // 旧请求失败不能终止用户刚开启的新会话。
      if (session.current !== live) return;
      stop(); setError(message);
    };
    const pending = new LiveVoiceQueue(text => submitRef.current(text), () => fail("本轮处理失败，已清空待处理语音，请重新开启。"));
    queue.current = pending;
    const live = new LiveVoiceSession(event => {
      if (event.type === "ready") setPhase("listening");
      if (event.type === "partial") setCaption(event.text || "");
      if (event.type === "final" && event.id && event.text) {
        if (isVoiceStopCommand(event.text)) { stop(); return; }
        try {
          if (pending.add(event.id, event.text)) setCaption(`已收到：${event.text}`);
        } catch (e) { fail(e instanceof Error ? e.message : "语音队列已满。"); }
      }
    }, fail);
    session.current = live;
    void live.start();
  }, [status.available, stop, localPhase]);

  return {phase, caption, error, status, start, stop, localPhase, control};
}

export type LiveVoice = ReturnType<typeof useLiveVoice>;
