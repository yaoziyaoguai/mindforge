"""v4.2 Package safety tests — 验证 wheel/sdist 构建产物不含敏感文件。

中文学习型说明：此测试确保 .mindforge/、secrets.json、*.key、*.token
等敏感文件不会通过 wheel/sdist 打包泄露。不读取任何 secret 内容。

v4.2.1 新增 artifact-level wheel 测试：实际构建 wheel 并检查产物内容。
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class TestPackageSafety:
    """验证项目文件结构和构建配置中的安全性。"""

    def test_gitignore_blocks_mindforge_dir(self):
        """.mindforge/ 目录在任何层级都应被 .gitignore 阻塞。"""
        gitignore = ROOT / ".gitignore"
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        has_pattern = any(
            line.strip() == ".mindforge/" or line.strip() == ".mindforge"
            for line in lines
        )
        assert has_pattern, ".gitignore 必须包含 .mindforge/ 模式"

    def test_gitignore_blocks_env_files(self):
        """.env 文件应被 .gitignore 阻塞（.env.example 除外）。"""
        gitignore = ROOT / ".gitignore"
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        has_env = any(line.strip() == ".env" for line in lines)
        has_env_wildcard = any(line.strip() == ".env.*" for line in lines)
        assert has_env, ".gitignore 必须包含 .env 模式"
        assert has_env_wildcard, ".gitignore 必须包含 .env.* 模式"

    def test_pyproject_toml_excludes_mindforge(self):
        """pyproject.toml 的 wheel target 必须排除 .mindforge/。"""
        pyproject = ROOT / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert (
            "src/mindforge/assets/.mindforge/**" in content
        ), "pyproject.toml 的 exclude 必须包含 .mindforge/"
        assert ".mindforge" in content, (
            "pyproject.toml 必须提及 .mindforge 排除规则"
        )

    def test_no_sensitive_files_in_assets(self):
        """assets/ 目录下不应有 git-tracked 的 secrets/token/key 文件。"""
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
        pyproject = ROOT / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        if "src/mindforge/assets/**" in content:
            assert "exclude" in content, (
                "include 了 assets/** 但缺少 exclude 规则："
                "必须在 pyproject.toml 中排除 .mindforge/"
            )


class TestWheelArtifactSafety:
    """v4.2.1: 实际构建 wheel 并检查产物不含敏感文件。

    中文学习型说明：配置文件检查（exclude/gitignore）是必要的，但不充分。
    此类测试实际运行 pip wheel 构建，解压产物，逐文件检查是否泄露敏感内容。
    不读取任何 secret 内容，不将构建产物加入 git。
    """

    # 必须不出现在 wheel 文件名中的敏感模式
    SENSITIVE_PATTERNS = (".mindforge", "secrets.json", ".key", ".token", ".env")

    def test_wheel_artifact_excludes_sensitive_files(self):
        """构建 wheel 产物，验证不含 .mindforge/secrets.json/*.key/*.token。"""
        tmpdir = Path(tempfile.mkdtemp(prefix="mindforge-wheel-test-"))
        try:
            # 构建 wheel 到临时目录
            result = subprocess.run(
                ["python", "-m", "pip", "wheel", str(ROOT), "--no-deps",
                 "-w", str(tmpdir), "--no-cache-dir"],
                capture_output=True, text=True,
                timeout=120,
            )
            assert result.returncode == 0, (
                f"wheel build failed (exit {result.returncode}):\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )

            # 找到构建的 wheel 文件
            wheels = list(tmpdir.glob("mindforge-*.whl"))
            assert len(wheels) > 0, f"未找到 wheel 产物于 {tmpdir}"
            wheel_path = wheels[0]

            # 检查 wheel 内文件列表
            with zipfile.ZipFile(wheel_path, "r") as zf:
                for name in zf.namelist():
                    name_lower = name.lower()
                    for pattern in self.SENSITIVE_PATTERNS:
                        assert pattern not in name_lower, (
                            f"wheel 产物包含敏感路径: {name} (匹配 {pattern})"
                        )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_wheel_artifact_builds_successfully(self):
        """wheel 构建应成功，产物应可被 zipfile 打开。"""
        tmpdir = Path(tempfile.mkdtemp(prefix="mindforge-wheel-build-"))
        try:
            result = subprocess.run(
                ["python", "-m", "pip", "wheel", str(ROOT), "--no-deps",
                 "-w", str(tmpdir), "--no-cache-dir"],
                capture_output=True, text=True,
                timeout=120,
            )
            assert result.returncode == 0, (
                f"wheel 构建失败 (exit {result.returncode})"
            )
            wheels = list(tmpdir.glob("mindforge-*.whl"))
            assert len(wheels) == 1, f"期望 1 个 wheel，得到 {len(wheels)} 个"
            assert zipfile.is_zipfile(wheels[0]), "产物不是有效的 zip 文件"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
