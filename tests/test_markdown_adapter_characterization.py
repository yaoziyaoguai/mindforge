"""M1 Phase P1 — PlainMarkdownAdapter 表征测试（characterization tests）。

中文学习型说明
================

为什么在 M1 Phase P1 先写 characterization tests 而不是直接改 production code？
------------------------------------------------------------------------

v0.2 要对 SourceAdapter 体系做 contract 升级（引入 AdapterResult、扩展
SourceDocument 字段），但 **PlainMarkdownAdapter 是 v0.1 的稳定实现**。
在动 production code 之前，必须先用测试把它的**所有现有行为**钉死：

1. **回归安全网**：后续换 AdapterResult 时，这些测试会告诉我们有没有不慎改坏
   PlainMarkdownAdapter 的已有行为。
2. **行为基线**：表征测试不评判"行为好不好"——只记录"当前实际行为"。即使
   当前行为不理想（例如跳过 unknown card_id 而非报错），也如实固定。
3. **契约可见化**：把散落在代码中的隐式契约（source_path 保持原样、hash 用
   sha256 前缀、frontmatter → title 映射规则）变成显式测试断言。

表征测试 vs 契约测试 vs TDD 单元测试
------------------------------------

- **表征测试（本文件）**：记录当前实际行为，不改任何 src。允许测试"不理想的
  当前行为"。
- **契约测试（后续 P2）**：定义 v0.2 期望行为。可能部分与当前行为一致（Green），
  部分为未来行为（Red）。
- **TDD 单元测试（后续 M2-M4）**：先写测试 → 再写实现。用于新 adapter。

本文件范围
----------

- **只测 PlainMarkdownAdapter** 的 can_handle / load 路径。
- **不测** CommonDocumentAdapter（它不在 M1 scope，虽也算 .md path）。
- **不测** scanner / processor / approval / wiki 链路。
- **不改** src/。
- **不读** .env、真实 vault、真实私人资料。
- **所有 fixture 均为 synthetic**：通过 tmp_path 在测试中动态生成。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from mindforge.sources.plain_markdown import PlainMarkdownAdapter


# =============================================================================
# 1. can_handle — 后缀识别
# =============================================================================


def test_can_handle_recognizes_md_suffix() -> None:
    """PlainMarkdownAdapter 应通过 .md 后缀识别文件。

    当前行为（v0.1）：can_handle 只看后缀是不是 .md，大小写不敏感。
    不检查文件是否存在、不读文件头、不验证内容。
    """
    adapter = PlainMarkdownAdapter()
    assert adapter.can_handle("note.md") is True
    assert adapter.can_handle("NOTE.MD") is True
    assert adapter.can_handle("path/to/note.Md") is True


def test_can_handle_rejects_non_md_suffix() -> None:
    """非 .md 后缀应返回 False。

    当前行为（v0.1）：can_handle 对所有非 .md 后缀返回 False，
    不做内容探测。即使文件内容是合法 Markdown，只要后缀不是 .md 就不认。
    """
    adapter = PlainMarkdownAdapter()
    assert adapter.can_handle("note.txt") is False
    assert adapter.can_handle("note.html") is False
    assert adapter.can_handle("note.pdf") is False
    assert adapter.can_handle("note.docx") is False
    assert adapter.can_handle("note.markdown") is False  # 非 .md
    assert adapter.can_handle("note.json") is False
    assert adapter.can_handle("note") is False  # 无后缀
    assert adapter.can_handle("") is False


# =============================================================================
# 2. load — 正常 Markdown 内容保留
# =============================================================================


def test_load_preserves_markdown_body(tmp_path: Path) -> None:
    """raw_text 应保留 Markdown 正文（去除 frontmatter 后）。

    当前行为（v0.1）：frontmatter 被 frontmatter 库剥离，剩余正文作为
    raw_text 原样保留——不做格式转换、不做 HTML 渲染。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text(
        "---\n"
        "title: Test Note\n"
        "---\n"
        "\n"
        "# Hello World\n"
        "\n"
        "This is a **bold** paragraph.\n"
        "\n"
        "- item 1\n"
        "- item 2\n"
        "\n"
        "```python\n"
        "print('hello')\n"
        "```\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.raw_text.startswith("# Hello World")
    assert "**bold**" in doc.raw_text
    assert "- item 1" in doc.raw_text
    assert "```python" in doc.raw_text
    # frontmatter 不应出现在 raw_text 中
    assert "---" not in doc.raw_text
    assert "title: Test Note" not in doc.raw_text


def test_load_extracts_frontmatter_fields(tmp_path: Path) -> None:
    """frontmatter 中的标准字段应映射到 SourceDocument 对应属性。

    当前行为（v0.1）：
    - title → doc.title（缺省时 fallback 到 stem）
    - author → doc.author
    - source_url / url → doc.source_url
    - tags → doc.tags（支持 list 或逗号分隔 string）
    - created_at / created → doc.created_at
    - captured_at → doc.captured_at
    """
    md_file = tmp_path / "note.md"
    md_file.write_text(
        "---\n"
        "title: My Note\n"
        "author: Alice\n"
        "source_url: https://example.com/post\n"
        "tags:\n"
        "  - python\n"
        "  - testing\n"
        "created_at: '2026-01-15T10:30:00'\n"
        "captured_at: '2026-05-01T08:00:00'\n"
        "---\n"
        "\n"
        "# My Note\n"
        "\n"
        "Body text.\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.title == "My Note"
    assert doc.author == "Alice"
    assert doc.source_url == "https://example.com/post"
    assert doc.tags == ["python", "testing"]
    assert doc.created_at is not None
    assert doc.created_at.isoformat() == "2026-01-15T10:30:00"
    assert doc.captured_at is not None
    assert doc.captured_at.isoformat() == "2026-05-01T08:00:00"


def test_load_uses_stem_as_title_when_no_frontmatter_title(tmp_path: Path) -> None:
    """frontmatter 无 title 时，title fallback 到文件 stem。

    当前行为（v0.1）：title 取 frontmatter.title；若无，取 p.stem。
    """
    md_file = tmp_path / "my-untitled-note.md"
    md_file.write_text(
        "# Some Heading\n\nBody here.\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.title == "my-untitled-note"


def test_load_handles_tags_as_comma_string(tmp_path: Path) -> None:
    """tags 为逗号分隔字符串时应拆分为 list。

    当前行为（v0.1）：_coerce_tags 支持 "a, b, c" 字符串形式。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text(
        "---\n"
        "tags: python, testing, v0.2\n"
        "---\n"
        "\n"
        "Body.\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.tags == ["python", "testing", "v0.2"]


def test_load_highlights_always_empty(tmp_path: Path) -> None:
    """PlainMarkdownAdapter 不解析 ==高亮== 语法，highlights 恒为 []。

    当前行为（v0.1）：PlainMarkdown 没有 highlights 概念。文件中即使
    有 ==高亮== 标记也不解析（与 CuboxMarkdownAdapter 不同）。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text(
        "# Note\n\n==highlighted text==\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.highlights == []


def test_load_metadata_contains_frontmatter_raw(tmp_path: Path) -> None:
    """metadata["frontmatter"] 应包含完整 frontmatter 原始字典。

    当前行为（v0.1）：metadata 是一个 dict，其中 "frontmatter" 键存放
    frontmatter 解析后的原始 dict。下游如需访问非标准 frontmatter 字段，
    从这里取。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text(
        "---\n"
        "title: Note\n"
        "custom_field: some-value\n"
        "---\n"
        "\n"
        "Body.\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert "frontmatter" in doc.metadata
    assert doc.metadata["frontmatter"]["title"] == "Note"
    assert doc.metadata["frontmatter"]["custom_field"] == "some-value"


# =============================================================================
# 3. source_path 行为
# =============================================================================


def test_source_path_preserved_as_passed(tmp_path: Path) -> None:
    """source_path 应保持传入时的路径形式。

    当前行为（v0.1）：adapter.load(path) 不改写路径，不做相对化 /
    绝对化转换。传入什么就存什么。这对于保持 scanner 调用的一致性很重要。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text("# Note\n\nBody.\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()

    # 传入绝对路径
    doc_abs = adapter.load(str(md_file.resolve()))
    assert doc_abs.source_path == str(md_file.resolve())

    # 传入相对路径
    doc_rel = adapter.load(str(md_file))
    assert doc_rel.source_path == str(md_file)


def test_source_path_with_unicode_and_spaces(tmp_path: Path) -> None:
    """中文文件名或含空格的路径不应导致崩溃。

    当前行为（v0.1）：路径中的 unicode 和空格属于文件系统合法字符，
    adapter 不应因此抛异常。source_path 原样保留。
    """
    # 中文文件名
    cn_file = tmp_path / "笔记-学习心得.md"
    cn_file.write_text("# 学习心得\n\n内容。\n", encoding="utf-8")

    # 空格文件名
    space_file = tmp_path / "my notes draft.md"
    space_file.write_text("# Draft\n\nContent.\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()

    doc_cn = adapter.load(str(cn_file))
    assert doc_cn.source_path == str(cn_file)
    assert "笔记" in doc_cn.source_path

    doc_space = adapter.load(str(space_file))
    assert doc_space.source_path == str(space_file)
    assert " " in doc_space.source_path


# =============================================================================
# 4. content_hash 行为
# =============================================================================


def test_content_hash_stable_for_same_content_and_same_stem(tmp_path: Path) -> None:
    """相同内容且相同 stem 时 content_hash 应一致。

    当前行为（v0.1）：content_hash = sha256(raw_text || \x00 || sorted_json(key_meta))。
    key_meta 包含 title（无 frontmatter title 时 fallback 到 p.stem）。
    因此**同一文件名不同目录**同内容 → 同 hash；
    **不同文件名**即使同内容也可能不同 hash（因为 stem/title 不同）。
    这是当前实际行为，表征测试如实记录。
    """
    content = "# Hello\n\nWorld.\n"
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "a.md"  # 同 stem
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    d1 = adapter.load(str(f1))
    d2 = adapter.load(str(f2))

    assert d1.content_hash == d2.content_hash
    assert d1.content_hash.startswith("sha256:")


def test_content_hash_differs_when_stems_differ_even_with_same_body(tmp_path: Path) -> None:
    """同正文但不同 stem 时 content_hash 可能不同（当前行为如实记录）。

    原因：无 frontmatter title 时 title = p.stem，而 key_meta 包含 title。
    stem 不同 → title 不同 → key_meta 不同 → hash 不同。
    这是当前实际行为——表征测试只记录，不评判好坏。
    """
    content = "# Hello\n\nWorld.\n"
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_text(content, encoding="utf-8")
    f2.write_text(content, encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    d1 = adapter.load(str(f1))
    d2 = adapter.load(str(f2))

    assert d1.content_hash != d2.content_hash


def test_content_hash_changes_when_body_changes(tmp_path: Path) -> None:
    """正文变化时 content_hash 应不同。

    当前行为（v0.1）：raw_text 是 hash 的主要输入，body 变 → hash 变。
    """
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_text("# Same\n", encoding="utf-8")
    f2.write_text("# Different\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    d1 = adapter.load(str(f1))
    d2 = adapter.load(str(f2))

    assert d1.content_hash != d2.content_hash


def test_content_hash_changes_when_key_meta_changes(tmp_path: Path) -> None:
    """关键 metadata（title / source_url / author）变化时 hash 应不同。

    当前行为（v0.1）：key_meta = {title, source_url, author}。这些字段
    变动应该触发 hash 变化（即使 raw_text 相同），因为 LLM 加工结果可能不同。
    """
    body = "# Note\n\nSame body.\n"

    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_text(
        "---\ntitle: Note A\nauthor: Alice\n---\n\n" + body,
        encoding="utf-8",
    )
    f2.write_text(
        "---\ntitle: Note B\nauthor: Bob\n---\n\n" + body,
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    d1 = adapter.load(str(f1))
    d2 = adapter.load(str(f2))

    assert d1.content_hash != d2.content_hash


def test_content_hash_has_sha256_prefix(tmp_path: Path) -> None:
    """content_hash 必须带 "sha256:" 前缀。

    当前行为（v0.1）：compute_content_hash 固定用 sha256 算法并加前缀。
    前缀的存在让未来迁移算法时不会出现歧义。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text("# Note\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.content_hash.startswith("sha256:")
    # 去掉前缀后应是 64 字符的 hex digest
    hex_part = doc.content_hash[len("sha256:"):]
    assert len(hex_part) == 64
    int(hex_part, 16)  # 不抛异常 = 合法 hex


# =============================================================================
# 5. source_id 行为
# =============================================================================


def test_source_id_is_sha1_of_path(tmp_path: Path) -> None:
    """source_id 格式为 "sha1:<hex>"。

    当前行为（v0.1）：source_id = "sha1:" + sha1(source_path.encode("utf-8")).hexdigest()
    这是稳定主键，与文件内容无关——同一个路径总是同一个 source_id。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text("# Content\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    expected = "sha1:" + hashlib.sha1(str(md_file).encode("utf-8")).hexdigest()
    assert doc.source_id == expected


def test_source_id_is_stable_for_same_path(tmp_path: Path) -> None:
    """同一路径多次 load，source_id 应一致。

    当前行为（v0.1）：source_id 只依赖 source_path，与文件内容无关。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text("# Content v1\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    id1 = adapter.load(str(md_file)).source_id

    # 修改内容，但路径不变
    md_file.write_text("# Content v2\n", encoding="utf-8")
    id2 = adapter.load(str(md_file)).source_id

    assert id1 == id2


# =============================================================================
# 6. 空 Markdown 行为
# =============================================================================


def test_load_empty_markdown_file(tmp_path: Path) -> None:
    """空 .md 文件的处理。

    当前行为（v0.1）：空文件 body 为空字符串，raw_text = ""，不抛异常。
    title fallback 到 stem。content_hash 也非空（因为 key_meta 有 stem）。
    """
    md_file = tmp_path / "empty.md"
    md_file.write_text("", encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.raw_text == ""
    assert doc.title == "empty"  # fallback to stem
    assert doc.content_hash.startswith("sha256:")


def test_load_markdown_with_only_frontmatter(tmp_path: Path) -> None:
    """只有 frontmatter 无正文的 .md 文件。

    当前行为（v0.1）：frontmatter 被剥离，body 为空字符串。raw_text = ""。
    不抛异常。
    """
    md_file = tmp_path / "meta-only.md"
    md_file.write_text(
        "---\ntitle: Meta Note\ntags: [meta]\n---\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.raw_text == ""
    assert doc.title == "Meta Note"
    assert doc.tags == ["meta"]


def test_load_markdown_with_only_body_no_frontmatter(tmp_path: Path) -> None:
    """无 frontmatter 的纯正文 .md 文件。

    当前行为（v0.1）：无 frontmatter 时 meta = {}，整文件内容作为 raw_text。
    frontmatter 库的 ``post.content`` 可能会去除末尾空白/换行——这是库的行为，
    表征测试如实记录。title fallback 到 stem。
    """
    md_file = tmp_path / "no-meta.md"
    md_file.write_text(
        "# Pure Content\n\nJust a paragraph.\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    # frontmatter 库的 post.content 可能会 trim 末尾换行
    assert "# Pure Content" in doc.raw_text
    assert "Just a paragraph" in doc.raw_text
    # 确认不包含 frontmatter 分隔符
    assert "---" not in doc.raw_text
    assert doc.title == "no-meta"
    assert doc.author is None
    assert doc.tags == []


# =============================================================================
# 7. 文件不存在行为
# =============================================================================


def test_load_missing_file_raises_filenotfound(tmp_path: Path) -> None:
    """文件不存在时抛 FileNotFoundError。

    当前行为（v0.1）：文件不存在是 hard error，不返回空 document，
    不用 skip/success 枚举包装。这与 v0.2 的 AdapterResult(status="skipped", ...)
    语义有本质区别——表征测试记录的就是这个"抛异常"的当前行为。
    """
    adapter = PlainMarkdownAdapter()
    nonexistent = str(tmp_path / "does-not-exist.md")

    with pytest.raises(FileNotFoundError, match="Markdown 文件不存在"):
        adapter.load(nonexistent)


# =============================================================================
# 8. source_type 行为
# =============================================================================


def test_source_type_is_plain_markdown(tmp_path: Path) -> None:
    """load 出的 SourceDocument.source_type 必须为 "plain_markdown"。

    当前行为（v0.1）：PlainMarkdownAdapter.source_type = "plain_markdown"。
    这是 registry 派发的关键字段——scanner 用它做 source_type 一致性校验。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text("# Note\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.source_type == "plain_markdown"
    assert adapter.source_type == "plain_markdown"


# =============================================================================
# 9. frontmatter 字段容错
# =============================================================================


def test_load_invalid_date_graceful(tmp_path: Path) -> None:
    """无法解析的日期字段应返回 None 而非抛异常。

    当前行为（v0.1）：_coerce_dt 对非法日期字符串返回 None。
    adapter 不因为元信息格式错误而拒绝整个文件。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text(
        "---\n"
        "created_at: not-a-valid-date\n"
        "---\n"
        "\n"
        "Body.\n",
        encoding="utf-8",
    )

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.created_at is None


def test_load_none_tags_becomes_empty_list(tmp_path: Path) -> None:
    """tags 缺失时返回 [] 而非 None。

    当前行为（v0.1）：_coerce_tags(None) → []。
    """
    md_file = tmp_path / "note.md"
    md_file.write_text("# Note\nNo frontmatter.\n", encoding="utf-8")

    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(md_file))

    assert doc.tags == []


# =============================================================================
# 10. 不读 secrets / 不做网络调用
# =============================================================================


def test_plain_markdown_adapter_has_no_api_capability() -> None:
    """PlainMarkdownAdapter 的 capabilities 不应包含 "real_api"。

    当前行为（v0.1 / v0.9 Slice 2）：基类 SourceAdapter.capabilities()
    默认返回 frozenset({"local_file", "fake_safe", "dry_run"})。
    PlainMarkdownAdapter 不 override——它是本地文件 adapter，不触网。
    """
    adapter = PlainMarkdownAdapter()
    caps = adapter.capabilities()

    assert "local_file" in caps
    assert "fake_safe" in caps
    assert "dry_run" in caps
    assert "real_api" not in caps


def test_adapter_instantiation_does_not_read_env(monkeypatch) -> None:
    """示例化 PlainMarkdownAdapter 不应读环境变量或文件。

    当前行为（v0.1）：__init__ 是默认的无参构造器，无副作用。
    设置 monkeypatch 确保即使有人尝试也不会成功。
    """
    import builtins

    original_open = builtins.open

    def _guard(*args, **kwargs):
        # 允许 pytest/tmp_path 的文件操作，拒绝其他 open
        raise AssertionError("PlainMarkdownAdapter 实例化不应读文件")

    monkeypatch.setattr(builtins, "open", _guard)
    # 构造器不读文件，guard 不会触发
    try:
        adapter = PlainMarkdownAdapter()
        assert adapter.name == "PlainMarkdownAdapter"
    finally:
        monkeypatch.setattr(builtins, "open", original_open)
