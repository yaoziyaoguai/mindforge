"""M4 Source Location golden fixtures — SDD §8.1。

为每种 source_type 定义 SourceLocation 的输入参数和期望的 display 输出。
"""

LOCATION_FIXTURES: dict[str, tuple[dict[str, object], str]] = {
    "markdown": (
        {
            "source_type": "plain_markdown",
            "heading_path": ("Architecture", "Authentication"),
            "line_start": 45,
            "line_end": 62,
        },
        "§ Architecture > Authentication, lines 45-62",
    ),
    "txt": (
        {"source_type": "txt", "line_start": 120, "line_end": 145},
        "Lines 120-145",
    ),
    "html": (
        {
            "source_type": "html",
            "heading_path": ("Overview",),
            "css_selector": "h2#overview > p:nth-child(3)",
        },
        "h2#overview > p:nth-child(3)",
    ),
    "pdf": (
        {"source_type": "pdf", "page_number": 12},
        "Page 12",
    ),
    "docx": (
        {"source_type": "docx", "paragraph_start": 8, "paragraph_end": 12},
        "Paragraphs 8-12",
    ),
}
