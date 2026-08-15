import { useState } from "react";

interface ComposerProps {
  onSubmit: (text: string) => void;
  busy: boolean;
  showHint?: boolean;
}

export default function Composer({ onSubmit, busy, showHint = false }: ComposerProps) {
  const [value, setValue] = useState("");

  const send = () => {
    if (value.trim() && !busy) {
      onSubmit(value);
      setValue("");
    }
  };

  return (
    <>
      <div className="ask">
        <input
          className="ask__input"
          value={value}
          placeholder="Ask Yu…"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          disabled={busy}
          aria-label="Ask Yu"
        />
        <button className="ask__send" onClick={send} disabled={busy || !value.trim()} aria-label="发送">
          {busy ? "…" : "↑"}
        </button>
      </div>
      {showHint && <div className="ask__hint">Enter 发送 · 试试「宇，我今天该做什么？」</div>}
    </>
  );
}
