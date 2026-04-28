# CLI Shell Completion

MindForge 的命令行基于 [Typer](https://typer.tiangolo.com/)，自带 shell completion。
本文只记录怎么用，**不**改任何运行时行为，**不**自动写入用户的 shell rc 文件。

## 一次性查看 completion 脚本

```bash
mindforge --show-completion bash
mindforge --show-completion zsh
mindforge --show-completion fish
mindforge --show-completion powershell
```

输出会打印一段补全脚本到 stdout，**不**会修改任何文件。可以人工 source 或保存。

## 安装到当前用户的 shell

> ⚠️ 这一步会修改你的 shell rc 文件（如 `~/.zshrc` / `~/.bashrc`）。
> 如果你不想被自动改文件，请只用上面的 `--show-completion` 自己粘贴。

```bash
mindforge --install-completion
```

Typer 会自动检测当前 shell 并追加一行 source 指令。重启 shell 或 `source ~/.zshrc` 后生效。

## 卸载

直接编辑你的 shell rc 文件，删除 Typer 追加的那一行（通常以
`# Typer` 注释开头）即可。MindForge 没有提供 `--uninstall-completion`，避免
反向修改用户的 shell 配置文件。

## 与 `--vault` / `--debug` 全局选项的关系

补全会同时识别全局选项与子命令。例如：

```bash
mindforge --vault /path/to/vault <Tab>
mindforge vault <Tab>
mindforge project context <Tab>
```

## 不做的事

- ❌ 不通过补全调用 LLM、不读 .env、不发 HTTP；
- ❌ 不做"基于 vault 内容"的动态补全（避免读卡片正文并意外泄漏）；
- ❌ 不维护补全数据库或缓存。
