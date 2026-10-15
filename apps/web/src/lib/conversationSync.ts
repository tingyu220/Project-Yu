import type { ConversationTurn } from "./types";

export function mergeTurns(existing: ConversationTurn[], incoming: ConversationTurn[]): ConversationTurn[] {
  const bySeq = new Map(existing.map(turn => [turn.seq, turn]));
  for (const turn of incoming) {
    const previous = bySeq.get(turn.seq);
    if (!previous || turn.revision >= previous.revision) bySeq.set(turn.seq, turn);
  }
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq);
}

export function pollDelay(hidden: boolean): number { return hidden ? 5000 : 1000; }
