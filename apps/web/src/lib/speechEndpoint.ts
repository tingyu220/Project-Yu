/** 轻量句尾检测：持续人声后静音一秒提交；纯静音不提交。 */
export class SpeechEndpoint {
  private voicedMs = 0;
  private quietMs = 0;
  private totalMs = 0;
  heardSpeech = false;
  feed(rms: number, elapsedMs: number): "listen" | "submit" | "empty" {
    this.totalMs += elapsedMs;
    if (rms >= 0.018) {
      this.voicedMs += elapsedMs;
      this.quietMs = 0;
      if (this.voicedMs >= 160) this.heardSpeech = true;
    } else {
      this.quietMs += elapsedMs;
      if (!this.heardSpeech) this.voicedMs = 0;
    }
    if (this.heardSpeech && this.quietMs >= 1000) return "submit";
    if (!this.heardSpeech && this.totalMs >= 8000) return "empty";
    return "listen";
  }
}
