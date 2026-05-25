# MindForge v4.2 Post-Remediation Red Team Re-Audit

**日期**: 2026-05-25  
**范围**: commit `715f44c fix: red-team stabilize graph and docs truth` 之后的 v4.2 remediation truth、当前产品方向、文档真实性、测试/gate 可信度  
**方法**: 只读审计 production code + 文档事实修正；不改 `src/`、`tests/`、`web/src/`  

---

## Executive Summary

v4.2 remediation **有效但不完整**。它解决了最危险的 backend/API 层过度暴露：Graph API 现在只正式支持 `card` / `source` / `tag` / `wiki_section`，不支持的 `community` / `topic` / `entity` / `concept_candidate` 会返回 422；Sensemaking 后端 docstring 已标为 LAB/INTERNAL；Sidebar 已移除 Graph 和 Sensemaking 主导航；package secret 风险通过 `.mindforge/**` exclude 和 git ignore 降低。

但严格复审后，v4.2 仍不是 feature-expansion green light：

- `/graph` 独立页仍展示 8 种 NodeType selector，其中 4 种会被 API 422，UI truth reset 不完整。
- Sensemaking 独立路由仍用 “Sensemaking Workspace / Analyze / bridge/evolution/influence” 这类成熟产品语言，页面本身没有 LAB/INTERNAL 可见标识。
- package safety tests 检查了 pyproject / `.gitignore` / git tracked files，但没有构建 wheel/sdist 并断言产物内不存在 `.mindforge` / `secrets.json` / `*.key` / `*.token`。
- README truth reset 基本完成；user guides 和关键 notes 已在本轮修正；但旧 ADR / roadmap / older implementation notes 仍残留 v4.2 前的 graph/sensemaking 过度声明，需要 Documentation System Reset 或 archive。

**Updated overall score: 5.5/10**, 高于上一轮红队 `5.1/10`，但仍是 **No-Go for feature expansion**。下一阶段应优先做 **Product Main Path Dogfood**，用非敏感资料验证 `Source/Import → ai_draft → Review → approve → Library → Recall/Wiki → Export`，不要恢复图谱扩张或进入 v4.3。

---

## Repo Facts

| Command | Result |
|---|---|
| `pwd` | `/Users/jinkun.wang/work_space/mindforge` |
| `git status --short` | clean at audit start |
| `git rev-parse --abbrev-ref HEAD` | `main` |
| `git rev-list --left-right --count @{u}...HEAD || true` | `0 0` |
| `git log --oneline -20` | HEAD `715f44c fix: red-team stabilize graph and docs truth`; prior graph line includes v4.1/v4.0/v3.9/v3.8/v3.7 commits |

---

## v4.2 Remediation Truth Table

| Area | Verdict | Evidence | Residual Risk |
|---|---|---|---|
| A. Package secret risk | **PARTIAL** | `pyproject.toml` has wheel `include = ["src/mindforge/assets/**"]` plus `exclude = ["src/mindforge/assets/.mindforge/**"]`; `.gitignore` blocks `.mindforge/`; `git ls-files src/mindforge/assets/` does not list sensitive files. `tests/test_package_safety.py` checks pyproject, `.gitignore`, and git-tracked asset names. | Tests do not build wheel/sdist and inspect artifacts. `src/mindforge/assets/.mindforge/secrets.json` exists locally but was not read; the safety relies on exclude + untracked status, not artifact-level proof. |
| B. Graph exposed NodeType truth reset | **PARTIAL** | Backend/API are aligned: `routers/graph.py` supports only `card/source/wiki_section/tag`; unsupported types are explicit 422. `tests/relations/test_graph_api.py` covers unsupported types and candidate graph not exposed as fact. | `/graph` still displays 8 selector buttons; `web/src/api/types.ts` and `schemas.py` still expose the 8-type ontology in response types; ADR-007 still overclaims 8-type workload. |
| C. Sensemaking downgrade | **PARTIAL** | `sensemaking.py` module docstring is LAB/INTERNAL and calls out heuristic limits. Sidebar no longer links `/sensemaking`. Tests assert module docstring is lab/internal and not production-ready. | `/sensemaking` route still exists, page title remains “Sensemaking Workspace”/“知识理解工作台”, no visible lab badge, and API route docstring still sounds like a product capability. |
| D. Gate false-positive remediation | **PARTIAL** | Target no-op tests were replaced in graph/sensemaking areas; `assert len(result) >= 0` pattern no longer appears in the targeted graph/sensemaking tests. Unsupported Graph semantics have negative tests. | Product copy tests do not assert Graph/Sensemaking removal from main nav or GraphPage selector contraction. Previous timeout-vs-pass reports cannot be proven from static docs; current-loop gates must be treated as the fresh source of truth. |
| E. Docs truth reset | **PARTIAL** | README now states graph/sensemaking lab/internal and 4 NodeTypes. This audit updated user guides to remove the nonexistent Import/Export page, updated architecture, and added v4.2 correction notes to v3.8/v4.0/v4.1 implementation notes. | ADR-007 and older roadmap/spec/history docs still contain pre-v4.2 claims. Full docs system reset/archive is still open. |

---

## Updated Scorecard

| Dimension | Old | New | Change | Reason / Evidence |
|---|---:|---:|---|---|
| Architecture | 5.0 | 5.4 | improved | Backend/API Graph exposure is narrower and safer, but `web_facade.py` and `schemas.py` remain god modules; graph/sensemaking routes still leak experimental surfaces. |
| Code Quality | 5.3 | 5.4 | unchanged/slight improved | v4.2 added targeted guards/tests, but no broader simplification. UI truth issue remains in GraphPage. |
| Documentation Truthfulness | 4.0 | 5.6 | improved | README and user guides now better reflect current state; v4.1/v3.8/v4.0 notes now carry correction notices. ADR/old plans still stale. |
| User Usability | 4.2 | 4.7 | improved | Main nav is less misleading. The actual first-run/dogfood path is still not proven with real non-sensitive material. |
| Product Value | 5.4 | 5.4 | unchanged | Core loop remains plausible; no new product proof was generated. |
| Safety Semantics | 7.0 | 7.6 | improved | Unsupported graph fact/candidate confusion now gets 422; package secret risk is reduced; approval boundary remains protected. |
| Test/Gate Reliability | 5.0 | 6.2 | improved | Negative graph tests and no-op cleanup help, but artifact package test and UI truth contract are missing. |
| Feature Focus | 3.2 | 4.8 | improved | Lab features are hidden from sidebar and docs now warn against expansion; stale routes still exist. |
| Maintainability | 4.7 | 4.9 | unchanged/slight improved | Truth docs help maintenance, but code modularity debts remain open. |
| Innovation Value | 5.0 | 5.0 | unchanged | Deterministic graph ideas are interesting but not yet product-validated; innovation should not outrun dogfood. |

**Overall**: **5.5/10**. This is better than `5.1/10`, but still below the threshold for feature expansion.

---

## Residual Findings

### P0

None found in this audit. No evidence of auto-approval, real LLM calls, embedding/vector DB, or secret content read during this audit.

### P1

| ID | Finding | Evidence | Required Next Action |
|---|---|---|---|
| P1-01 | GraphPage still exposes unsupported NodeTypes | `web/src/pages/GraphPage.tsx` `EXPLORABLE_TYPES` contains `community`, `topic`, `entity`, `concept_candidate`; API returns 422 for those. | Next stabilization loop should contract GraphPage selector to supported types or add explicit unsupported/lab affordance. |
| P1-02 | Package safety lacks artifact-level proof | `tests/test_package_safety.py` checks config/git-tracked files, not built wheel/sdist contents. | Add focused artifact inspection test or documented packaging gate before release. |

### P2

| ID | Finding | Evidence | Required Next Action |
|---|---|---|---|
| P2-01 | Sensemaking page still presents mature workspace language | Page title and action text are not visibly lab/internal. | Hide route more deeply or label it clearly in UI before exposing to users. |
| P2-02 | Documentation corpus remains too large and stale | 80+ implementation notes and multiple old roadmaps/ADRs contain pre-v4.2 graph claims. | Documentation System Reset: canonical docs + archive. |
| P2-03 | web_facade.py / schemas.py remain god modules | `web_facade.py` > 2000 lines, `schemas.py` > 1300 lines. | Architecture simplification after product dogfood identifies true boundaries. |
| P2-04 | Product copy tests miss key product-truth contracts | No test asserts Graph/Sensemaking absence from sidebar or GraphPage supported selector set. | Add tests in a stabilization loop, not during this docs-only audit. |

### P3

| ID | Finding | Evidence | Required Next Action |
|---|---|---|---|
| P3-01 | `assets/__pycache__` exists locally under package include root | Local file listing showed `src/mindforge/assets/__pycache__/...`; not tracked and not a secret. | Clean local build artifacts or add exclude if packaging proves noisy. |

---

## Updated Feature Value Matrix

| Capability | Value Class | Main Nav? | Internal/Lab? | Continue Polish? | Archive/Hide? | Next Step |
|---|---|---:|---:|---:|---:|---|
| Knowledge Card | Core | Yes via Library/Review | No | Yes | No | Dogfood card creation, review, edit, provenance. |
| `ai_draft` / `human_approved` | Core | Indirect | No | Yes | No | Keep explicit approval semantics central. |
| Review / Approval | Core | Yes | No | Yes | No | User-path tests and copy polish. |
| Import | Core | Sources | No | Yes | No | Validate non-sensitive folder/paste import in dogfood. |
| Library | Core | Yes | No | Yes | No | Make card detail, export selection, provenance ergonomic. |
| Recall / Search | Core | Yes | No | Yes | No | Dogfood BM25 usefulness and failure modes. |
| Wiki | Core/Support | Yes | No | Yes | No | Validate approved-only synthesis path; no auto rebuild. |
| Export | Support | Library | No | Yes | No | Prove JSON/OPML/Zip on real non-sensitive data. |
| Graph View | Experimental | No | Yes | Later | Hide unsupported selectors | Rebuild only as narrow evidence graph after dogfood. |
| Entity Resolution | Experimental | No | Yes | No now | Hide | Keep as candidate-only until user confirmation workflow exists. |
| ConceptCandidate | Experimental | No | Yes | No now | Hide | Do not expose as fact graph. |
| Topic / Community | Support/Experimental | No standalone | Partial lab | Limited | Hide as graph NodeType | Keep Library community browser if useful; no graph expansion. |
| Sensemaking Workspace | Experimental/Low Value | No | Yes | No now | Hide/label | Do not promote until semantics are real. |
| Retrieval Context Composer | Support | No | Internal | Maybe | No | Keep as explainable context, not answerer/RAG. |
| Dogfood Scenario | Support | Dogfood internal | Internal | Yes | No | Convert to real non-sensitive dogfood evidence. |
| Provider Readiness | Support | Setup | No | Yes | No | Needed before safe real use; no key exposure. |
| Extension / Plugin Boundary | Experimental | No | Yes | No now | Hide | Do not build plugin system before product path proves demand. |
| Graph Backend Decision | Support/Internal | No | Internal | Maybe | No | Revisit only after scale/perf evidence. |
| Quality Debt / Gate | Core Engineering | No | Internal | Yes | No | Add artifact package gate and UI truth contracts. |
| ADR / Specs / Implementation Notes flow | Support | No | Internal | Yes | Archive old docs | Documentation reset to reduce stale claims. |

---

## Product Main Path Verdict

The real product path is clear and should be the next evaluation unit:

```
Source / Import → ai_draft → Review → explicit approval → human_approved
→ Library → Recall / Wiki → Export
```

Current verdict: **Promising but not proven by real dogfood**. The code and docs describe a coherent local-first knowledge loop, but the project has spent too much recent effort on graph/sensemaking breadth. The next phase should measure whether a user can actually use MindForge on 50-100 non-sensitive local documents without relying on implementation knowledge.

---

## Documentation Truth Verdict

Current verdict: **Improved, still partial**.

What is now better:
- README says graph/sensemaking are lab/internal and graph support is 4 NodeTypes.
- User guides no longer claim a standalone Import/Export page.
- Architecture now states current graph support and lab/internal sensemaking status.
- Key v3.8/v4.0/v4.1 implementation notes carry v4.2 correction notices.

Remaining truth debt:
- ADR-007 still records “8 types” workload as if it were validated.
- Old roadmap/spec/history docs still contain aspirational graph/sensemaking language.
- The docs corpus is too large for a user or future agent to know what is canonical.

---

## Safety Verdict

Current verdict: **Materially improved; no P0 found**.

Safety boundaries that held:
- Explicit approval / `human_approved` boundary remains guarded by tests.
- Unsupported Graph candidate/fact node types no longer silently return success through API.
- No real LLM, Cubox, Upstage, embedding, vector DB, real private data, or Obsidian vault write was used in this audit.
- No secret content was read.

Residual safety-related risk:
- Packaging safety needs a built-artifact assertion before release.
- UI still invites unsupported Graph API calls from `/graph`.

---

## Gate / Test Verdict

Fresh gate results from this audit are the only trusted evidence. Historical notes that reported timeouts as pass cannot be proven from static review. The final gate table below must be read together with the commit containing this audit.

| Command | Timeout | Real Exit Code | Summary |
|---|---|---:|---|
| `git diff --check` | no | 0 | clean |
| `ruff check src/ tests/ docs/` | no | 0 | `All checks passed!` |
| `python -m pytest tests/test_package_safety.py -q --tb=short` | no | 0 | 5 passed |
| `python -m pytest tests/relations/test_graph_builder.py tests/relations/test_graph_api.py tests/test_sensemaking.py -q --tb=short` | no | 0 | completed to 100%, no failures |
| `python -m pytest tests/test_web_product_copy.py -q --tb=short` | no | 0 | completed to 100%, no failures |
| `npm --prefix web run build` | no | 0 | build succeeded; Vite emitted existing chunk-size/dynamic-import warnings |
| `python -m pytest tests/ -q --tb=short` | no | 0 | optional full gate completed to 100%; one skip marker observed; no failures |

---

## Recommended Strategic Direction

### Primary Recommendation: A. Product Main Path Dogfood

Use 50-100 non-sensitive real local materials to dogfood:

```
Source/Import → ai_draft → Review → approve → Library → Recall/Wiki → Export
```

Why:
- It directly answers whether MindForge has a usable product, not just a feature inventory.
- It will expose onboarding, state, copy, import, review, recall, wiki, and export issues in the order users hit them.
- It prevents graph/sensemaking from consuming another cycle before the core workflow is proven.

### Secondary Recommendation: C. Documentation System Reset

After or alongside dogfood reporting, reduce docs to canonical docs + archive:
- README
- user guides
- architecture
- quality debt ledger
- current limitations
- current ADRs

Why:
- v4.2 showed that stale docs can become product risk.
- A smaller canonical docs set reduces future audit cost.

### Defer

- B. Architecture Simplification: useful, but dogfood should identify real module boundaries first.
- D. Graph View Rebuild: only after main path dogfood is stable.
- E. Safe Real Dogfood Readiness: useful before real LLM use, but not a substitute for product-path dogfood.

---

## What Not To Do Next

- Do not start v4.3.
- Do not add graph/community/entity/sensemaking features.
- Do not introduce RAG, embedding, vector DB, GraphRAG, or graph DB dependencies.
- Do not split architecture abstractly before dogfood shows the pressure points.
- Do not treat Sensemaking as a primary product surface.
- Do not claim package safety is release-grade until wheel/sdist artifacts are inspected.
- Do not continue writing broad implementation notes without a canonical docs/archive reset.
