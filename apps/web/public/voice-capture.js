/* 音频线程只负责分块编码；AudioContext 必须以 16 kHz 创建。 */
class VoiceCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.frame = new ArrayBuffer(3200);
    this.view = new DataView(this.frame);
    this.offset = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel || sampleRate !== 16000) return true;
    for (const value of channel) {
      const clipped = Math.max(-1, Math.min(1, value));
      this.view.setInt16(this.offset, clipped < 0 ? clipped * 32768 : clipped * 32767, true);
      this.offset += 2;
      if (this.offset === 3200) {
        this.port.postMessage(this.frame, [this.frame]);
        this.frame = new ArrayBuffer(3200);
        this.view = new DataView(this.frame);
        this.offset = 0;
      }
    }
    return true;
  }
}
registerProcessor('voice-capture', VoiceCapture);
