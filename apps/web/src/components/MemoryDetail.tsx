import { motion } from "framer-motion";
import { clusterLabel, clusterOf } from "../lib/cluster";
import type { Memory } from "../lib/types";

interface Props {
  memory: Memory;
  demo: boolean;
  mask: (s: string) => string;
  onClose: () => void;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

export default function MemoryDetail({ memory, demo, mask, onClose }: Props) {
  return (
    <motion.aside
      className="memory-detail"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      role="dialog"
      aria-label="记忆详情"
    >
      <div className="md__head">
        <div className="md__title">{demo ? "Memory #" + memory.id : mask(memory.content)}</div>
        <button className="md__close" onClick={onClose} aria-label="关闭">
          ×
        </button>
      </div>
      <div className="md__badges">
        <span className="md__badge">{clusterLabel(clusterOf(memory))}</span>
        <span className={"md__badge" + (memory.importance === "high" ? " md__badge--high" : "")}>
          {memory.importance}
        </span>
      </div>
      <div className={"md__body" + (demo ? " demo-blur" : "")}>{memory.content}</div>
      <div className="md__meta">
        <div className="md__row">
          <span className="md__key">TYPE</span>
          <span className="md__val">{memory.type}</span>
        </div>
        <div className="md__row">
          <span className="md__key">CREATED</span>
          <span className="md__val">{fmtDate(memory.created_at)}</span>
        </div>
        <div className="md__row">
          <span className="md__key">STATUS</span>
          <span className="md__val">{memory.status}</span>
        </div>
      </div>
    </motion.aside>
  );
}
