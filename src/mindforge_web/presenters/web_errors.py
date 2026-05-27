"""Error translation for Web API.

中文学习型说明：浏览器端面向普通个人用户，默认不应该看到 Python traceback。
这里把异常收敛成短错误码、可读 message 和下一步，而 debug traceback 仍留给
CLI / pytest / 开发者工具。
"""

from __future__ import annotations

from fastapi import HTTPException


def user_error(status_code: int, kind: str, message: str, next_action: str | None = None) -> HTTPException:
    detail: dict[str, str] = {"error": kind, "message": message}
    if next_action:
        detail["next_action"] = next_action
    return HTTPException(status_code=status_code, detail=detail)


def http_error(status_code: int, message: str) -> HTTPException:
    """把用户主路径错误保持为前端可读的 `{detail:{message}}`。

    中文学习型说明：Add Source / Process Now 是普通用户第一阶段主链路。
    后端拒绝相对路径、缺模型或其它用户可修复错误时，不能只返回字符串
    detail，否则 Web fetch helper 会退化成浏览器的 `Bad Request` 文案。
    """

    return HTTPException(status_code=status_code, detail={"message": message})
