import type { Message, YuUIState } from "../lib/types";
import Composer from "./Composer";
import MessageList from "./MessageList";

interface ConversationPanelProps {
  messages: Message[];
  uiState: YuUIState;
  busy: boolean;
  reduced: boolean;
  mask: (s: string) => string;
  onSubmit: (text: string) => void;
}

const WORKING: YuUIState[] = ["thinking", "remembering", "planning", "system_analysis", "answering"];

export default function ConversationPanel({ messages, uiState, busy, reduced, mask, onSubmit }: ConversationPanelProps) {
  const statusLabel = uiState === "error" ? "ERROR" : WORKING.includes(uiState) ? "WORKING" : "READY";
  const dot = uiState === "error" ? "foot__dot--off" : "foot__dot--ok";

  return (
    <section className="conversation-panel">
      <header className="conversation-panel__header">
        <span className="conversation-panel__title">CONVERSATION</span>
        <span className="conversation-panel__status">
          <span className={"foot__dot " + dot} />
          {statusLabel}
        </span>
      </header>
      <MessageList messages={messages} busy={busy} reduced={reduced} mask={mask} />
      <div className="conversation-panel__composer">
        <Composer onSubmit={onSubmit} busy={busy} />
      </div>
    </section>
  );
}
