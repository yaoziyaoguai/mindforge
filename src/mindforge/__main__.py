"""`python -m mindforge` entrypoint.

保持与 console script ``mindforge = mindforge.cli:main`` 同一入口，避免
测试和用户在无安装脚本时无法运行包模块。
"""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":  # pragma: no cover
    main()
