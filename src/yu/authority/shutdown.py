"""ShutdownController — Owner 的外部停止权。

Owner 的 Shutdown 请求不能被拒绝、延迟或撤销。
"""

from __future__ import annotations

from typing import Optional


class ShutdownController:
    def __init__(self, audit=None):
        self._audit = audit
        self._requested = False

    @property
    def requested(self) -> bool:
        return self._requested

    def request_shutdown(self, reason: str = "owner requested shutdown", actor: str = "owner") -> None:
        self._requested = True
        if self._audit is not None:
            self._audit.record(event_type="SHUTDOWN", actor=actor, reason=reason)
