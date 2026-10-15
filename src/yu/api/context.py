"""Yu API 的进程内应用上下文。

在 API 进程内构建并持有 Yu Core 各子系统实例（Memory / Entities / Daily /
Audit / Owner / Safety Kernel / LLM Provider）。与 CLI 使用完全相同的
配置来源（环境变量 + 默认相对路径），保证 Web 与 CLI 读取同一份真实数据。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..audit.store import AuditStore
from ..actions.service import ActionService, build_action_service
from ..authority.owner import OwnerManager
from ..daily import DailyLogStore
from ..entities.store import EntitiesStore
from ..llm import LLMError, LLMProvider, create_provider
from ..memory.store import MemoryStore
from ..safety.constitution import SafetyConstitution
from ..safety.kernel import SafetyKernel
from ..safety.permissions import PermissionEngine

DEFAULT_DB_PATH = os.environ.get("YU_DB_PATH", "data/yu.db")
DEFAULT_AUDIT_DB = os.environ.get("YU_AUDIT_DB", "data/audit.db")
DEFAULT_CONSTITUTION_PATH = os.environ.get("YU_CONSTITUTION_PATH", "config/safety_constitution.yaml")
DEFAULT_OWNER_PATH = os.environ.get("YU_OWNER_PATH", "config/owner.yaml")
DEFAULT_ACTION_CONFIG_DIR = os.environ.get("YU_ACTION_CONFIG_DIR", "config")


@dataclass
class AppContext:
    """Yu Core 各子系统的单一进程内实例集合（由 API 进程持有）。"""

    memory: MemoryStore
    entities: EntitiesStore
    daily: DailyLogStore
    audit: AuditStore
    owner: OwnerManager
    constitution: SafetyConstitution
    permissions: PermissionEngine
    kernel: SafetyKernel
    action_service: ActionService
    provider: LLMProvider | None
    provider_error: str | None

    def close(self) -> None:
        self.memory.close()
        self.entities.close()
        self.daily.close()
        self.audit.close()


def build_context() -> AppContext:
    """构建 Yu Core 上下文；LLM Provider 缺失时降级为本地只读能力。"""
    memory = MemoryStore(DEFAULT_DB_PATH)
    entities = EntitiesStore(DEFAULT_DB_PATH)
    daily = DailyLogStore(DEFAULT_DB_PATH)
    audit = AuditStore(DEFAULT_AUDIT_DB)
    owner = OwnerManager(DEFAULT_OWNER_PATH)
    constitution = SafetyConstitution(DEFAULT_CONSTITUTION_PATH)
    owner_id = owner.owner.owner_id if owner.owner is not None else "unknown"
    permissions = PermissionEngine(owner_id, audit)
    kernel = SafetyKernel(constitution, permissions, owner, audit)
    action_service = build_action_service(kernel, audit, DEFAULT_ACTION_CONFIG_DIR)

    provider: LLMProvider | None = None
    provider_error: str | None = None
    try:
        provider = create_provider()
    except LLMError as e:
        provider_error = str(e)

    return AppContext(
        memory=memory,
        entities=entities,
        daily=daily,
        audit=audit,
        owner=owner,
        constitution=constitution,
        permissions=permissions,
        kernel=kernel,
        action_service=action_service,
        provider=provider,
        provider_error=provider_error,
    )
