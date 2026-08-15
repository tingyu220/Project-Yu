"""结构化实体数据模型：Goal / Task / Decision / Project。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Goal:
    id: int
    title: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    status: str
    priority: str
    due_date: Optional[str]
    related_goal: Optional[int]
    related_project: Optional[int]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Decision:
    id: int
    decision: str
    reason: Optional[str]
    constraints: Optional[str]
    alternatives: Optional[str]
    created_at: str


@dataclass(frozen=True)
class Project:
    id: int
    name: str
    status: str
    current_goal: Optional[str]
    next_step: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str
