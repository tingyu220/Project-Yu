import { SpeechEndpoint } from "./speechEndpoint";

/** 只在用户开启录音期间分析本机音量，不保留音频。 */
export function detectSilence(context: AudioContext, stream: MediaStream, onEnd: () => void, onEmpty: () => void) {
  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = 2048;
  source.connect(analyser);
  const samples = new Float32Array(analyser.fftSize);
  const endpoint = new SpeechEndpoint();
  let previous = performance.now();
  const timer = window.setInterval(() => {
    analyser.getFloatTimeDomainData(samples);
    const rms = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
    const now = performance.now();
    const state = endpoint.feed(rms, Math.min(now - previous, 150));
    previous = now;
    if (state !== "listen") {
      window.clearInterval(timer);
      if (state === "submit") onEnd(); else onEmpty();
    }
  }, 40);
  return () => { window.clearInterval(timer); source.disconnect(); analyser.disconnect(); };
}
