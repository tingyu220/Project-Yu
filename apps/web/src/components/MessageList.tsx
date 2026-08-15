import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Message } from "../lib/types";
import YuMessage from "./YuMessage";

interface MessageListProps {
  messages: Message[];
  busy: boolean;
  reduced: boolean;
  mask: (s: string) => string;
}

export default function MessageList({ messages, busy, reduced, mask }: MessageListProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const [autoFollow, setAutoFollow] = useState(true);

  const scrollToBottom = (smooth: boolean) => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth && !reduced ? "smooth" : "auto" });
  };

  const onScroll = () => {
    const el = listRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    setAutoFollow(dist < 80);
  };

  useEffect(() => {
    if (autoFollow) scrollToBottom(false);
  }, [messages, busy, autoFollow]);

  return (
    <div className="message-list-wrap">
      <div className="message-list" ref={listRef} onScroll={onScroll}>
        <AnimatePresence initial={false}>
          {messages.map((m) =>
            m.role === "user" ? (
              <motion.div
                key={m.id}
                className="msg msg--user"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <div className="msg__label">YOU</div>
                <div className="msg__body">{m.content}</div>
              </motion.div>
            ) : (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
              >
                <YuMessage message={m} mask={mask} />
              </motion.div>
            ),
          )}
        </AnimatePresence>

        {busy && (
          <div className="msg msg--typing" aria-label="Yu 正在思考">
            <span className="msg__label">YU</span>
            <span className="typing-dots">
              <i />
              <i />
              <i />
            </span>
          </div>
        )}
      </div>

      {!autoFollow && messages.length > 0 && (
        <button
          className="latest-btn"
          onClick={() => {
            scrollToBottom(true);
            setAutoFollow(true);
          }}
        >
          ↓ Latest
        </button>
      )}
    </div>
  );
}
