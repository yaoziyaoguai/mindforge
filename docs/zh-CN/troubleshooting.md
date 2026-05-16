# Troubleshooting

常见问题和诊断方法。

---

## 诊断入口

```bash
mindforge doctor
```

检查环境、配置和潜在风险。troubleshooting 的统一入口。

---

## 常见问题

### source 提示 unsupported / 不支持

**原因**：source 格式不在支持列表中。

**对策**：确认格式（详见 [Source 管理](sources.md)）。PDF / DOCX 需要安装可选依赖：`pip install "mindforge[pdf,docx]"`。旧版 `.doc` 不支持，请转换为 `.docx` 或 PDF / TXT。

### PDF 提示 scanned / no text

**原因**：PDF 仅含扫描图片，没有文字层。

**对策**：MindForge 不做 OCR。使用含文字层的 PDF，或先用 OCR 软件预处理扫描件后再导入。

### DOCX 可选依赖缺失

**原因**：`python-docx` 未安装。

**对策**：安装可选依赖：`pip install "mindforge[docx]"` 或 `pip install python-docx`，然后重新 import。

### PDF 可选依赖缺失

**原因**：`pypdf` 未安装。

**对策**：安装可选依赖：`pip install "mindforge[pdf]"` 或 `pip install pypdf`，然后重新 import。

### Wiki 页面为空

**原因**：还没有 `human_approved` 卡片。Wiki 只从已审批卡片生成。

**对策**：处理 source → 审批 ai_draft（`mindforge approve <ref> --confirm`）→ 重建 Wiki（`mindforge wiki rebuild`）。

### 模型无法生成 draft

**原因**：缺少 API key。

**对策**：在 Web Setup 中为该 model 添加 API key。

### run skipped by triage

**原因**：source 内容被 triage 判定为低价值。

**对策**：检查 `mindforge runs show <run_id>` 查看 triage 结果。

### running 持续几分钟

**原因**：真实模型处理需要时间。

**对策**：检查 `mindforge runs show <run_id>` 看当前 step。不是卡死。

### provider timed out

**原因**：endpoint / network / proxy 问题，或文档过长。

**对策**：
- 检查网络和 endpoint 可达性
- 长文档先拆分为较小 source
- 在配置中调高 `timeout_seconds` 后重新 import

### already processed / already approved

**原因**：source 已处理过。

**对策**：不会重复生成 draft。如有需要，在 Web Sources 中 Process now。

### approve number ref expired

**原因**：审批后编号失效。

**对策**：重新 `mindforge approve list` 获取最新编号。

### Web port already in use

**原因**：已有 `mindforge web` 进程运行，或端口被其他程序占用。

**对策**：换端口启动：
```bash
mindforge web --port 8766 --open
```

### stale web process / wrong venv

**原因**：venv 未激活或安装不完整。

**对策**：确认 venv 已激活且 `pip install -e .` 成功。

### `mindforge: command not found`

**原因**：MindForge 未安装到当前环境。

**对策**：
```bash
source .venv/bin/activate
pip install -e .
```

---

## Provider 错误

| 现象 | 原因 | 对策 |
|------|------|------|
| Provider failure | Provider 构建失败 | 检查 Web Setup 中模型的 type / base_url / model |
| HTTP 401/403 | API key 错误/过期 | 回到对应平台检查 key 状态 |

---

## 安全提醒

- API key 不要粘贴到聊天、issue、logs 或文档中
- API key 不进 YAML，不进 Git
- 如怀疑 key 泄露，立即到对应平台轮换
