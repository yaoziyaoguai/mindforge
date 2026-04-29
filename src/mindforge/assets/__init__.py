"""Bundled runtime assets for packaged MindForge installs.

中文学习型说明：这些文件是 CLI 默认路径的一部分，不是业务逻辑。放进
package 后，`process` 和 `init` 在 wheel/install 场景下不再依赖仓库根目录。
用户显式传入的 `--prompts-dir` / `--tracks` / `--template` 仍然优先。
"""
