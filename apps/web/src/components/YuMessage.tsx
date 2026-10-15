import { useState } from "react";
import type { Message } from "../lib/types";
import Markdown from "./Markdown";
import SpeakButton from "./SpeakButton";

const LONG_THRESHOLD = 1400;
const PREVIEW_LENGTH = 600;

interface YuMessageProps {
  message: Message;
  mask: (s: string) => string;
  voiceActive?: boolean;
}

export default function YuMessage({ message, mask, voiceActive = false }: YuMessageProps) {
  const [expanded, setExpanded] = useState(false);
  const isLong = message.content.length > LONG_THRESHOLD;
  const collapsed = isLong && !expanded;

  return (
    <div className="msg msg--yu">
      <div className="msg__label">YU</div>
      <div className="msg__body">
        <SpeakButton text={mask(message.content)} disabled={voiceActive} />
        {message.kind === "error" ? (
          <div className="msg__error">{message.content}</div>
        ) : collapsed ? (
          <>
            <Markdown>{message.content.slice(0, PREVIEW_LENGTH).replace(/\n+$/, "") + "…"}</Markdown>
            <button className="msg__toggle" onClick={() => setExpanded(true)}>
              展开完整分析 ↓
            </button>
          </>
        ) : (
          <>
            <Markdown>{message.content}</Markdown>
            {isLong && (
              <button className="msg__toggle" onClick={() => setExpanded(false)}>
                收起 ↑
              </button>
            )}
          </>
        )}

        {message.retrieved && message.retrieved.length > 0 && (
          <div className="msg__chips">
            {message.retrieved.slice(0, 6).map((m) => (
              <span key={m.memory.id} className="chip" title={"mem_" + m.memory.id}>
                <span className="chip__dot" />
                <span className="chip__id">#{m.memory.id}</span>
                {mask(m.memory.content)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
