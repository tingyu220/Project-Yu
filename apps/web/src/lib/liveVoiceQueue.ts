/** 每个语音会话独立排队；相同识别句号只执行一次，结束后不能再入队。 */
export class LiveVoiceQueue {
  private seen = new Set<string>();
  private pending: string[] = [];
  private running = false;
  private closed = false;
  constructor(private submit: (text: string) => Promise<void>, private onError: () => void = () => {}) {}

  add(id: string, text: string): boolean {
    if (this.closed || this.seen.has(id) || !text.trim()) return false;
    if (this.pending.length >= 3 || this.seen.size >= 1000) throw new Error("待处理语音过多，已结束监听，请等当前操作完成。");
    this.seen.add(id);
    this.pending.push(text.trim());
    void this.drain();
    return true;
  }

  clear(): void {
    this.closed = true;
    this.pending = [];
  }

  private async drain(): Promise<void> {
    if (this.running || this.closed) return;
    this.running = true;
    try {
      while (!this.closed && this.pending.length) await this.submit(this.pending.shift()!);
    } catch {
      this.clear();
      this.onError();
    } finally {
      this.running = false;
    }
  }
}
