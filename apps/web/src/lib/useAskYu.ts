import { useCallback, useRef, useState } from "react";
import type { CoreState, NodeHint } from "../components/Core";
import { api } from "./api";
import type { ChatKind, HistoryMessage, RetrievalMatch } from "./types";

export interface AskYuState {
  state: CoreState;
  nodes: NodeHint[];
  reply: string;
  kind: ChatKind;
  retrieved: RetrievalMatch[];
  error: string | null;
  busy: boolean;
  submit: (text: string) => void;
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

/** 驱动 Ask Yu 交互的状态机：idle → listening → thinking → remembering → answering。 */
export function useAskYu(reduced: boolean): AskYuState {
  const [state, setState] = useState<CoreState>("idle");
  const [nodes, setNodes] = useState<NodeHint[]>([]);
  const [reply, setReply] = useState("");
  const [kind, setKind] = useState<ChatKind>("chat");
  const [retrieved, setRetrieved] = useState<RetrievalMatch[]>([]);
  const [error, setError] = useState<string | null>(null);
  const historyRef = useRef<HistoryMessage[]>([]);

  const submit = useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t) return;
      setReply("");
      setError(null);
      setNodes([]);
      setRetrieved([]);
      setState("listening");

      window.setTimeout(
        () => {
          setState("thinking");
          api
            .chat(t, historyRef.current)
            .then((res) => {
              setKind(res.kind);
              setReply(res.reply);
              setRetrieved(res.retrieved);
              historyRef.current = [
                ...historyRef.current,
                { role: "user", content: t },
                { role: "assistant", content: res.reply },
              ].slice(-20);

              const hints = res.retrieved.slice(0, 7).map((m) => ({
                id: m.memory.id,
                label: truncate(m.memory.content, 12),
              }));
              if (hints.length > 0 && !reduced) {
                setNodes(hints);
                setState("remembering");
                window.setTimeout(() => setState("answering"), 1150);
              } else {
                setState("answering");
              }
              window.setTimeout(() => setState("idle"), 2600);
            })
            .catch((e: unknown) => {
              setError(e instanceof Error ? e.message : String(e));
              setState("error");
            });
        },
        reduced ? 0 : 480,
      );
    },
    [reduced],
  );

  const busy = state === "listening" || state === "thinking" || state === "remembering";

  return { state, nodes, reply, kind, retrieved, error, busy, submit };
}
