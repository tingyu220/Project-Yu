// 轻量 API 客户端。开发时经 Vite 代理 /api -> Yu API；生产时同源。
import type {
  ChatResponse,
  HistoryMessage,
  Memory,
  MemoryStats,
  RetrievalMatch,
  StatusResponse,
  SystemStatusResponse,
  TodayResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body.detail ? " — " + JSON.stringify(body.detail) : "";
    } catch {
      /* ignore */
    }
    throw new Error(path + " 请求失败（" + res.status + "）" + detail);
  }
  return (await res.json()) as T;
}

function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  status: () => get<StatusResponse>("/api/status"),
  today: () => get<TodayResponse>("/api/today"),
  memories: (limit = 150) =>
    get<{ memories: Memory[]; total: number }>("/api/memories?limit=" + limit),
  memoryStats: () => get<MemoryStats>("/api/memory/stats"),
  systemStatus: () => get<SystemStatusResponse>("/api/system/status"),
  queryMemories: (query: string, limit = 8) =>
    post<{ query: string; matches: RetrievalMatch[] }>("/api/memories/query", { query, limit }),
  chat: (message: string, history: HistoryMessage[] = []) =>
    post<ChatResponse>("/api/chat", { message, history }),
};
