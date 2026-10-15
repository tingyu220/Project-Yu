import { motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import CockpitPanel from "../components/CockpitPanel";
import Composer from "../components/Composer";
import ConversationPanel from "../components/ConversationPanel";
import Core from "../components/Core";
import StatTile from "../components/StatTile";
import { api } from "../lib/api";
import { usePresentation } from "../lib/presentation";
import { useReducedMotion } from "../lib/useReducedMotion";
import type { StatusResponse, SystemStatusResponse, TodayResponse } from "../lib/types";
import { useConversation } from "../lib/useConversation";
import { useLiveVoice } from "../lib/useLiveVoice";

const DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

function formatDate(d: Date): string {
  return DAYS[d.getDay()] + " · " + MONTHS[d.getMonth()] + " " + d.getDate();
}

function greeting(d: Date): string {
  const h = d.getHours();
  if (h < 5) return "GOOD NIGHT";
  if (h < 12) return "GOOD MORNING";
  if (h < 18) return "GOOD AFTERNOON";
  return "GOOD EVENING";
}

export default function Cockpit() {
  const reduced = useReducedMotion();
  const { demo, mask } = usePresentation();
  const refreshToday = useCallback(() => {
    api.today().then(setToday).catch(() => {});
  }, []);
  const conv = useConversation(reduced, refreshToday);
  // 会话放在稳定父组件，首句触发布局切换时不关闭麦克风。
  const voice = useLiveVoice(conv.submit);
  const submitText = (text: string) => { void conv.submit(text).catch(() => {}); };

  const [today, setToday] = useState<TodayResponse | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [sys, setSys] = useState<SystemStatusResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.today(), api.status(), api.systemStatus()])
      .then(([t, s, y]) => {
        if (!alive) return;
        setToday(t);
        setStatus(s);
        setSys(y);
      })
      .catch((e: unknown) => {
        if (alive) setErr(e instanceof Error ? e.message : String(e));
      });
    return () => {
      alive = false;
    };
  }, []);

  // 进入 system_analysis 状态时刷新系统数据（供 SystemHealthCard 展示）
  useEffect(() => {
    if (conv.uiState === "system_analysis") {
      api.systemStatus().then(setSys).catch(() => {});
    }
  }, [conv.uiState]);

  const now = new Date();
  const one = today?.top_priority ?? null;
  const openCount = today?.tasks.open.length ?? 0;
  const memCount = today?.memory_count ?? 0;
  const ram = sys?.status?.ram_percent ?? null;

  if (conv.mode === "idle") {
    return (
      <main className="cockpit-page">
        <div className="cockpit-idle">
          <section className="cockpit__hero">
            <span className="hero__date">{formatDate(now)}</span>
            <div className="hero__core-wrap">
              <Core state="idle" />
            </div>
            <span className="hero__greeting">{greeting(now)}</span>
            <h1 className="hero__one">
              {one ? (
                <>
                  今天最重要的一件事：
                  <strong>{demo ? mask(one.title) : one.title}</strong>
                </>
              ) : (
                <>Yu 已就绪。</>
              )}
            </h1>
            <p className="hero__sub">
              {today && !one ? "还没有目标或任务。先对 Yu 说一句话，让它开始了解你。" : "Today matters."}
            </p>
          </section>

          <section className="stats" aria-label="概览">
            <StatTile label="Memory" value={String(memCount)} unit="memories" />
            <StatTile
              label="Today"
              value={String(openCount)}
              unit="priorities"
              hint={one ? mask(one.title) : undefined}
            />
            <StatTile label="System" value={ram != null ? Math.round(ram) + "%" : "—"} unit="RAM" />
          </section>

          {err && <div className="state-msg">无法连接 Yu API：{err}</div>}

          <div className="idle-composer">
            <Composer onSubmit={submitText} busy={conv.busy} voice={voice} showHint />
          </div>

          <footer className="foot">
            <span>
              <span className={"foot__dot " + (status?.llm.available ? "foot__dot--ok" : "foot__dot--off")} />
              {status?.llm.available ? "LLM READY" : "LLM OFFLINE"}
            </span>
            <span>Yu v{status?.version ?? "0.0.8"}</span>
          </footer>
        </div>
      </main>
    );
  }

  return (
    <main className="cockpit-page cockpit-page--conversation">
      <motion.div
        className="cockpit-layout"
        initial={{ opacity: 0, x: reduced ? 0 : 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: reduced ? 0.001 : 0.7, ease: [0.22, 0.61, 0.36, 1] }}
      >
        <CockpitPanel
          state={conv.uiState}
          today={today}
          sys={sys?.status ?? null}
          demo={demo}
          mask={mask}
        />
        <ConversationPanel
          messages={conv.messages}
          uiState={conv.uiState}
          busy={conv.busy}
          reduced={reduced}
          mask={mask}
          onSubmit={submitText}
          voice={voice}
        />
      </motion.div>
    </main>
  );
}
