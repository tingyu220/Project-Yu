import { useCallback, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { HistoryMessage, Message, YuUIState } from "./types";

let seq = 0;
function nextId(): string {
  seq += 1;
  return "m" + Date.now().toString(36) + "-" + seq;
}

function intentOf(text: string): "planning" | "system_analysis" | "thinking" {
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
  submit: (text: string) => void;
}

/** Cockpit 对话状态机：Mode（idle/conversation）与 YuUIState 分离。 */
export function useConversation(reduced: boolean): ConversationApi {
  const [messages, setMessages] = useState<Message[]>([]);
  const [uiState, setUiState] = useState<YuUIState>("idle");
  const [busy, setBusy] = useState(false);
  const historyRef = useRef<HistoryMessage[]>([]);
  const busyRef = useRef(false);

  const submit = useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t || busyRef.current) return;
      busyRef.current = true;

      setMessages((prev) => [...prev, { id: nextId(), role: "user", content: t, createdAt: Date.now() }]);
      setBusy(true);
      setUiState(intentOf(t));

      api
        .chat(t, historyRef.current)
        .then((res) => {
          historyRef.current = [
            ...historyRef.current,
            { role: "user", content: t },
            { role: "assistant", content: res.reply },
          ].slice(-20);

          const append = () => {
            setMessages((prev) => [
              ...prev,
              { id: nextId(), role: "yu", content: res.reply, kind: res.kind, retrieved: res.retrieved, createdAt: Date.now() },
            ]);
            setBusy(false);
            busyRef.current = false;
            setUiState("answering");
            window.setTimeout(() => setUiState("ready"), 1400);
          };

          if (res.retrieved.length > 0 && !reduced) {
            setUiState("remembering");
            window.setTimeout(append, 1000);
          } else {
            append();
          }
        })
        .catch((e: unknown) => {
          setMessages((prev) => [
            ...prev,
            { id: nextId(), role: "yu", content: e instanceof Error ? e.message : String(e), kind: "error", createdAt: Date.now() },
          ]);
          setBusy(false);
          busyRef.current = false;
          setUiState("error");
        });
    },
    [reduced],
  );

  const mode = messages.length > 0 ? "conversation" : "idle";

  return useMemo(() => ({ messages, mode, uiState, busy, submit }), [messages, mode, uiState, busy, submit]);
}
