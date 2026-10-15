import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { ConversationTurn, HistoryMessage, Message, YuUIState } from "./types";
import { mergeTurns, pollDelay } from "./conversationSync";

let seq = 0;
function nextId(): string {
  seq += 1;
  return "m" + Date.now().toString(36) + "-" + seq;
}

function intentOf(text: string): "remembering" | "planning" | "system_analysis" | "thinking" {
  if (/记住|保存|修改.*记忆|更新.*记忆|忘掉|纠正|加入记忆/.test(text)) return "remembering";
  if (text.includes("今天") && /干什么|做什么|该做|计划|规划/.test(text)) return "planning";
  if ((text.includes("电脑") || text.includes("系统")) && /状态|卡|内存|磁盘|cpu|为什么|运行|怎么样|分析/.test(text)) {
    return "system_analysis";
  }
  return "thinking";
}

export interface ConversationApi {
  messages: Message[];
  mode: "idle" | "conversation";
  uiState: YuUIState;
  busy: boolean;
  submit: (text: string) => Promise<void>;
}

/** Cockpit 对话状态机：Mode（idle/conversation）与 YuUIState 分离。 */
export function useConversation(_reduced: boolean, onMemoryChanged?: () => void): ConversationApi {
  const [messages, setMessages] = useState<Message[]>([]);
  const [uiState, setUiState] = useState<YuUIState>("idle");
  const [busy, setBusy] = useState(false);
  const historyRef = useRef<HistoryMessage[]>([]);
  const lastReferencedRef = useRef<number[]>([]);
  const busyRef = useRef(false);
  const sessionRef = useRef<string | undefined>(undefined);
  const cursorRef = useRef(0);
  const turnsRef = useRef<ConversationTurn[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;
    const sync = async () => {
      try {
        if (!sessionRef.current) sessionRef.current = (await api.conversation()).session_id;
        let page = await api.conversationChanges(cursorRef.current, controller.signal);
        turnsRef.current = mergeTurns(turnsRef.current, page.turns);
        cursorRef.current = page.next_cursor;
        while (page.has_more) {
          page = await api.conversationChanges(cursorRef.current, controller.signal);
          turnsRef.current = mergeTurns(turnsRef.current, page.turns);
          cursorRef.current = page.next_cursor;
        }
        const restored: Message[] = [];
        for (const turn of turnsRef.current) {
          if (turn.state !== "completed" || !turn.result) continue;
          restored.push({id: `turn-${turn.seq}-user`, role: "user", content: turn.message, createdAt: Date.parse(turn.created_at)});
          restored.push({id: `turn-${turn.seq}-yu`, role: "yu", content: turn.result.reply, kind: turn.result.kind, retrieved: turn.result.retrieved, createdAt: Date.parse(turn.completed_at || turn.created_at)});
        }
        setMessages(prev => {
          const local = prev.filter(item => !item.id.startsWith("turn-"));
          return restored.length ? [...restored, ...local.filter(item => !restored.some(r => r.content === item.content && r.role === item.role))] : prev;
        });
      } catch (error) {
        if (!controller.signal.aborted) timer = window.setTimeout(sync, pollDelay(document.hidden));
        return;
      }
      if (!controller.signal.aborted) timer = window.setTimeout(sync, pollDelay(document.hidden));
    };
    void sync();
    return () => { controller.abort(); if (timer) window.clearTimeout(timer); };
  }, []);

  const submit = useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t) return Promise.resolve();
      if (busyRef.current) return Promise.reject(new Error("上一条消息仍在处理。"));
      busyRef.current = true;

      setMessages((prev) => [...prev, { id: nextId(), role: "user", content: t, createdAt: Date.now() }]);
      setBusy(true);
      setUiState(intentOf(t));

      return api
        .chat(t, [], lastReferencedRef.current, sessionRef.current, `web-${Date.now()}-${seq}`, "web")
        .then((res) => {
          historyRef.current = [
            ...historyRef.current,
            { role: "user", content: t },
            { role: "assistant", content: res.reply },
          ].slice(-20);

          // 记录本轮引用的记忆 id，供「修改这条记忆」等指代解析。
          lastReferencedRef.current = res.retrieved.map((m) => m.memory.id);

          // 记忆写操作成功后通知上层刷新（memory count / 列表）。
          if (res.intent && res.intent.startsWith("MEMORY_") && res.memory_result?.success) {
            onMemoryChanged?.();
          }

          const append = () => {
            setMessages((prev) => [
              ...prev,
              { id: nextId(), role: "yu", content: res.reply, kind: res.kind, retrieved: res.retrieved, createdAt: Date.now() },
            ]);
            setBusy(false);
            busyRef.current = false;
            setUiState("answering");
            window.setTimeout(() => { if (!busyRef.current) setUiState("ready"); }, 1400);
          };

          // 不为视觉状态增加人工等待，语音下一句可立即接续。
          append();
          return res;
        })
        .catch((e: unknown) => {
          setMessages((prev) => [
            ...prev,
            { id: nextId(), role: "yu", content: e instanceof Error ? e.message : String(e), kind: "error", createdAt: Date.now() },
          ]);
          setBusy(false);
          busyRef.current = false;
          setUiState("error");
          throw e;
        })
        .then((res) => {
          // HTTP 成功不代表业务成功；已展示真实回复，再通知语音队列停下。
          if (!res.allowed || res.kind === "error" || res.memory_result?.success === false) {
            setUiState("error");
            throw new Error(res.reply);
          }
        });
    },
    [onMemoryChanged],
  );

  const mode = messages.length > 0 ? "conversation" : "idle";

  return useMemo(() => ({ messages, mode, uiState, busy, submit }), [messages, mode, uiState, busy, submit]);
}
