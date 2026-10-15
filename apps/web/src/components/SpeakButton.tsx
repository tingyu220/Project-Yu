import { useEffect, useState } from "react";

/** 只使用浏览器标记为本地的中文音色，不自动调用境外服务。 */
export default function SpeakButton({ text, disabled = false }: { text: string; disabled?: boolean }) {
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => () => { window.speechSynthesis?.cancel(); }, []);
  useEffect(() => {
    if (disabled) { window.speechSynthesis?.cancel(); setSpeaking(false); }
  }, [disabled]);
  function toggle() {
    if (disabled) return;
    const engine = window.speechSynthesis;
    if (!engine) { setError("当前浏览器不支持播报。"); return; }
    engine.cancel();
    if (speaking) { setSpeaking(false); return; }
    const voice = engine.getVoices().find((v) => v.localService && /^zh/i.test(v.lang));
    if (!voice) { setError("未找到本机中文音色，请安装 Windows 中文语音包后重试。"); return; }
    setError("");
    const utterance = new SpeechSynthesisUtterance(text.replace(/[`#*_]/g, "").slice(0, 2000));
    utterance.voice = voice;
    utterance.onend = utterance.onerror = () => setSpeaking(false);
    setSpeaking(true); engine.speak(utterance);
  }
  return <div className="voice-controls"><button className="voice-button" disabled={disabled} title={disabled ? "持续监听时暂停朗读，避免误识别自身回复" : undefined} onClick={toggle}>{speaking ? "停止播报" : "朗读回复"}</button><span role="status">{error}</span></div>;
}
