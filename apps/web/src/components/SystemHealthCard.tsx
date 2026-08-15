import type { SystemStatus } from "../lib/types";

type Tone = "ok" | "warn" | "danger";

function band(v: number, warnAt: number, dangerAt: number): Tone {
  if (v >= dangerAt) return "danger";
  if (v >= warnAt) return "warn";
  return "ok";
}

function toneText(t: Tone): string {
  if (t === "danger") return "HIGH";
  if (t === "warn") return "ELEVATED";
  return "NORMAL";
}

export default function SystemHealthCard({ status }: { status: SystemStatus }) {
  const ramTone = band(status.ram_percent, 70, 85);
  const cpuTone = band(status.cpu_percent, 60, 80);
  const diskTone = band(status.disk_percent, 80, 90);
  const uptimeTone = status.uptime_hours > 72 ? "warn" : "ok";
  const battery = status.battery_percent;

  return (
    <div className="sys-card">
      <div className="sys-card__title">SYSTEM</div>

      <div className="sys-card__main">
        <div className="sys-card__row">
          <span className="sys-card__key">Memory</span>
          <span className={"sys-card__val sys-card__val--" + ramTone}>{Math.round(status.ram_percent)}%</span>
        </div>
        <div className="sys-card__bar">
          <span
            className={"sys-card__fill sys-card__fill--" + ramTone}
            style={{ width: Math.min(100, Math.max(0, status.ram_percent)) + "%" }}
          />
        </div>
        <div className="sys-card__sub">
          {status.ram_used_gb} / {status.ram_total_gb} GB · {toneText(ramTone)}
        </div>
      </div>

      <div className="sys-card__grid">
        <div className="sys-card__cell">
          <span className="sys-card__k">CPU</span>
          <b>{Math.round(status.cpu_percent)}%</b>
          <span className={"sys-card__t sys-card__t--" + cpuTone}>{toneText(cpuTone)}</span>
        </div>
        <div className="sys-card__cell">
          <span className="sys-card__k">DISK</span>
          <b>{Math.round(status.disk_percent)}%</b>
          <span className={"sys-card__t sys-card__t--" + diskTone}>{toneText(diskTone)}</span>
        </div>
        <div className="sys-card__cell">
          <span className="sys-card__k">BATTERY</span>
          <b>{battery != null ? Math.round(battery) + "%" : "—"}</b>
          <span className="sys-card__t sys-card__t--ok">{battery != null ? (battery > 20 ? "GOOD" : "LOW") : "—"}</span>
        </div>
        <div className="sys-card__cell">
          <span className="sys-card__k">UPTIME</span>
          <b>{Math.round(status.uptime_hours)}h</b>
          <span className={"sys-card__t sys-card__t--" + uptimeTone}>{uptimeTone === "warn" ? "ATTENTION" : "NORMAL"}</span>
        </div>
      </div>
    </div>
  );
}
