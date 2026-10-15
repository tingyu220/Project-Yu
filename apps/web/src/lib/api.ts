// 轻量 API 客户端。开发时经 Vite 代理 /api -> Yu API；生产时同源。
import type {
  ChatResponse,
  HistoryMessage,
  Memory,
  MemoryResult,
  MemoryStats,
  RetrievalMatch,
  StatusResponse,
  SystemStatusResponse,
  TodayResponse,
  ConversationTurn,
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

export interface MemoryWriteResponse {
  result: MemoryResult;
  memory: Memory | null;
}

export const api = {
  conversation: () => get<{session_id: string}>("/api/conversation"),
  conversationChanges: (after: number, signal?: AbortSignal) => request<{turns: ConversationTurn[]; next_cursor: number; has_more: boolean}>("/api/conversation/turns?after=" + after, {signal}),
  status: () => get<StatusResponse>("/api/status"),
  today: () => get<TodayResponse>("/api/today"),
  memories: (limit = 150) =>
    get<{ memories: Memory[]; total: number }>("/api/memories?limit=" + limit),
  memoryStats: () => get<MemoryStats>("/api/memory/stats"),
  systemStatus: () => get<SystemStatusResponse>("/api/system/status"),
  queryMemories: (query: string, limit = 8) =>
    post<{ query: string; matches: RetrievalMatch[] }>("/api/memories/query", { query, limit }),
  createMemory: (content: string, type = "fact", importance = "high") =>
    post<MemoryWriteResponse>("/api/memories", { content, type, importance }),
  updateMemory: (id: number, content: string) =>
    post<MemoryWriteResponse>("/api/memories/" + id + "/update", { content }),
  archiveMemory: (id: number) =>
    post<MemoryWriteResponse>("/api/memories/" + id + "/archive", {}),
  chat: (message: string, history: HistoryMessage[] = [], referencedMemoryIds?: number[], sessionId?: string, requestId?: string, source: "web" | "local_voice" = "web") =>
    post<ChatResponse>("/api/chat", { message, history, referenced_memory_ids: referencedMemoryIds, session_id: sessionId, request_id: requestId, source }),
};
