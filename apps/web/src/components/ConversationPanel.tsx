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

const STATE_LABEL: Record<YuUIState, string> = {
  idle: "READY",
  thinking: "THINKING",
  remembering: "REMEMBERING",
  planning: "PLANNING",
  system_analysis: "ANALYZING",
  answering: "ANSWERING",
  ready: "READY",
  error: "ERROR",
};

export default function ConversationPanel({ messages, uiState, busy, reduced, mask, onSubmit }: ConversationPanelProps) {
  const dot = uiState === "error" ? "foot__dot--off" : "foot__dot--ok";

  return (
    <section className="conversation-panel">
      <header className="conversation-panel__header">
        <span className="conversation-panel__title">CONVERSATION</span>
        <span className="conversation-panel__status">
          <span className={"foot__dot " + dot} />
          {STATE_LABEL[uiState]}
        </span>
      </header>
      <MessageList messages={messages} busy={busy} reduced={reduced} mask={mask} />
      <div className="conversation-panel__composer">
        <Composer onSubmit={onSubmit} busy={busy} />
      </div>
    </section>
  );
}
