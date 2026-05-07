"""Repo-wide architecture audit script.

为什么要有这个脚本：
- MindForge 之前每次 decomposition pack 都临时人工 grep / ad-hoc python，
  没有可重复的衡量标准；treatment 容易反弹。
- 这个脚本是巨石化治理的“度量尺”：production / tests / functions 三个维度
  + 阈值分桶。
- 输出稳定可比较；既能跑在命令行,也是 milestone evidence packet 的一部分。

边界 / 不做：
- 不替代 ruff / pytest;只做 size & import 边界审计。
- 不做语义分析;只做 AST + line counting。
- 不引入新依赖。
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "mindforge"
TESTS = REPO / "tests"

FILE_BUCKETS = (500, 800, 1200, 2000, 3000)
FUNC_BUCKETS = (80, 120, 200)

PRODUCTION_TOP_N = 50
TEST_TOP_N = 50
FUNCTION_TOP_N = 100

ALLOWLIST: dict[str, str] = {}

CATEGORY_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("adapter", ("_cli.py", "/cli.py", "/__main__.py", "/provider_cli.py", "/cubox_cli.py")),
    ("service", ("/services/", "_service.py")),
    ("presenter", ("_presenter.py", "/presenters/")),
    ("policy", ("_policy.py", "/safety_policy.py")),
    ("workspace", ("/vault.py", "/obsidian.py", "_workflow.py", "_stage.py", "_manifest_policy.py")),
    ("approval", ("/approver.py", "approval", "approve")),
    ("source", ("/sources/", "/source_mux.py")),
    ("strategy", ("/strategies/",)),
)

FORBIDDEN_IMPORT_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "service must not import CLI/Typer/Rich/Console",
        ("/services/", "_service.py"),
        ("typer", "rich", "mindforge.cli", ".cli", "Console"),
    ),
    (
        "presenter must not import CLI/Typer",
        ("_presenter.py", "/presenters/"),
        ("typer", "mindforge.cli", ".cli"),
    ),
    (
        "policy/guard/workspace must not import CLI/Typer",
        ("_policy.py", "/safety_policy.py", "/vault.py", "_workflow.py", "_manifest_policy.py"),
        ("typer", "mindforge.cli", ".cli"),
    ),
    (
        "processor/strategy must not import CuboxAdapter",
        ("/processors/", "/strategies/"),
        ("cubox_cli", "cubox_api", "cubox_markdown", "Cubox"),
    ),
)

RUNTIME_POLLUTION_TERMS = (
    "runs",
    "state",
    "cache",
    "index",
    "logs",
    "vector",
    "graph",
)


@dataclass
class FuncInfo:
    file: str
    name: str
    lineno: int
    loc: int


@dataclass
class FileInfo:
    path: str
    loc: int
    funcs: list[FuncInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    top_level_symbols: list[str] = field(default_factory=list)
    category: str = "other"


@dataclass(frozen=True)
class BoundaryIssue:
    rule: str
    file: str
    detail: str


@dataclass(frozen=True)
class AuditReport:
    production: list[FileInfo]
    tests: list[FileInfo]
    boundary_issues: list[BoundaryIssue]
    allowlist: dict[str, str]


def _iter_py(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def _file_info(path: Path) -> FileInfo:
    src = path.read_text(encoding="utf-8")
    loc = src.count("\n") + 1
    rel = str(path.relative_to(REPO))
    info = FileInfo(path=rel, loc=loc, category=_category_for(rel))
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return info
    info.imports.extend(_imports(tree))
    info.top_level_symbols.extend(_top_level_symbols(tree))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None)
            if end is None:
                continue
            info.funcs.append(
                FuncInfo(file=info.path, name=node.name, lineno=node.lineno, loc=end - node.lineno + 1)
            )
    return info


def _category_for(rel_path: str) -> str:
    normalized = "/" + rel_path.replace("\\", "/")
    for category, markers in CATEGORY_MARKERS:
        if any(marker in normalized for marker in markers):
            return category
    return "other"


def _imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = ("." * node.level) + (node.module or "")
            imports.append(module)
    return sorted(set(imports))


def _top_level_symbols(tree: ast.Module) -> list[str]:
    symbols: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
    return symbols


def collect(root: Path) -> list[FileInfo]:
    return sorted((_file_info(p) for p in _iter_py(root)), key=lambda f: -f.loc)


def bucket_files(files: list[FileInfo]) -> dict[int, list[FileInfo]]:
    return {b: [f for f in files if f.loc > b] for b in FILE_BUCKETS}


def bucket_funcs(files: list[FileInfo]) -> dict[int, list[FuncInfo]]:
    funcs = [fn for f in files for fn in f.funcs]
    return {b: sorted([fn for fn in funcs if fn.loc > b], key=lambda x: -x.loc) for b in FUNC_BUCKETS}


def _matches(path: str, markers: tuple[str, ...]) -> bool:
    normalized = "/" + path.replace("\\", "/")
    return any(marker in normalized for marker in markers)


def boundary_issues(prod: list[FileInfo]) -> list[BoundaryIssue]:
    issues: list[BoundaryIssue] = []
    for file_info in prod:
        imports_text = "\n".join(file_info.imports)
        for rule, path_markers, forbidden in FORBIDDEN_IMPORT_RULES:
            if not _matches(file_info.path, path_markers):
                continue
            hits = sorted({term for term in forbidden if term in imports_text})
            if hits:
                issues.append(
                    BoundaryIssue(
                        rule=rule,
                        file=file_info.path,
                        detail=", ".join(hits),
                    )
                )
        if file_info.category == "workspace":
            pollution_hits = sorted(
                term for term in RUNTIME_POLLUTION_TERMS if term in imports_text
            )
            if pollution_hits:
                issues.append(
                    BoundaryIssue(
                        rule="workspace module imports possible machine-runtime layer",
                        file=file_info.path,
                        detail=", ".join(pollution_hits),
                    )
                )
    return issues


def collect_report() -> AuditReport:
    prod = collect(SRC)
    tests = collect(TESTS)
    return AuditReport(
        production=prod,
        tests=tests,
        boundary_issues=boundary_issues(prod),
        allowlist=ALLOWLIST,
    )


def render_text(report: AuditReport) -> str:
    prod = report.production
    tests = report.tests
    lines: list[str] = []

    def hdr(t: str) -> None:
        lines.append("")
        lines.append("=" * 70)
        lines.append(t)
        lines.append("=" * 70)

    hdr(f"PRODUCTION FILES — TOP {PRODUCTION_TOP_N} by LOC")
    for f in prod[:PRODUCTION_TOP_N]:
        lines.append(f"  {f.loc:5d}  [{f.category:<9}]  {f.path}")

    hdr("PRODUCTION FILES — bucket counts")
    pb = bucket_files(prod)
    for b in FILE_BUCKETS:
        lines.append(f"  >{b:>4} LOC : {len(pb[b])} files")
    for b in (3000, 2000, 1200):
        if pb[b]:
            lines.append(f"  files >{b}: {[f.path for f in pb[b]]}")

    hdr("PRODUCTION LARGE FILE DETAILS — top-level symbols + imports")
    for f in [item for item in prod if item.loc > 500]:
        lines.append(f"  {f.loc:5d}  [{f.category:<9}]  {f.path}")
        lines.append(f"         symbols: {', '.join(f.top_level_symbols[:24]) or '-'}")
        lines.append(f"         imports: {', '.join(f.imports[:24]) or '-'}")

    hdr("PRODUCTION FUNCTIONS — bucket counts")
    pf = bucket_funcs(prod)
    for b in FUNC_BUCKETS:
        lines.append(f"  >{b:>3} LOC : {len(pf[b])} functions")
    lines.append(f"  top {FUNCTION_TOP_N} functions:")
    for fn in sorted([fn for f in prod for fn in f.funcs], key=lambda x: -x.loc)[:FUNCTION_TOP_N]:
        lines.append(f"    {fn.loc:4d}  {fn.file}::{fn.name} (L{fn.lineno})")
    lines.append("  functions >200 LOC:")
    for fn in pf[200]:
        lines.append(f"    {fn.loc:4d}  {fn.file}::{fn.name} (L{fn.lineno})")
    lines.append("  functions >120 LOC (top 25):")
    for fn in pf[120][:25]:
        lines.append(f"    {fn.loc:4d}  {fn.file}::{fn.name} (L{fn.lineno})")

    hdr(f"TESTS FILES — TOP {TEST_TOP_N} by LOC")
    for f in tests[:TEST_TOP_N]:
        lines.append(f"  {f.loc:5d}  {f.path}")
    hdr("TESTS FILES — bucket counts")
    tb = bucket_files(tests)
    for b in FILE_BUCKETS:
        lines.append(f"  >{b:>4} LOC : {len(tb[b])} files")

    hdr("TESTS FUNCTIONS — bucket counts")
    tf = bucket_funcs(tests)
    for b in FUNC_BUCKETS:
        lines.append(f"  >{b:>3} LOC : {len(tf[b])} test funcs/helpers")
    lines.append(f"  top {FUNCTION_TOP_N} test funcs/helpers:")
    for fn in sorted([fn for f in tests for fn in f.funcs], key=lambda x: -x.loc)[:FUNCTION_TOP_N]:
        lines.append(f"    {fn.loc:4d}  {fn.file}::{fn.name} (L{fn.lineno})")
    lines.append("  test functions >120 LOC (top 10):")
    for fn in tf[120][:10]:
        lines.append(f"    {fn.loc:4d}  {fn.file}::{fn.name} (L{fn.lineno})")

    hdr("ARCHITECTURE BOUNDARY ISSUES")
    if not report.boundary_issues:
        lines.append("  none")
    for issue in report.boundary_issues:
        lines.append(f"  - {issue.rule}: {issue.file} ({issue.detail})")

    hdr("ALLOWLIST")
    if not report.allowlist:
        lines.append("  none")
    for path, reason in sorted(report.allowlist.items()):
        lines.append(f"  - {path}: {reason}")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="MindForge architecture audit")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = p.parse_args()
    report = collect_report()
    if args.json:
        out = {
            "production": {
                "top50": [asdict(f) for f in report.production[:PRODUCTION_TOP_N]],
                "buckets": {
                    b: [asdict(f) for f in fs]
                    for b, fs in bucket_files(report.production).items()
                },
                "func_buckets": {
                    b: [{"file": fn.file, "name": fn.name, "loc": fn.loc, "lineno": fn.lineno} for fn in fns]
                    for b, fns in bucket_funcs(report.production).items()
                },
                "top100_functions": [
                    asdict(fn)
                    for fn in sorted(
                        [fn for f in report.production for fn in f.funcs],
                        key=lambda x: -x.loc,
                    )[:FUNCTION_TOP_N]
                ],
            },
            "tests": {
                "top50": [asdict(f) for f in report.tests[:TEST_TOP_N]],
                "buckets": {
                    b: [asdict(f) for f in fs]
                    for b, fs in bucket_files(report.tests).items()
                },
                "func_buckets": {
                    b: [{"file": fn.file, "name": fn.name, "loc": fn.loc} for fn in fns]
                    for b, fns in bucket_funcs(report.tests).items()
                },
                "top100_functions": [
                    asdict(fn)
                    for fn in sorted(
                        [fn for f in report.tests for fn in f.funcs],
                        key=lambda x: -x.loc,
                    )[:FUNCTION_TOP_N]
                ],
            },
            "architecture": {
                "boundary_issues": [asdict(issue) for issue in report.boundary_issues],
                "allowlist": report.allowlist,
            },
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
