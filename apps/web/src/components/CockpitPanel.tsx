import type { SystemStatus, TodayResponse, YuUIState } from "../lib/types";
import Core from "./Core";
import StatTile from "./StatTile";
import SystemHealthCard from "./SystemHealthCard";

interface CockpitPanelProps {
  state: YuUIState;
  today: TodayResponse | null;
  sys: SystemStatus | null;
  demo: boolean;
  mask: (s: string) => string;
}

export default function CockpitPanel({ state, today, sys, demo, mask }: CockpitPanelProps) {
  const one = today?.top_priority ?? null;
  const memCount = today?.memory_count ?? 0;
  const openCount = today?.tasks.open.length ?? 0;
  const ram = sys?.ram_percent ?? null;

  return (
    <aside className="cockpit-panel">
      <div className="cockpit-panel__core">
        <Core state={state} compact />
      </div>

      <div className="cockpit-panel__section">
        <span className="label">TODAY</span>
        <div className="cockpit-panel__today">{one ? (demo ? mask(one.title) : one.title) : "暂无优先事项"}</div>
      </div>

      <div className="cockpit-panel__metrics">
        <StatTile label="Memory" value={String(memCount)} unit="memories" />
        <StatTile label="Today" value={String(openCount)} unit="priorities" />
        <StatTile label="System" value={ram != null ? Math.round(ram) + "%" : "—"} unit="RAM" />
      </div>

      {state === "system_analysis" && sys && <SystemHealthCard status={sys} />}
    </aside>
  );
}
