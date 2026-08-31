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
from ..memory.correction import MemoryCorrectionService, is_correction
from ..memory.guard import MemoryAttributionGuard, has_verified_support
from ..memory.models import Memory
from ..memory.provenance import (
    AUDIT_MEMORY_CLAIM_UNSUPPORTED,
    NO_RELIABLE_MEMORY_REPLY,
    is_memory_probe,
    memory_debug_emit,
    memory_debug_enabled,
)
from ..memory.retrieval import build_context as build_memory_context, memory_debug_trace
from ..memory.router import (
    MEMORY_ARCHIVE,
    MEMORY_CORRECT,
    MEMORY_CREATE,
    MEMORY_READ,
    MEMORY_SEARCH,
    MEMORY_UPDATE,
    detect_memory_intent,
)
from ..memory.service import MemoryService
from ..planner import build_plan, is_plan_request
from .context import AppContext, build_context
from .schemas import ChatRequest, MemoryCreateRequest, MemoryQueryRequest, MemoryUpdateRequest

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
        "source_type": m.source_type,
        "source_role": m.source_role,
        "confidence": m.confidence,
        "verified": m.verified,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
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


def _emit_debug(matches: list[Any]) -> None:
    """YU_MEMORY_DEBUG=1 时打印检索溯源（不含 API Key / Secret）。"""
    import sys

    print(memory_debug_trace(matches), file=sys.stderr)


def _chat_correction(ctx: AppContext, message: str) -> dict[str, Any]:
    """用户纠正（「我没说过……」）→ MemoryCorrectionService。"""
    service = MemoryCorrectionService(ctx.memory, ctx.audit)
    result = service.handle_correction(message)
    if result.kind == "invalidated":
        reply = f"明白了，我已作废这条错误记忆（{result.target_memory_id}）。"
    else:
        reply = NO_RELIABLE_MEMORY_REPLY
    return _reply("chat", reply, memory_correction=result.kind)


def _format_create_reply(result) -> str:
    if result.success:
        return f"已保存。Memory ID: {result.memory_id}"
    return "保存失败：" + result.reason


def _format_memory_list(memories: list[Memory]) -> str:
    if not memories:
        return "（暂无记忆）"
    return "\n".join(f"[{m.id}] ({m.source_type}) {m.content}" for m in memories)


def _format_retrieval_list(matches: list[Any]) -> str:
    if not matches:
        return "（未检索到相关记忆）"
    return "\n".join(f"[{m.id}] {m.content}" for m, _ in matches)


def _chat_memory_command(ctx: AppContext, intent, referenced_ids: list[int]) -> dict[str, Any]:
    """Explicit Memory Command -> MemoryService（确定性，不依赖 LLM）。"""
    service = MemoryService(ctx.memory, ctx.audit)
    kind = intent.intent

    memory_debug_emit(
        INPUT=intent.payload, INTENT=kind, ROUTER_RESULT="memory-pipeline",
        REFERENCED_MEMORY_IDS=list(referenced_ids or []),
    )

    if kind == MEMORY_CREATE:
        result = service.create(intent.payload)
        return _reply(
            "chat", _format_create_reply(result),
            intent=MEMORY_CREATE, memory_result=result.to_dict(),
        )

    if kind == MEMORY_UPDATE:
        resolution = service.resolve_reference(referenced_ids, ctx.memory.list_memories())
        if resolution.memory_id is None:
            return _reply("chat", resolution.reason, intent=MEMORY_UPDATE)
        result = service.update(resolution.memory_id, intent.payload)
        reply = "已更新。" if result.success else "修改失败：" + result.reason
        return _reply("chat", reply, intent=MEMORY_UPDATE, memory_result=result.to_dict())

    if kind == MEMORY_ARCHIVE:
        resolution = service.resolve_reference(referenced_ids, ctx.memory.list_memories())
        if resolution.memory_id is None:
            return _reply("chat", resolution.reason, intent=MEMORY_ARCHIVE)
        result = service.archive(resolution.memory_id)
        reply = "已归档（不再参与检索）。" if result.success else "归档失败：" + result.reason
        return _reply("chat", reply, intent=MEMORY_ARCHIVE, memory_result=result.to_dict())

    if kind == MEMORY_CORRECT:
        result = service.correct(intent.payload)
        if result.kind == "invalidated":
            reply = f"明白了，我已作废这条错误记忆（{result.target_memory_id}）。"
        else:
            reply = NO_RELIABLE_MEMORY_REPLY
        return _reply("chat", reply, memory_correction=result.kind, intent=MEMORY_CORRECT)

    if kind == MEMORY_READ:
        return _reply("chat", _format_memory_list(ctx.memory.list_memories()), intent=MEMORY_READ)

    if kind == MEMORY_SEARCH:
        matches = ctx.memory.retrieve(intent.payload, limit=8)
        retrieved = [{"memory": _mem(m), "score": s} for m, s in matches]
        return _reply(
            "chat", _format_retrieval_list(matches),
            retrieved=retrieved, intent=MEMORY_SEARCH,
        )

    return _chat_memory(ctx, intent.payload, [])


def _chat_memory(ctx: AppContext, message: str, history: list[Any]) -> dict[str, Any]:
    """默认对话：检索长期记忆 -> 注入上下文 -> 经 Yu Core 调用 LLM。"""
    # 1. 用户纠正错误记忆（Correction Flow）。
    if is_correction(message):
        return _chat_correction(ctx, message)

    # 2. No-Evidence Question（「我以前说过 X 吗？」）——无 verified 支撑时确定性回答。
    if is_memory_probe(message):
        verified = ctx.memory.list_verified_memories()
        if not has_verified_support(message, verified):
            return _reply("chat", NO_RELIABLE_MEMORY_REPLY, memory_probe=True)

    matches = ctx.memory.retrieve(message, limit=5)
    retrieved = [{"memory": _mem(m), "score": s} for m, s in matches]

    if memory_debug_enabled():
        memory_debug_emit(
            INPUT=message, INTENT="GENERAL_CHAT", ROUTER_RESULT="memory-search",
            RETRIEVED_MEMORY_IDS=[m.id for m, _ in matches],
            SOURCE_TYPES=[m.source_type for m, _ in matches],
        )
        _emit_debug(matches)

    if ctx.provider is None:
        return _reply(
            "chat",
            "未配置 LLM Provider（缺少 DEEPSEEK_API_KEY）。我已检索到相关长期记忆，但无法生成回答。",
            retrieved=retrieved,
        )

    context_text = build_memory_context(matches)
    request_messages: list[ChatMessage] = [ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT)]
    if context_text:
        request_messages.append(ChatMessage(role="system", content=context_text))
    for m in history[-20:]:
        role = m.role if m.role in ("user", "assistant") else "user"
        request_messages.append(ChatMessage(role=role, content=m.content))
    request_messages.append(ChatMessage(role="user", content=message))

    if memory_debug_enabled():
        memory_debug_emit(FINAL_LLM_CONTEXT=context_text or "(no memory context)")

    try:
        reply = ctx.provider.chat(request_messages)
    except LLMError as e:
        return _reply("error", f"[错误] {e}", retrieved=retrieved, reason=str(e))

    # 3. Attribution Guard：检测回复中的历史归因是否有 verified 证据。
    verdict = MemoryAttributionGuard().check(reply.content, [m for m, _ in matches])
    claims = [
        {"text": c, "supported": c not in verdict.unsupported_claims}
        for c in verdict.claims
    ]
    if verdict.needs_block:
        ctx.audit.record(
            event_type=AUDIT_MEMORY_CLAIM_UNSUPPORTED,
            actor="yu",
            reason="回复包含无 verified 记忆支撑的历史归因",
            metadata={"unsupported_claims": verdict.unsupported_claims},
        )
    return _reply("chat", reply.content, retrieved=retrieved, memory_claims=claims)


def _reply(
    kind: str,
    reply: str,
    retrieved: list[dict[str, Any]] | None = None,
    allowed: bool = True,
    reason: str = "",
    memory_claims: list[dict[str, Any]] | None = None,
    memory_correction: str = "",
    memory_probe: bool = False,
    intent: str = "",
    memory_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "reply": reply,
        "retrieved": retrieved or [],
        "allowed": allowed,
        "reason": reason,
        "memory_claims": memory_claims or [],
        "memory_correction": memory_correction,
        "memory_probe": memory_probe,
        "intent": intent,
        "memory_result": memory_result,
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
        verified = sum(1 for m in ms if m.verified)
        return {
            "total": len(ms),
            "active": active,
            "archived": len(ms) - active,
            "verified": verified,
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

    @app.post("/api/memories")
    async def create_memory(request: Request, body: MemoryCreateRequest) -> dict[str, Any]:
        ctx = _ctx(request)
        result = MemoryService(ctx.memory, ctx.audit).create(body.content, body.type, body.importance)
        memory = ctx.memory.get_memory(result.memory_id) if result.success and result.memory_id else None
        return {"result": result.to_dict(), "memory": _mem(memory) if memory else None}

    @app.post("/api/memories/{memory_id}/update")
    async def update_memory(request: Request, memory_id: int, body: MemoryUpdateRequest) -> dict[str, Any]:
        ctx = _ctx(request)
        result = MemoryService(ctx.memory, ctx.audit).update(memory_id, body.content)
        memory = ctx.memory.get_memory(memory_id)
        return {"result": result.to_dict(), "memory": _mem(memory) if memory else None}

    @app.post("/api/memories/{memory_id}/archive")
    async def archive_memory(request: Request, memory_id: int) -> dict[str, Any]:
        ctx = _ctx(request)
        result = MemoryService(ctx.memory, ctx.audit).archive(memory_id)
        memory = ctx.memory.get_memory(memory_id)
        return {"result": result.to_dict(), "memory": _mem(memory) if memory else None}

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

        # 1. Explicit Memory Command 优先（Explicit Intent > Inferred Routing）。
        intent = detect_memory_intent(message)
        if intent is not None:
            return _chat_memory_command(ctx, intent, body.referenced_memory_ids)

        if is_plan_request(message):
            return _chat_plan(ctx, message)
        if is_computer_request(message):
            return _chat_computer(ctx, message)
        return _chat_memory(ctx, message, body.history)

    _mount_spa(app)
    return app