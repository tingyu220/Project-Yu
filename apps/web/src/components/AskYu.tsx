import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { usePresentation } from "../lib/presentation";
import type { ChatKind, RetrievalMatch } from "../lib/types";
import type { CoreState } from "./Core";

const KIND_LABELS: Record<ChatKind, string> = {
  chat: "YU",
  plan: "TODAY",
  computer: "SYSTEM",
  error: "ERROR",
};

interface AskYuProps {
  state: CoreState;
  reply: string;
  kind: ChatKind;
  retrieved: RetrievalMatch[];
  error: string | null;
  busy: boolean;
  onSubmit: (text: string) => void;
}

export default function AskYu({ state, reply, kind, retrieved, error, busy, onSubmit }: AskYuProps) {
  const [value, setValue] = useState("");
  const { demo, mask } = usePresentation();

  const send = () => {
    if (value.trim() && !busy) {
      onSubmit(value);
      setValue("");
    }
  };

  const hasReply = reply.length > 0 || error !== null;
  const spinning = state === "thinking" || state === "remembering";

  return (
    <div className="ask-wrap">
      <AnimatePresence mode="wait">
        {hasReply && (
          <motion.div
            key={reply + (error ?? "")}
            className="answer"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.5, ease: [0.22, 0.61, 0.36, 1] }}
          >
            <div className="answer__kind">{error ? "ERROR" : KIND_LABELS[kind]}</div>
            <div className="answer__text">{error ? error : reply}</div>
            {retrieved.length > 0 && (
              <div className="answer__chips">
                {retrieved.slice(0, 6).map((m) => (
                  <span key={m.memory.id} className="chip">
                    <span className="chip__dot" />
                    {mask(m.memory.content)}
                  </span>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="ask">
        <input
          className="ask__input"
          value={value}
          placeholder="Ask Yu…  宇，我今天该做什么？"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          disabled={busy}
          aria-label="Ask Yu"
        />
        <button className="ask__send" onClick={send} disabled={busy || !value.trim()} aria-label="发送">
          {spinning ? "…" : "↑"}
        </button>
      </div>
      <div className="ask__hint">
        {busy ? "Yu 正在思考…" : demo ? "Demo 模式已开启" : "Enter 发送 · 试试「宇，你还记得我们为什么开始做你吗？」"}
      </div>
    </div>
  );
}
