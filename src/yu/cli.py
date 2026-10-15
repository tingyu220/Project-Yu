"""Command-line interface for Yu (v0.0.7: Computer Context).

Usage:
    python -m yu.cli

Commands:
    记住：<内容>   记录一条事实（同时创建 Event 与 Memory）
    记忆           列出所有有效记忆
    目标：<标题>   新建目标；目标 列出目标；完成目标 <id>
    任务：<标题>   新建任务；任务 列出任务；完成任务 <id>
    项目：<名称>   新建项目；项目 列出项目
    决策：<内容>   记录决策；决策 列出决策
    规划           生成今日计划（也可直接问「我今天应该干什么」）
    总结           生成并保存今日 Daily Summary
    日报           列出已保存的 Daily Summary
    电脑状态       读取电脑状态并分析（也可问「我电脑为什么卡」）
    权限           查看当前 Permission
    安全状态       查看 Safety Kernel 状态
    审计           查看最近安全审计事件
    重置           清空当前对话
    exit           停止 Yu（受 Owner 停止权保护，不可被拒绝）
    其他输入       作为对话发送给 LLM（多轮）
"""

from __future__ import annotations

import os

from . import __version__
from .actions.models import ProposedAction
from .actions.service import build_action_service
from .audit.store import AuditStore
from .computer import build_computer_advice, format_status, is_computer_request, read_computer_status
from .authority.owner import OwnerManager
from .authority.shutdown import ShutdownController
from .daily import DailyLogStore, build_daily_summary, today_date
from .entities.store import EntitiesStore
from .llm import ChatMessage, Conversation, LLMError, create_provider
from .memory.correction import MemoryCorrectionService, is_correction
from .memory.guard import MemoryAttributionGuard, has_verified_support
from .memory.provenance import (
    AUDIT_MEMORY_CLAIM_UNSUPPORTED,
    NO_RELIABLE_MEMORY_REPLY,
    is_memory_probe,
    memory_debug_enabled,
)
from .memory.retrieval import build_context, memory_debug_trace
from .memory.router import (
    MEMORY_ARCHIVE,
    MEMORY_CORRECT,
    MEMORY_CREATE,
    MEMORY_READ,
    MEMORY_SEARCH,
    MEMORY_UPDATE,
    detect_memory_intent,
)
from .memory.service import MemoryService
from .memory.store import MemoryStore
from .planner import build_plan, is_plan_request
from .safety.constitution import SafetyConstitution
from .safety.kernel import SafetyKernel
from .safety.permissions import PermissionEngine
from .safety.risk import KNOWN_CAPABILITIES

DEFAULT_DB_PATH = os.environ.get("YU_DB_PATH", "data/yu.db")
DEFAULT_AUDIT_DB = os.environ.get("YU_AUDIT_DB", "data/audit.db")
DEFAULT_CONSTITUTION_PATH = os.environ.get("YU_CONSTITUTION_PATH", "config/safety_constitution.yaml")
DEFAULT_OWNER_PATH = os.environ.get("YU_OWNER_PATH", "config/owner.yaml")

_PROMPT = "> "

_SHUTDOWN_COMMANDS = {"exit", "quit", "shutdown", "关闭", "关闭yu", "关闭 yu"}


def _normalize_command(command: str) -> str:
    return command.strip().rstrip("。.!！？?").strip().lower()


def _print_banner() -> None:
    print(f"宇 Yu v{__version__}")


def main(argv: list[str] | None = None) -> int:
    del argv
    _print_banner()

    store = MemoryStore(DEFAULT_DB_PATH)
    entities = EntitiesStore(DEFAULT_DB_PATH)
    daily = DailyLogStore(DEFAULT_DB_PATH)
    audit = AuditStore(DEFAULT_AUDIT_DB)
    owner = OwnerManager(DEFAULT_OWNER_PATH)
    constitution = SafetyConstitution(DEFAULT_CONSTITUTION_PATH)
    owner_id = owner.owner.owner_id if owner.owner is not None else "unknown"
    permissions = PermissionEngine(owner_id, audit)
    kernel = SafetyKernel(constitution, permissions, owner, audit)
    action_service = build_action_service(kernel, audit)
    shutdown = ShutdownController(audit)
    provider = _build_provider()
    conversation = Conversation()
    last_ref: list[int] = []

    try:
        while True:
            try:
                line = input(_PROMPT)
            except EOFError:
                print()
                break
            command = line.strip()
            if not command:
                continue
            if _normalize_command(command) in _SHUTDOWN_COMMANDS:
                shutdown.request_shutdown("owner requested shutdown: " + command)
                break
            if command == "记忆":
                _show_memories(store)
            elif command == "重置":
                conversation.clear()
                print("对话已重置。")
            elif command == "权限":
                _show_permissions(permissions)
            elif command == "安全状态":
                _show_safety_status(kernel)
            elif command == "审计":
                _show_audit(audit)
            elif command == "目标":
                _show_goals(entities)
            elif command.startswith("目标："):
                _add_goal(entities, command[len("目标："):].strip())
            elif command.startswith("完成目标 "):
                _complete_goal(entities, command[len("完成目标 "):].strip())
            elif command == "任务":
                _show_tasks(entities)
            elif command.startswith("任务："):
                _add_task(entities, command[len("任务："):].strip())
            elif command.startswith("完成任务 "):
                _complete_task(entities, command[len("完成任务 "):].strip())
            elif command == "项目":
                _show_projects(entities)
            elif command.startswith("项目："):
                _add_project(entities, command[len("项目："):].strip())
            elif command == "决策":
                _show_decisions(entities)
            elif command.startswith("决策："):
                _add_decision(entities, command[len("决策："):].strip())
            elif command in ("规划", "今日计划", "计划"):
                _plan(store, entities, provider)
            elif command == "总结":
                _do_summary(store, entities, daily, provider)
            elif command == "日报":
                _show_daily_logs(daily)
            elif command in ("电脑状态", "系统状态"):
                _computer_status(kernel, provider)
            else:
                action_result = action_service.handle(command)
                if action_result is not None:
                    print(action_result.message)
                else:
                    intent = detect_memory_intent(command)
                    if intent is not None:
                        _memory_command(store, audit, intent, last_ref)
                    elif is_plan_request(command):
                        _plan(store, entities, provider)
                    elif is_computer_request(command):
                        _computer_status(kernel, provider)
                    else:
                        _chat(store, provider, conversation, command, audit, last_ref)
    finally:
        store.close()
        entities.close()
        daily.close()
        audit.close()
    return 0


def _build_provider():
    try:
        return create_provider()
    except LLMError as e:
        print(f"[警告] {e}")
        print("未配置 LLM，本轮仅支持本地命令（记住：/ 记忆 / 目标 / 任务 / 项目 / 决策 / 权限 / 安全状态 / 审计 / 重置 / exit）。")
        return None


def _chat(store: MemoryStore, provider, conversation: Conversation, text: str, audit=None, last_ref=None) -> None:
    # 1. 用户纠正（Correction Flow）。
    if is_correction(text) and audit is not None:
        result = MemoryCorrectionService(store, audit).handle_correction(text)
        if result.kind == "invalidated":
            print(f"明白了，我已作废这条错误记忆（{result.target_memory_id}）。")
        else:
            print(NO_RELIABLE_MEMORY_REPLY)
        return

    # 2. No-Evidence Question 确定性回答。
    if is_memory_probe(text):
        if not has_verified_support(text, store.list_verified_memories()):
            print(NO_RELIABLE_MEMORY_REPLY)
            return

    if provider is None:
        print("未配置 LLM Provider（缺少 DEEPSEEK_API_KEY），无法对话。")
        return

    matches = store.retrieve(text, limit=5)
    if last_ref is not None:
        last_ref[:] = [m.id for m, _ in matches]
    if memory_debug_enabled():
        import sys
        print(memory_debug_trace(matches), file=sys.stderr)

    context = build_context(matches)
    base = conversation.as_messages()
    request = [base[0]]
    if context:
        request.append(ChatMessage(role="system", content=context))
    request.extend(base[1:])
    request.append(ChatMessage(role="user", content=text))
    try:
        reply = provider.chat(request)
    except LLMError as e:
        print(f"[错误] {e}")
        return

    # 3. Attribution Guard：无证据的历史归因记入审计。
    verdict = MemoryAttributionGuard().check(reply.content, [m for m, _ in matches])
    if verdict.needs_block and audit is not None:
        audit.record(
            event_type=AUDIT_MEMORY_CLAIM_UNSUPPORTED,
            actor="yu",
            reason="回复包含无 verified 记忆支撑的历史归因",
            metadata={"unsupported_claims": verdict.unsupported_claims},
        )

    conversation.add_user(text)
    conversation.add_assistant(reply.content)
    print(reply.content)


def _plan(store: MemoryStore, entities: EntitiesStore, provider) -> None:
    if provider is None:
        print("未配置 LLM Provider（缺少 DEEPSEEK_API_KEY），无法规划。")
        return
    if not entities.list_goals() and not entities.list_tasks() and not entities.list_projects():
        print("暂无目标 / 任务 / 项目。请先用 目标：/ 任务：/ 项目： 记录一些，再让我规划。")
        return
    try:
        plan = build_plan(store, entities, provider)
    except LLMError as e:
        print(f"[错误] {e}")
        return
    print(plan)


def _do_summary(store: MemoryStore, entities: EntitiesStore, daily: DailyLogStore, provider) -> None:
    if provider is None:
        print("未配置 LLM Provider（缺少 DEEPSEEK_API_KEY），无法总结。")
        return
    try:
        summary = build_daily_summary(store, entities, provider)
    except LLMError as e:
        print(f"[错误] {e}")
        return
    daily.save(today_date(), summary)
    print(summary)


def _show_daily_logs(daily: DailyLogStore) -> None:
    logs = daily.list_logs()
    if not logs:
        print("（暂无日报）")
        return
    for lg in logs:
        first = lg.content.splitlines()[0] if lg.content else ""
        print(f"[{lg.date}] {first}")


def _computer_status(kernel: SafetyKernel, provider) -> None:
    action = ProposedAction(
        action_id="computer-status",
        action_type="system.status.read",
        description="读取电脑状态",
        requested_by="owner",
        proposed_by="yu",
        required_capability="system.status.read",
        reason="用户请求电脑状态分析",
    )
    decision = kernel.evaluate(action)
    if not decision.allowed:
        print(f"[拒绝] {decision.reason}")
        return
    try:
        status = read_computer_status()
    except Exception as e:
        print(f"[错误] 读取电脑状态失败：{e}")
        return
    if provider is None:
        print(format_status(status))
        return
    try:
        advice = build_computer_advice(provider, status)
    except LLMError as e:
        print(f"[错误] {e}")
        return
    print(advice)


def _memory_command(store: MemoryStore, audit: AuditStore, intent, last_ref: list[int]) -> None:
    """确定性 Memory 命令 -> MemoryService（不依赖 LLM）。"""
    service = MemoryService(store, audit)
    kind = intent.intent

    if kind == MEMORY_CREATE:
        result = service.create(intent.payload)
        if result.success:
            print(f"已保存。Memory ID: {result.memory_id}")
        else:
            print("保存失败：" + result.reason)
    elif kind == MEMORY_UPDATE:
        resolution = service.resolve_reference(last_ref, store.list_memories())
        if resolution.memory_id is None:
            print(resolution.reason)
            return
        result = service.update(resolution.memory_id, intent.payload)
        print("已更新。" if result.success else "修改失败：" + result.reason)
    elif kind == MEMORY_ARCHIVE:
        resolution = service.resolve_reference(last_ref, store.list_memories())
        if resolution.memory_id is None:
            print(resolution.reason)
            return
        result = service.archive(resolution.memory_id)
        print("已归档（不再参与检索）。" if result.success else "归档失败：" + result.reason)
    elif kind == MEMORY_CORRECT:
        result = service.correct(intent.payload)
        if result.kind == "invalidated":
            print(f"明白了，我已作废这条错误记忆（{result.target_memory_id}）。")
        else:
            print(NO_RELIABLE_MEMORY_REPLY)
    elif kind == MEMORY_READ:
        _show_memories(store)
    elif kind == MEMORY_SEARCH:
        matches = store.retrieve(intent.payload, limit=8)
        if not matches:
            print("（未检索到相关记忆）")
            return
        for m, _ in matches:
            print(f"[{m.id}] {m.content}")


def _show_memories(store: MemoryStore) -> None:
    memories = store.list_memories()
    if not memories:
        print("（暂无记忆）")
        return
    for m in memories:
        print(f"[{m.id}] {m.content}")


def _show_permissions(permissions: PermissionEngine) -> None:
    for cap in KNOWN_CAPABILITIES:
        status = "GRANTED" if permissions.has_permission(cap) else "DENIED"
        print(f"{cap:<20} {status}")


def _show_safety_status(kernel: SafetyKernel) -> None:
    s = kernel.status()
    print(f"Safety Kernel: {s['safety_kernel']}")
    print(f"Owner: {s['owner']}")
    print(f"Audit: {s['audit']}")
    print(f"Constitution: {s['constitution']}")


def _show_audit(audit: AuditStore, limit: int = 10) -> None:
    events = audit.list_recent(limit)
    if not events:
        print("（暂无审计记录）")
        return
    for e in events:
        risk = e.risk_level or "-"
        decision = e.decision or "-"
        print(f"[{e.id}] {e.timestamp} {e.event_type} actor={e.actor} risk={risk} decision={decision} reason={e.reason}")


def _add_goal(entities: EntitiesStore, title: str) -> None:
    if not title:
        print("内容为空，未记录。")
        return
    goal = entities.add_goal(title)
    print("已记录目标。")
    print(f"Goal ID: {goal.id}")


def _show_goals(entities: EntitiesStore) -> None:
    goals = entities.list_goals()
    if not goals:
        print("（暂无目标）")
        return
    for g in goals:
        print(f"[{g.id}] ({g.status}) {g.title}")


def _complete_goal(entities: EntitiesStore, goal_id_str: str) -> None:
    try:
        goal_id = int(goal_id_str)
    except ValueError:
        print("目标 ID 无效。")
        return
    goal = entities.update_goal_status(goal_id, "completed")
    if goal is None:
        print("目标不存在。")
    else:
        print(f"目标 [{goal.id}] 已标记为 completed。")


def _add_task(entities: EntitiesStore, title: str) -> None:
    if not title:
        print("内容为空，未记录。")
        return
    task = entities.add_task(title)
    print("已记录任务。")
    print(f"Task ID: {task.id}")


def _show_tasks(entities: EntitiesStore) -> None:
    tasks = entities.list_tasks()
    if not tasks:
        print("（暂无任务）")
        return
    for t in tasks:
        print(f"[{t.id}] ({t.status}/{t.priority}) {t.title}")


def _complete_task(entities: EntitiesStore, task_id_str: str) -> None:
    try:
        task_id = int(task_id_str)
    except ValueError:
        print("任务 ID 无效。")
        return
    task = entities.update_task_status(task_id, "done")
    if task is None:
        print("任务不存在。")
    else:
        print(f"任务 [{task.id}] 已标记为 done。")


def _add_project(entities: EntitiesStore, name: str) -> None:
    if not name:
        print("内容为空，未记录。")
        return
    project = entities.add_project(name)
    print("已记录项目。")
    print(f"Project ID: {project.id}")


def _show_projects(entities: EntitiesStore) -> None:
    projects = entities.list_projects()
    if not projects:
        print("（暂无项目）")
        return
    for p in projects:
        step = f" | 下一步：{p.next_step}" if p.next_step else ""
        print(f"[{p.id}] ({p.status}) {p.name}{step}")


def _add_decision(entities: EntitiesStore, decision: str) -> None:
    if not decision:
        print("内容为空，未记录。")
        return
    d = entities.add_decision(decision)
    print("已记录决策。")
    print(f"Decision ID: {d.id}")


def _show_decisions(entities: EntitiesStore) -> None:
    decisions = entities.list_decisions()
    if not decisions:
        print("（暂无决策）")
        return
    for d in decisions:
        print(f"[{d.id}] {d.decision}")
        if d.reason:
            print(f"    理由：{d.reason}")


if __name__ == "__main__":
    raise SystemExit(main())
