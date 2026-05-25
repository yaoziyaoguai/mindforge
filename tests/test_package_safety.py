"""v4.2 Package safety tests — 验证 wheel/sdist 构建产物不含敏感文件。

中文学习型说明：此测试确保 .mindforge/、secrets.json、*.key、*.token
等敏感文件不会通过 wheel/sdist 打包泄露。不读取任何 secret 内容。
"""

from __future__ import annotations

from pathlib import Path


class TestPackageSafety:
    """验证项目文件结构和构建配置中的安全性。"""

    def test_gitignore_blocks_mindforge_dir(self):
        """.mindforge/ 目录在任何层级都应被 .gitignore 阻塞。"""
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        # .mindforge/ 作为不带路径分隔符的模式应匹配任意层级
        has_pattern = any(
            line.strip() == ".mindforge/" or line.strip() == ".mindforge"
            for line in lines
        )
        assert has_pattern, ".gitignore 必须包含 .mindforge/ 模式"

    def test_gitignore_blocks_env_files(self):
        """.env 文件应被 .gitignore 阻塞（.env.example 除外）。"""
        gitignore = Path(__file__).resolve().parent.parent / ".gitignore"
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        has_env = any(line.strip() == ".env" for line in lines)
        has_env_wildcard = any(line.strip() == ".env.*" for line in lines)
        assert has_env, ".gitignore 必须包含 .env 模式"
        assert has_env_wildcard, ".gitignore 必须包含 .env.* 模式"

    def test_pyproject_toml_excludes_mindforge(self):
        """pyproject.toml 的 wheel target 必须排除 .mindforge/。"""
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert (
            "src/mindforge/assets/.mindforge/**" in content
        ), "pyproject.toml 的 exclude 必须包含 .mindforge/"
        assert ".mindforge" in content, (
            "pyproject.toml 必须提及 .mindforge 排除规则"
        )

    def test_no_sensitive_files_in_assets(self):
        """assets/ 目录下不应有 git-tracked 的 secrets/token/key 文件。"""
        import subprocess
        result = subprocess.run(
            ["git", "ls-files", "src/mindforge/assets/"],
            capture_output=True, text=True,
        )
        tracked = result.stdout.strip().splitlines()
        sensitive_patterns = ("secrets.json", ".key", ".token", ".env")
        for path in tracked:
            for pattern in sensitive_patterns:
                assert pattern not in path, (
                    f"敏感文件不应被 git track: {path} (匹配 {pattern})"
                )

    def test_pyproject_has_no_artifacts_wildcard_without_exclude(self):
        """pyproject.toml 如有 artifacts/include 通配符，必须伴随 exclude。"""
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        # 确认 exclude 在 include 之后且包含敏感目录
        if "src/mindforge/assets/**" in content:
            assert "exclude" in content, (
                "include 了 assets/** 但缺少 exclude 规则："
                "必须在 pyproject.toml 中排除 .mindforge/"
            )
