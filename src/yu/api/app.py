"""FastAPI Yu API — Yu Core 与 apps/web 之间的桥梁（Interface Layer）。

原则（见 DECISIONS.md D020）：
- apps/web 只能通过本 API 使用 Yu 能力，不能直接读 SQLite / 内部 Python 文件。
- Frontend 不直接调用 DeepSeek；Chat 经由 Yu Core -> LLM Provider -> DeepSeek。
- API 不绕过 Safety Kernel；system.status.read 等能力仍经 Safety Kernel 评估。
- Yu Core 不依赖 Web 才能运行。

运行：
    python -m yu.api            # 默认 http://127.0.0.1:8787
    环境变量 YU_API_HOST / YU_API_PORT 可覆盖。

注意：端点均为 async def，使 SQLite 访问保持在 lifespan 所在的事件循环线程
（Yu Core 的 SQLite 连接默认 check_same_thread=True）；本地单用户场景下，
阻塞式 LLM/psutil 调用短暂占用事件循环可接受。
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..actions.models import ProposedAction
from ..computer import (
    build_computer_advice,
    format_status,
    is_computer_request,
    read_computer_status,
)
from ..daily import today_date
from ..entities.models import Decision, Goal, Project, Task
from ..llm import ChatMessage, LLMError
from ..llm.conversation import DEFAULT_SYSTEM_PROMPT
from ..memory.models import Memory
from ..memory.retrieval import build_context
from ..planner import build_plan, is_plan_request
from .context import AppContext, build_context
from .schemas import ChatRequest, MemoryQueryRequest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DIST = _REPO_ROOT / "apps" / "web" / "dist"

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


# ------------------------------------------------------------------ serializers

def _mem(m: Memory) -> dict[str, Any]:
    return {
        "id": m.id,
        "type": m.type,
        "content": m.content,
        "importance": m.importance,
        "status": m.status,
        "source_event_id": m.source_event_id,
        "created_at": m.created_at,
        "archived_at": m.archived_at,
    }


def _goal(g: Goal) -> dict[str, Any]:
    return {
        "id": g.id, "title": g.title, "status": g.status,
        "created_at": g.created_at, "updated_at": g.updated_at,
    }


def _task(t: Task) -> dict[str, Any]:
    return {
        "id": t.id, "title": t.title, "status": t.status, "priority": t.priority,
        "due_date": t.due_date, "related_goal": t.related_goal,
        "related_project": t.related_project,
        "created_at": t.created_at, "updated_at": t.updated_at,
    }


def _project(p: Project) -> dict[str, Any]:
    return {
        "id": p.id, "name": p.name, "status": p.status,
        "current_goal": p.current_goal, "next_step": p.next_step, "notes": p.notes,
        "created_at": p.created_at, "updated_at": p.updated_at,
    }


def _decision(d: Decision) -> dict[str, Any]:
    return {
        "id": d.id, "decision": d.decision, "reason": d.reason,
        "constraints": d.constraints, "alternatives": d.alternatives,
        "created_at": d.created_at,
    }


def _top_priority(ctx: AppContext) -> dict[str, Any] | None:
    """首页「今天最重要的一件事」：未完成任务(按优先级) > 活跃目标 > 项目下一步。"""
    tasks = [t for t in ctx.entities.list_tasks() if t.status != "done"]
    tasks.sort(key=lambda t: (_PRIORITY_RANK.get(t.priority, 1), t.id))
    if tasks:
        t = tasks[0]
        return {"kind": "task", "title": t.title, "priority": t.priority, "id": t.id}
    goals = [g for g in ctx.entities.list_goals() if g.status == "active"]
    if goals:
        return {"kind": "goal", "title": goals[0].title, "priority": "high", "id": goals[0].id}
    projects = ctx.entities.list_projects()
    if projects:
        p = projects[0]
        return {"kind": "project", "title": p.next_step or p.name, "priority": "medium", "id": p.id}
    return None


# ------------------------------------------------------------------ chat helpers

def _chat_plan(ctx: AppContext, message: str) -> dict[str, Any]:
    if ctx.provider is None:
        return _reply("plan", "未配置 LLM Provider（缺少 DEEPSEEK_API_KEY），无法规划。")
    if not ctx.entities.list_goals() and not ctx.entities.list_tasks() and not ctx.entities.list_projects():
        return _reply("plan", "暂无目标 / 任务 / 项目。请先用 目标：/ 任务：/ 项目： 记录一些，再让我规划。")
    try:
        plan = build_plan(ctx.memory, ctx.entities, ctx.provider)
    except LLMError as e:
        return _reply("error", f"[错误] {e}", reason=str(e))
    return _reply("plan", plan)


def _chat_computer(ctx: AppContext, message: str) -> dict[str, Any]:
    action = ProposedAction(
        action_id="api-chat-computer",
        action_type="system.status.read",
        description="读取电脑状态并分析",
        requested_by="owner",
        proposed_by="yu",
        required_capability="system.status.read",
        reason="用户请求电脑状态分析",
    )
    decision = ctx.kernel.evaluate(action)
    if not decision.allowed:
        return _reply("computer", f"[拒绝] {decision.reason}", allowed=False, reason=decision.reason)
    status = read_computer_status()
    if ctx.provider is None:
        return _reply("computer", format_status(status))
    try:
        advice = build_computer_advice(ctx.provider, status)
    except LLMError as e:
        return _reply("error", f"[错误] {e}", reason=str(e))
    return _reply("computer", advice)


def _chat_memory(ctx: AppContext, message: str, history: list[Any]) -> dict[str, Any]:
    """默认对话：检索长期记忆 -> 注入上下文 -> 经 Yu Core 调用 LLM。"""
    matches = ctx.memory.retrieve(message, limit=5)
    retrieved = [{"memory": _mem(m), "score": s} for m, s in matches]

    if ctx.provider is None:
        return _reply(
            "chat",
            "未配置 LLM Provider（缺少 DEEPSEEK_API_KEY）。我已检索到相关长期记忆，但无法生成回答。",
            retrieved=retrieved,
        )

    context_text = build_context(matches)
    request_messages: list[ChatMessage] = [ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT)]
    if context_text:
        request_messages.append(ChatMessage(role="system", content=context_text))
    for m in history[-20:]:
        role = m.role if m.role in ("user", "assistant") else "user"
        request_messages.append(ChatMessage(role=role, content=m.content))
    request_messages.append(ChatMessage(role="user", content=message))

    try:
        reply = ctx.provider.chat(request_messages)
    except LLMError as e:
        return _reply("error", f"[错误] {e}", retrieved=retrieved, reason=str(e))
    return _reply("chat", reply.content, retrieved=retrieved)


def _reply(
    kind: str,
    reply: str,
    retrieved: list[dict[str, Any]] | None = None,
    allowed: bool = True,
    reason: str = "",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "reply": reply,
        "retrieved": retrieved or [],
        "allowed": allowed,
        "reason": reason,
    }


# ------------------------------------------------------------------ app

def _mount_spa(app: FastAPI) -> None:
    """如果 apps/web 已构建，则让 FastAPI 同时提供前端静态资源（单进程运行）。"""
    dist = Path(os.environ.get("YU_WEB_DIST", str(_DEFAULT_DIST)))
    if not (dist / "index.html").exists():
        return
    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ctx = build_context()
        try:
            yield
        finally:
            app.state.ctx.close()

    app = FastAPI(title="Yu API", version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _ctx(request: Request) -> AppContext:
        return request.app.state.ctx

    # ------------------------------------------------------------------ status

    @app.get("/api/status")
    async def status(request: Request) -> dict[str, Any]:
        ctx = _ctx(request)
        return {
            "name": "Yu",
            "version": __version__,
            "safety": ctx.kernel.status(),
            "llm": {"available": ctx.provider is not None, "error": ctx.provider_error},
        }

    # ------------------------------------------------------------------ today

    @app.get("/api/today")
    async def today(request: Request) -> dict[str, Any]:
        ctx = _ctx(request)
        goals = ctx.entities.list_goals()
        tasks = ctx.entities.list_tasks()
        projects = ctx.entities.list_projects()
        memories = ctx.memory.list_memories()
        open_tasks = [t for t in tasks if t.status != "done"]
        done_tasks = [t for t in tasks if t.status == "done"]
        log = ctx.daily.get(today_date())
        return {
            "date": today_date(),
            "memory_count": len(memories),
            "goals": [_goal(g) for g in goals if g.status != "archived"],
            "tasks": {"open": [_task(t) for t in open_tasks], "done": [_task(t) for t in done_tasks]},
            "projects": [_project(p) for p in projects],
            "top_priority": _top_priority(ctx),
            "daily_summary": log.content if log else None,
        }

    @app.get("/api/goals")
    async def goals(request: Request) -> dict[str, Any]:
        return {"goals": [_goal(g) for g in _ctx(request).entities.list_goals()]}

    @app.get("/api/tasks")
    async def tasks(request: Request) -> dict[str, Any]:
        return {"tasks": [_task(t) for t in _ctx(request).entities.list_tasks()]}

    # ------------------------------------------------------------------ memories

    @app.get("/api/memories")
    async def memories(request: Request, limit: int = 150) -> dict[str, Any]:
        ms = _ctx(request).memory.list_memories()
        return {"memories": [_mem(m) for m in ms[:limit]], "total": len(ms)}

    @app.get("/api/memories/recent")
    async def memories_recent(request: Request, limit: int = 20) -> dict[str, Any]:
        ms = _ctx(request).memory.list_memories()
        recent = list(reversed(ms))[:limit]  # list_memories 按 id 升序 -> 反转取最新
        return {"memories": [_mem(m) for m in recent]}

    @app.get("/api/memory/stats")
    async def memory_stats(request: Request) -> dict[str, Any]:
        ms = _ctx(request).memory.list_memories(include_archived=True)
        by_type: dict[str, int] = {}
        by_importance: dict[str, int] = {}
        for m in ms:
            by_type[m.type] = by_type.get(m.type, 0) + 1
            by_importance[m.importance] = by_importance.get(m.importance, 0) + 1
        active = sum(1 for m in ms if m.status == "active")
        return {
            "total": len(ms),
            "active": active,
            "archived": len(ms) - active,
            "by_type": by_type,
            "by_importance": by_importance,
        }

    @app.post("/api/memories/query")
    async def memory_query(request: Request, body: MemoryQueryRequest) -> dict[str, Any]:
        ctx = _ctx(request)
        matches = ctx.memory.retrieve(body.query, limit=body.limit)
        return {
            "query": body.query,
            "matches": [{"memory": _mem(m), "score": s} for m, s in matches],
        }

    # ------------------------------------------------------------------ system

    @app.get("/api/system/status")
    async def system_status(request: Request) -> dict[str, Any]:
        ctx = _ctx(request)
        action = ProposedAction(
            action_id="api-system-status",
            action_type="system.status.read",
            description="读取电脑状态（Web API）",
            requested_by="owner",
            proposed_by="yu",
            required_capability="system.status.read",
            reason="用户请求电脑状态",
        )
        decision = ctx.kernel.evaluate(action)
        if not decision.allowed:
            return {"allowed": False, "reason": decision.reason, "status": None}
        s = read_computer_status()
        return {"allowed": True, "reason": decision.reason, "status": s.__dict__}

    # ------------------------------------------------------------------ chat

    @app.post("/api/chat")
    async def chat(request: Request, body: ChatRequest) -> dict[str, Any]:
        ctx = _ctx(request)
        message = body.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="message 不能为空")

        if is_plan_request(message):
            return _chat_plan(ctx, message)
        if is_computer_request(message):
            return _chat_computer(ctx, message)
        return _chat_memory(ctx, message, body.history)

    _mount_spa(app)
    return app
