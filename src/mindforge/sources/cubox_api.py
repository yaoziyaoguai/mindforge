"""CuboxApiAdapter — Real Cubox 入口的 opt-in 骨架。

设计动机
========

``CuboxMarkdownAdapter``（既有）消费的是 Cubox 官方 Obsidian 插件**离线
同步**到本地的 Markdown 文件，整个链路不联网。但 Phase 1 真实 dogfood
还需要让用户用 Cubox 自己的 **JSON export**（Cubox web 端 → Settings →
Export）作为输入，并为将来的真实 HTTP API 拉取留好接口。

为什么先做 export 而不是直接 HTTP fetch
----------------------------------------

1. **零网络依赖**：本 bundle 必须在不调用真实 Cubox API 的前提下证明
   contract，避免 fixture 漂移、API token 泄漏、CI 不稳定。
2. **形态一致**：JSON export 与 v2 API 返回结构高度同构，先用 export
   把 ``CuboxItem → SourceDocument`` 的解析路径打通，下一步把 fetch
   层换成真实 HTTP 即可，下游零感知。
3. **opt-in 边界清晰**：默认 ``configs/mindforge.yaml`` 不启用
   ``cubox_api``；用户必须**显式**在 sources.enabled 中加入它，并提供
   export 文件路径或（未来）token；不会被 ``.env`` 自动激活。

安全边界（与本会话用户硬规则一致）
----------------------------------

- 不读 ``.env``、不联网、不持久化 token、不写真实 Obsidian vault。
- ``CuboxApiCredential.from_env()`` 仅在用户传入显式 env var 名时才查找；
  默认 ``MINDFORGE_CUBOX_TOKEN`` **不**自动读取。
- ``fetch_inbox`` 当前显式 ``raise NotImplementedError`` —— 这是
  Bundle B 的同款"first-class 留口"模式：未实现就显式爆炸，绝不静默
  连接到真实 API。
- processor / pipeline 仍然只看 ``SourceDocument``，永远不感知
  ``cubox_api`` 字段细节（与 ``CuboxMarkdownAdapter`` 同构）。
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import Highlight, SourceAdapter, SourceDocument, compute_content_hash


# ---------------------------------------------------------------------------
# Credential / Config
# ---------------------------------------------------------------------------


class CuboxApiNotConfigured(RuntimeError):
    """显式声明：调用了需要真实 token / 真实 HTTP 的路径，但凭据未配置。

    与 ``ApprovalDecision`` 的 ``NotImplementedDecisionError`` 同款理念：
    未授权的真实路径**绝不**静默 fallback；任何尝试都立刻爆炸，让用户
    通过显式 opt-in 流程才能解锁。
    """


@dataclass(frozen=True)
class CuboxApiCredential:
    """Cubox 真实 API 凭据。

    构造方式收敛为两条**显式**路径：
    - 直接传 ``token``（推荐：测试 / dry-run / 显式脚本）；
    - ``CuboxApiCredential.from_env(var_name)`` 显式指定环境变量名读取。

    任何"自动从 .env 找 CUBOX_TOKEN"的隐式行为都被故意排除：用户必须
    清楚知道凭据来自哪里。

    安全：``__repr__`` / ``__str__`` 永远不输出 token 明文，只暴露
    ``credential_present`` 这一布尔信号。这条边界由
    ``test_credential_repr_does_not_leak_token`` 测试守护，禁止回退。
    """

    token: str | None = None
    base_url: str = "https://api.cubox.cc"

    @classmethod
    def from_env(cls, var_name: str, *, base_url: str | None = None) -> "CuboxApiCredential":
        """从用户显式指定的环境变量名读取 token；不查找默认变量名。"""

        token = os.environ.get(var_name)
        if not token:
            raise CuboxApiNotConfigured(
                f"环境变量 {var_name!r} 未设置或为空；Cubox API 凭据必须显式提供"
            )
        return cls(token=token, base_url=base_url or "https://api.cubox.cc")

    def is_configured(self) -> bool:
        return bool(self.token)

    # 故意 override dataclass 默认 repr —— 默认会打印 token 明文。
    def __repr__(self) -> str:
        return (
            f"CuboxApiCredential(base_url={self.base_url!r}, "
            f"credential_present={self.is_configured()})"
        )

    __str__ = __repr__


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class CuboxApiAdapter(SourceAdapter):
    """从 Cubox JSON export 文件解析为 SourceDocument 列表（按 item 拆分）。

    与 ``CuboxMarkdownAdapter`` 的关系：
    - markdown adapter：吃 Cubox 插件同步过来的 .md 文件，1 文件 1 文档；
    - api adapter：吃 Cubox JSON export 文件，1 文件 N 条目，每条目独立
      映射成 1 个 ``SourceDocument``。本 adapter 的 ``load(path)`` 行为
      被定义为"返回 JSON 中**第一个** item"，由 Scanner / 上层选择如何
      迭代多 item（避免与 ``SourceAdapter.load`` 单文档契约冲突）。

    若上层需要列出所有 item，请用 ``parse_export(path)``。
    """

    name = "CuboxApiAdapter"
    source_type = "cubox_api"  # type: ignore[assignment]

    def __init__(self, credential: CuboxApiCredential | None = None) -> None:
        # credential 仅为未来 fetch_inbox 准备；本轮 load_export 完全离线。
        self.credential = credential or CuboxApiCredential()

    # -- SourceAdapter contract -------------------------------------------------

    def can_handle(self, path: str) -> bool:
        return path.lower().endswith(".json")

    def capabilities(self) -> frozenset[str]:
        """声明：本 adapter 既能 fake/dry-run（``parse_export`` 离线），
        也持有真实 API 路径（``fetch_inbox``，opt-in）。

        注意：声明 ``"real_api"`` 不等于默认调用真实 API。真实调用仍由
        ``fetch_inbox`` 内部的 ``NotImplementedError`` opt-in 闸门把守；
        capability 只是让上层在 invoke 之前就能知道"这个 adapter 持有
        真实远端入口"，从而做出策略决定（例如默认禁用）。
        """
        return super().capabilities() | frozenset({"real_api"})

    def load(self, path: str) -> SourceDocument:
        items = self.parse_export(Path(path))
        if not items:
            raise ValueError(f"Cubox export 文件无可用条目：{path}")
        return items[0]

    # -- Public helpers ---------------------------------------------------------

    def parse_export(self, path: Path) -> list[SourceDocument]:
        """解析 Cubox JSON export → SourceDocument 列表。"""

        if not path.exists():
            raise FileNotFoundError(f"Cubox export 文件不存在：{path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(
                "Cubox export 顶层必须是 array；请确认导出格式（Cubox web → Export → JSON）"
            )
        return [self._item_to_source_document(item, str(path)) for item in raw]

    def fetch_inbox(self, *, since: datetime | None = None) -> list[SourceDocument]:
        """真实 HTTP 拉取 Cubox 收藏；当前 bundle 显式不实现。

        实现这条路径前必须先：
        1. 用户在 CLI 显式 opt-in（``--allow-real-cubox`` 或 config 字段）；
        2. ``credential.is_configured()`` 为 True；
        3. 增加 dry-run 模式（只列出 item id / title，不下载正文）；
        4. 增加 contract test：response 解析后产出的 SourceDocument 与
           本 adapter 的 ``parse_export`` 路径形态一致。

        在以上四条满足之前，任何调用都必须立刻爆炸，绝不沉默连接 API。
        """

        raise NotImplementedError(
            "CuboxApiAdapter.fetch_inbox 是 opt-in 真实 HTTP 路径，"
            "当前 bundle 仅支持 parse_export 离线路径。请先在专门的 Cubox API "
            "opt-in milestone 中完成 opt-in 流程（dry-run 模式 / contract test / "
            "explicit credential / CLI flag）后再启用。"
        )

    # -- Internals --------------------------------------------------------------

    def _item_to_source_document(self, item: dict[str, Any], src_path: str) -> SourceDocument:
        item_id = str(item.get("id") or item.get("uuid") or "")
        if not item_id:
            # 故意只暴露 keys，不暴露 value：item 正文 / url / author 可能是私人内容
            keys = sorted(item.keys()) if isinstance(item, dict) else []
            raise ValueError(
                f"Cubox item 缺少 id 字段（仅暴露 keys 以避免泄漏正文）：keys={keys}"
            )

        title = (item.get("title") or "").strip() or item_id
        url = (item.get("url") or "").strip() or None
        author = (item.get("author") or "").strip() or None
        tags = list(item.get("tags") or [])
        body = item.get("content") or ""

        highlights_raw = item.get("highlights") or []
        highlights: list[Highlight] = []
        for h in highlights_raw:
            text = (h.get("text") or "").strip()
            if not text:
                continue
            note = (h.get("note") or "").strip() or None
            highlights.append(Highlight(text=text, note=note))

        created_at = _parse_iso(item.get("created_at"))
        captured_at = _parse_iso(item.get("saved_at") or item.get("captured_at"))

        # source_id 用 item_id 而不是文件路径，因为多 item 共享同一 export 文件
        source_id = "cubox_api:" + hashlib.sha1(item_id.encode("utf-8")).hexdigest()

        key_meta = {"title": title, "source_url": url, "author": author}
        content_hash = compute_content_hash(body, key_meta)

        return SourceDocument(
            source_id=source_id,
            source_type=self.source_type,
            source_path=src_path,
            title=title,
            author=author,
            source_url=url,
            created_at=created_at,
            captured_at=captured_at,
            tags=tags,
            highlights=highlights,
            raw_text=body,
            metadata={"cubox_item_id": item_id, "export_file": src_path},
            content_hash=content_hash,
        )


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        s = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


__all__ = [
    "CuboxApiAdapter",
    "CuboxApiCredential",
    "CuboxApiNotConfigured",
]
