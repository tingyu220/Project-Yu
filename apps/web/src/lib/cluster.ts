// Memory Universe 的星座分组：优先使用 Memory.type；type 为通用值时，
// 用真实内容的关键词做轻量话题聚类（不引入向量库 / embedding）。
import type { Memory } from "./types";

export interface ClusterDef {
  key: string;
  label: string;
  color: string;
}

export const CLUSTERS: ClusterDef[] = [
  { key: "decision", label: "决策", color: "#d9bd93" },
  { key: "project", label: "项目", color: "#e6cfa4" },
  { key: "goal", label: "目标", color: "#a9c39b" },
  { key: "computer", label: "电脑", color: "#a8b6c4" },
  { key: "personal", label: "个人", color: "#c8a3b0" },
  { key: "fact", label: "记忆", color: "#cfd2cc" },
];

const RULES: [RegExp, string][] = [
  [/决定|决策|优先|暂时|未来|不再|不开发|选择|放弃/i, "decision"],
  [/项目|project|开发|yu|版本|v0\.|集成|接口|api|前端|web|jarvis|personal ai|长期记忆/i, "project"],
  [/目标|计划|规划|任务|完成/i, "goal"],
  [/电脑|笔记本|华硕|设备|内存|磁盘|cpu|系统|卡/i, "computer"],
  [/资金|预算|成本|时间|生活|家庭|喜欢|性格|经历|我|本人/i, "personal"],
];

export function clusterOf(memory: Memory): string {
  const t = memory.type.toLowerCase();
  if (t !== "fact" && t !== "memory" && t !== "unknown" && t !== "") {
    return t;
  }
  for (const [re, key] of RULES) {
    if (re.test(memory.content)) return key;
  }
  return "fact";
}

export function clusterColor(key: string): string {
  return CLUSTERS.find((c) => c.key === key)?.color ?? "#cfd2cc";
}

export function clusterLabel(key: string): string {
  return CLUSTERS.find((c) => c.key === key)?.label ?? key;
}
