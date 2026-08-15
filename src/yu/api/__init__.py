"""Yu API — 最薄的 Interface Layer。

将 Yu Core 的能力以 HTTP API 暴露给 apps/web（Yu Web）。
这是 Yu 的「身体」与交互入口，不是另一个 Yu。

原则：
- apps/web 只能通过本 API 使用 Yu 能力，不能直接读 SQLite / 内部 Python 文件。
- API 不绕过 Safety Kernel / Permission Engine。
- Frontend 不直接调用 DeepSeek；Chat 经由 Yu Core -> LLM Provider -> DeepSeek。
- Yu Core 不依赖 Web 才能运行（本包只是可选入口）。
"""

from .app import create_app

__all__ = ["create_app"]
