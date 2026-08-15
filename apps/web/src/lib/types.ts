// Yu API 响应类型（与 src/yu/api/app.py 对应）。

export type Importance = "high" | "medium" | "low";

export interface Memory {
  id: number;
  type: string;
  content: string;
  importance: Importance;
  status: string;
  source_event_id: number | null;
  created_at: string;
  archived_at: string | null;
}

export interface Goal {
  id: number;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: number;
  title: string;
  status: string;
  priority: string;
  due_date: string | null;
  related_goal: number | null;
  related_project: number | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  name: string;
  status: string;
  current_goal: string | null;
  next_step: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface TopPriority {
  kind: "task" | "goal" | "project";
  title: string;
  priority: string;
  id: number;
}

export interface TodayResponse {
  date: string;
  memory_count: number;
  goals: Goal[];
  tasks: { open: Task[]; done: Task[] };
  projects: Project[];
  top_priority: TopPriority | null;
  daily_summary: string | null;
}

export interface StatusResponse {
  name: string;
  version: string;
  safety: {
    safety_kernel: string;
    owner: string;
    audit: string;
    constitution: string;
  };
  llm: { available: boolean; error: string | null };
}

export interface SystemStatus {
  cpu_percent: number;
  ram_percent: number;
  ram_total_gb: number;
  ram_used_gb: number;
  disk_percent: number;
  disk_free_gb: number;
  disk_total_gb: number;
  battery_percent: number | null;
  uptime_hours: number;
  top_processes: { name: string; memory_mb: number }[];
}

export interface SystemStatusResponse {
  allowed: boolean;
  reason: string;
  status: SystemStatus | null;
}

export interface MemoryStats {
  total: number;
  active: number;
  archived: number;
  by_type: Record<string, number>;
  by_importance: Record<string, number>;
}

export interface RetrievalMatch {
  memory: Memory;
  score: number;
}

export type ChatKind = "chat" | "plan" | "computer" | "error";

export interface ChatResponse {
  kind: ChatKind;
  reply: string;
  retrieved: RetrievalMatch[];
  allowed: boolean;
  reason: string;
}

export interface HistoryMessage {
  role: string;
  content: string;
}

// ------------------------------------------------------------------ Cockpit UI

/** Yu 的交互状态（驱动 Core 与 Cockpit 状态可视化）。 */
export type YuUIState =
  | "idle"
  | "thinking"
  | "remembering"
  | "planning"
  | "system_analysis"
  | "answering"
  | "ready"
  | "error";

/** 记住（remembering）状态下向 Core 聚合的节点提示。 */
export interface NodeHint {
  id: number;
  label: string;
}

/** 一条对话消息（user / yu）。 */
export interface Message {
  id: string;
  role: "user" | "yu";
  content: string;
  kind?: ChatKind;
  retrieved?: RetrievalMatch[];
  createdAt: number;
}
