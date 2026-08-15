import { useEffect, useMemo, useState } from "react";
import MemoryCanvas from "../components/MemoryCanvas";
import MemoryDetail from "../components/MemoryDetail";
import { api } from "../lib/api";
import { CLUSTERS, clusterOf } from "../lib/cluster";
import { usePresentation } from "../lib/presentation";
import { useReducedMotion } from "../lib/useReducedMotion";
import type { Memory, MemoryStats } from "../lib/types";

export default function MemoryUniverse() {
  const reduced = useReducedMotion();
  const { demo, mask } = usePresentation();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [query, setQuery] = useState("");
  const [highlights, setHighlights] = useState<number[]>([]);
  const [selected, setSelected] = useState<Memory | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.memories(150), api.memoryStats()])
      .then(([m, s]) => {
        if (!alive) return;
        setMemories(m.memories);
        setStats(s);
      })
      .catch((e: unknown) => {
        if (alive) setErr(e instanceof Error ? e.message : String(e));
      });
    return () => {
      alive = false;
    };
  }, []);

  const runQuery = async (q: string) => {
    const t = q.trim();
    if (!t) {
      setHighlights([]);
      return;
    }
    try {
      const res = await api.queryMemories(t, 8);
      setHighlights(res.matches.map((m) => m.memory.id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  const legendClusters = useMemo(() => {
    const seen = new Set(memories.map((m) => clusterOf(m)));
    return CLUSTERS.filter((c) => seen.has(c.key));
  }, [memories]);

  return (
    <main className="page">
      <div className="universe">
        <div className="universe__bar">
          <h1 className="universe__title">Memory Universe</h1>
          <span className="universe__stats">
            {stats ? stats.total + " memories · " + stats.active + " active" : "…"}
          </span>
          <div className="universe__spacer" />
          <div className="universe__query">
            <input
              className="universe__query-input"
              value={query}
              placeholder="搜索记忆…"
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runQuery(query);
              }}
              aria-label="搜索记忆"
            />
          </div>
        </div>

        <div className="universe__stage">
          {memories.length === 0 && !err ? (
            <div className="state-msg">暂无记忆。对 Yu 说「记住：……」来积累长期记忆。</div>
          ) : (
            <MemoryCanvas
              memories={memories}
              highlights={highlights}
              selectedId={selected?.id ?? null}
              onSelect={setSelected}
              reduced={reduced}
            />
          )}
          <div className="universe__hint">拖拽平移 · 滚轮缩放 · 点击节点查看</div>

          {selected && (
            <MemoryDetail
              memory={selected}
              demo={demo}
              mask={mask}
              onClose={() => setSelected(null)}
            />
          )}
        </div>

        {legendClusters.length > 0 && (
          <div className="legend">
            {legendClusters.map((c) => (
              <span key={c.key} className="legend__item">
                <span className="legend__dot" style={{ background: c.color }} />
                {c.label}
              </span>
            ))}
          </div>
        )}

        {err && <div className="state-msg">无法连接 Yu API：{err}</div>}
      </div>
    </main>
  );
}
