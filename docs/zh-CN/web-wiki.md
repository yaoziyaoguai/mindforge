# Web Wiki 页面

Web Wiki 页面提供 LLM-first synthesis 的可视化入口和 Wiki 内容浏览。

---

## 页面功能

| 功能 | 说明 |
|------|------|
| **Wiki 状态** | 显示上次生成时间、卡片基数，以及是否有新审批卡片待纳入（过期提醒） |
| **Generate Wiki** | 触发 LLM synthesis，基于所有 `human_approved` 卡片重建 Wiki |
| **Wiki 内容展示** | 结构化 topic page 的阅读视图，含目录导航 |
| **Quality / References** | 查看 Wiki 质量、引用来源和可追溯信息 |
| **Local Graph Preview** | 基于 wiki section / card 的确定性关系展示局部导航，不使用 Vector DB 或 GraphRAG |
| **Advanced** | 高级选项和 troubleshooting 回退 |

---

## Generate Wiki

点击 **Generate Wiki** 触发 LLM synthesis：

1. 系统收集所有 `human_approved` 卡片
2. 调用配置的 LLM 模型做综合归纳
3. 生成结构化 topic page（含目录、章节、引用）
4. 生成完成后页面自动更新

生成过程需要真实模型调用，耗时取决于卡片数量和模型响应速度。

---

## Advanced 区域

**Safe fallback rebuild** 是确定性模板重建，用于没有可用模型时的应急回退。

这不是推荐的 Wiki 生成路径。仅在以下场景使用：

- 模型不可用（API key 未配置、provider 宕机）
- 需要快速验证 Wiki 结构
- Troubleshooting 诊断

正常使用请走 **Generate Wiki** 主路径。

---

## 相关命令

```bash
mindforge wiki status       # CLI 查看 Wiki 状态
mindforge wiki rebuild      # CLI 触发 LLM synthesis
mindforge wiki show         # CLI 查看 Wiki 内容
```
