"""共享会话的串行执行队列与 request_id 幂等边界。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from .store import ConversationStore


class SessionConflict(ValueError):
    """同一 request_id 携带了不同消息。"""


class QueueCapacityError(RuntimeError):
    """共享会话等待队列已满。"""


class ConversationService:
    def __init__(self, store: ConversationStore,
                 handler: Callable[[str, list[dict[str, str]], list[int]], Awaitable[dict[str, Any]]]):
        self.store = store
        self.handler = handler
        self._lock = asyncio.Lock()
        self._execution_lock = asyncio.Lock()
        self._active: asyncio.Task | None = None
        self._pending: list[asyncio.Task] = []
        self._closed = False

    async def submit(self, session_id: str, request_id: str, source: str, message: str,
                     references: list[int] | None = None) -> dict[str, Any]:
        wait_task = None
        async with self._lock:
            existing = self.store.get_request(session_id, request_id)
            if existing:
                if existing.message != message or existing.source != source:
                    raise SessionConflict("request_id 已用于其他消息")
                if existing.state == "completed":
                    return self._result(existing)
                if existing.state in {"failed", "unknown"}:
                    return self._result(existing)
                task = next((task for task in [self._active, *self._pending]
                             if task and getattr(task, "turn_seq", None) == existing.seq), None)
                if task:
                    wait_task = task
                else:
                    raise RuntimeError("该请求状态未知，不会自动重发")
            elif self._closed:
                raise RuntimeError("共享会话已关闭")
            elif len(self._pending) >= 3:
                raise QueueCapacityError("共享会话等待队列已满")
            else:
                turn = self.store.insert_turn(session_id, request_id, source, message)
                wait_task = asyncio.create_task(self._execute(turn.seq, session_id, message, references or []))
                wait_task.turn_seq = turn.seq
                self._pending.append(wait_task)
        try:
            return await asyncio.shield(wait_task)
        except asyncio.CancelledError:
            raise

    async def _execute(self, seq: int, session_id: str, message: str, references: list[int]) -> dict[str, Any]:
        async with self._execution_lock:
            return await self._execute_serial(seq, session_id, message, references)

    async def _execute_serial(self, seq: int, session_id: str, message: str, references: list[int]) -> dict[str, Any]:
        async with self._lock:
            current = asyncio.current_task()
            if current in self._pending:
                self._pending.remove(current)
            self._active = current
            self.store.set_state(seq, "running")
        try:
            result = await self.handler(message, self.store.history(session_id), references)
            turn = self.store.set_state(seq, "completed", result)
            return self._result(turn)
        except Exception as exc:
            result = {"reply": str(exc), "kind": "error", "allowed": False}
            self.store.set_state(seq, "failed", result)
            return result
        finally:
            async with self._lock:
                if self._active is current:
                    self._active = None

    @staticmethod
    def _result(turn) -> dict[str, Any]:
        result = dict(turn.result or {})
        result.update({"session_id": turn.session_id, "request_id": turn.request_id,
                       "seq": turn.seq, "state": turn.state})
        return result

    async def close(self) -> None:
        self._closed = True
        tasks = [task for task in [self._active, *self._pending] if task]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.store.close()
