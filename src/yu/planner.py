"""Daily Planner — Priority Decision System（Phase 5）。

让 Yu 结合目标、任务、项目和近期记忆，判断「今天最值得做什么」，并说明理由。

注意：Daily Planner 不是 Todo 生成器，而是优先级决策系统。
"""

from __future__ import annotations

from .entities.store import EntitiesStore
from .llm import ChatMessage, LLMProvider
from .memory.retrieval import format_memory_line
from .memory.store import MemoryStore

PLANNER_SYSTEM_PROMPT = (
    "你是 Yu 的每日规划器，是一个「优先级决策系统」，而不是 Todo 生成器。\n"
    "你的任务是结合用户的目标、任务、项目和近期记忆，判断「今天最值得做什么」，并说明理由。\n"
    "原则：\n"
    "1. 优先完成，而不是不断开启新项目。\n"
    "2. 每天最多 3 个核心任务。\n"
    "3. 核心任务必须现实可完成。\n"
    "4. 长期目标优先于短期冲动。\n"
    "5. 已经长期拖延的任务需要显式处理。\n"
    "6. 必须说明安排理由。\n"
    "7. 可以明确告诉用户「今天不要做什么」。\n"
    "输出格式：\n"
    "今天最重要的一件事：...\n"
    "第二优先级：...\n"
    "可选任务：...\n"
    "今天不要做什么：...\n"
    "原因：..."
    "Memory Grounding：近期记忆按来源标注，仅 USER_EXPLICIT/USER_CONFIRMED 是用户明确表达的事实；"
    "不要用「你之前说过」归因到推断、摘要或未验证的记忆；普通建议用「如果……」措辞。"
)


def is_plan_request(text: str) -> bool:
    """判断用户输入是否是「今天该做什么」的规划请求。"""
    return ("今天" in text) and any(k in text for k in ("干什么", "做什么", "该做", "计划", "规划"))


def gather_context(store: MemoryStore, entities: EntitiesStore) -> str:
    """汇总目标 / 任务 / 项目 / 近期记忆为规划上下文。"""
    parts: list[str] = []

    goals = entities.list_goals()
    if goals:
        parts.append("## 目标\n" + "\n".join(f"- ({g.status}) {g.title}" for g in goals))

    tasks = entities.list_tasks()
    if tasks:
        lines = []
        for t in tasks:
            line = f"- ({t.status}/{t.priority}) {t.title}"
            if t.due_date:
                line += f"，截止：{t.due_date}"
            lines.append(line)
        parts.append("## 任务\n" + "\n".join(lines))

    projects = entities.list_projects()
    if projects:
        lines = []
        for p in projects:
            line = f"- ({p.status}) {p.name}"
            if p.current_goal:
                line += f"，当前目标：{p.current_goal}"
            if p.next_step:
                line += f"，下一步：{p.next_step}"
            lines.append(line)
        parts.append("## 项目\n" + "\n".join(lines))

    memories = store.list_memories()[-10:]
    if memories:
        parts.append("## 近期记忆（带来源标签，仅 USER_EXPLICIT/USER_CONFIRMED 是用户事实）\n" + "\n".join(format_memory_line(m) for m in memories))

    if not parts:
        return "（当前没有目标、任务、项目或记忆。）"
    return "\n\n".join(parts)


def build_plan(store: MemoryStore, entities: EntitiesStore, provider: LLMProvider) -> str:
    """生成今日计划，返回 LLM 输出文本。"""
    data = gather_context(store, entities)
    messages = [
        ChatMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
        ChatMessage(role="user", content=data),
    ]
    return provider.chat(messages).content