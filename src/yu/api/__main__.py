"""运行 Yu API 服务器。

    python -m yu.api

默认监听 127.0.0.1:8787；可用环境变量 YU_API_HOST / YU_API_PORT 覆盖。
"""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("YU_API_HOST", "127.0.0.1")
    port = int(os.environ.get("YU_API_PORT", "8787"))
    uvicorn.run("yu.api.app:create_app", factory=True, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
