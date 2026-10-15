import { useEffect, useRef, useState } from "react";
import { toWav } from "./voiceAudio";
import { detectSilence } from "./silenceDetector";

type Phase = "idle" | "requesting" | "recording" | "recognizing";
interface Status { available: boolean; message: string }

/** 每次录音绑定序号；取消、切页后的迟到结果不能覆盖输入。 */
export function useVoiceInput(onText: (text: string) => void) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [seconds, setSeconds] = useState(0);
  const [status, setStatus] = useState<Status>({ available: false, message: "正在检查语音服务…" });
  const [error, setError] = useState("");
  const active = useRef(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const controller = useRef<AbortController | null>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const detector = useRef<(() => void) | null>(null);
  const callback = useRef(onText);
  callback.current = onText;

  function release() {
    detector.current?.(); detector.current = null;
    if (audioContext.current && audioContext.current.state !== "closed") void audioContext.current.close();
    audioContext.current = null;
    window.clearInterval(timer.current);
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }
  function cancel() {
    active.current++;
    controller.current?.abort();
    if (recorder.current?.state === "recording") recorder.current.stop();
    release(); setPhase("idle");
  }
  useEffect(() => {
    const abort = new AbortController();
    fetch("/api/voice/status", { signal: abort.signal }).then(async (res) => {
      if (!res.ok) throw new Error("服务不可用");
      setStatus(await res.json());
    }).catch(() => { if (!abort.signal.aborted) setStatus({ available: false, message: "语音服务不可用，仍可输入文字。" }); });
    return () => { abort.abort(); active.current++; controller.current?.abort(); release(); };
  }, []);

  function stop() {
    if (recorder.current?.state === "recording") recorder.current.stop();
    release();
  }
  async function start() {
    if (phase !== "idle") return;
    const id = ++active.current;
    setError(""); setPhase("requesting"); setSeconds(0);
    window.speechSynthesis?.cancel();
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
        throw new Error("请使用 localhost 或 HTTPS 下的现代浏览器录音。");
      }
      const context = new AudioContext();
      audioContext.current = context;
      await context.resume();
      if (id !== active.current) return;
      const media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
      if (id !== active.current) { media.getTracks().forEach((t) => t.stop()); return; }
      stream.current = media;
      const chunks: Blob[] = [];
      const rec = new MediaRecorder(media);
      recorder.current = rec;
      rec.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      rec.onerror = () => { if (id === active.current) { cancel(); setError("录音中断，请检查麦克风后重试。"); } };
      rec.onstop = async () => {
        if (id !== active.current) return;
        release(); setPhase("recognizing");
        const abort = new AbortController(); controller.current = abort;
        const timeout = window.setTimeout(() => abort.abort(), 25000);
        try {
          const wav = await toWav(new Blob(chunks, { type: rec.mimeType }));
          if (id !== active.current) return;
          const response = await fetch("/api/voice/transcribe", { method: "POST", headers: { "Content-Type": "audio/wav" }, body: wav, signal: abort.signal });
          const result = await response.json();
          if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "语音识别失败，请重试。");
          if (id === active.current) callback.current(result.text);
        } catch (e) {
          if (id === active.current) setError(abort.signal.aborted ? "识别超时，请重试或输入文字。" : e instanceof Error ? e.message : "识别失败，请重试。");
        } finally {
          window.clearTimeout(timeout);
          if (id === active.current) setPhase("idle");
        }
      };
      rec.start(); setPhase("recording");
      detector.current = detectSilence(context, media, stop, () => {
        cancel(); setError("没有听到说话，录音已停止。点击说话可重试。");
      });
      const started = Date.now();
      timer.current = window.setInterval(() => {
        const elapsed = Math.floor((Date.now() - started) / 1000); setSeconds(elapsed);
        if (elapsed >= 30) stop();
      }, 200);
    } catch (e) {
      if (id === active.current) {
        release();
        setPhase("idle");
        setError(e instanceof DOMException && e.name === "NotAllowedError" ? "麦克风权限被拒绝，请在浏览器地址栏允许麦克风。" : e instanceof Error ? e.message : "无法打开麦克风。");
      }
    }
  }
  return { phase, seconds, status, error, start, stop, cancel };
}
