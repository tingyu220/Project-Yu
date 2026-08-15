import { AnimatePresence, motion } from "framer-motion";
import { useReducedMotion } from "../lib/useReducedMotion";

export type CoreState =
  | "idle"
  | "listening"
  | "thinking"
  | "remembering"
  | "answering"
  | "error";

export interface NodeHint {
  id: number;
  label: string;
}

const CAPTIONS: Record<CoreState, string> = {
  idle: "IDLE",
  listening: "LISTENING",
  thinking: "THINKING",
  remembering: "REMEMBERING",
  answering: "ANSWERING",
  error: "ERROR",
};

const NODE_RADIUS = 76;

interface CoreProps {
  state: CoreState;
  nodes?: NodeHint[];
}

export default function Core({ state, nodes = [] }: CoreProps) {
  const reduced = useReducedMotion();
  const showNodes = state === "remembering" && nodes.length > 0 && !reduced;
  const count = Math.min(nodes.length, 7);

  return (
    <div className={"core core--" + state} aria-hidden="true">
      <div className="core__halo" />
      <div className="core__ring" />
      <div className="core__disc">
        <span className="core__glyph">宇</span>
      </div>

      <AnimatePresence>
        {showNodes && (
          <div className="core__nodes" key="nodes">
            {nodes.slice(0, count).map((n, i) => {
              const angle = (i / Math.max(count, 1)) * Math.PI * 2 - Math.PI / 2;
              const px = Math.cos(angle) * NODE_RADIUS;
              const py = Math.sin(angle) * NODE_RADIUS;
              return (
                <motion.span
                  key={n.id}
                  className="core__node"
                  initial={{ x: px, y: py, scale: 0.5, opacity: 0 }}
                  animate={{ x: 0, y: 0, scale: [0.7, 1, 0.35], opacity: [0, 1, 0] }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 1.15, ease: "easeInOut" }}
                >
                  <span className="core__node-label">{n.label}</span>
                </motion.span>
              );
            })}
          </div>
        )}
      </AnimatePresence>

      <span className="core__caption">{CAPTIONS[state]}</span>
    </div>
  );
}
