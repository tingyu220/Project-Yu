import { useReducedMotion } from "../lib/useReducedMotion";
import type { YuUIState } from "../lib/types";

interface CoreProps {
  state: YuUIState;
  compact?: boolean;
}

/** Yu Core —— 纯视觉智能核心：Sphere + Glow + Halo，只表达 Presence / State / Energy，不承担文字。 */
export default function Core({ state, compact = false }: CoreProps) {
  const reduced = useReducedMotion();
  const remembering = state === "remembering" && !reduced;

  return (
    <div className={"core" + (compact ? " core--compact" : "") + " core--" + state} aria-hidden="true">
      <div className="core__halo" />
      <div className="core__glow" />
      <div className="core__sphere" />
      {remembering && <div className="core__ring" />}
    </div>
  );
}
