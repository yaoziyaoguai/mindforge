# Autopilot Simplification Analysis

Post-Mint4 Remediation P4 — 只分析，不实施。
分析日期: 2026-05-28.
源文件: `.claude/commands/mf-autopilot.md` (1015 lines).

---

## 1. Structure Breakdown

Total: 1015 lines, ~34 top-level sections, ~47 sub-sections.

### Section Size Distribution

| Section | Lines (est.) | % | Cumulative |
|---------|---------------|---|-----------|
| §0 Roadmap-authorized execution | ~35 | 3.4% | 3.4% |
| §1 Repo facts | ~20 | 2.0% | 5.4% |
| §2 Read docs | ~20 | 2.0% | 7.4% |
| §3 Task type selection | ~60 | 5.9% | 13.3% |
| §4 Legacy phase detection | ~25 | 2.5% | 15.8% |
| §5 Auto loop execution | ~200 | 19.7% | 35.5% |
| §6 Allowed scope | ~40 | 3.9% | 39.4% |
| §7 Hard red lines | ~30 | 3.0% | 42.4% |
| §8 Gate rules | ~50 | 4.9% | 47.3% |
| §9 Commit/push rules | ~15 | 1.5% | 48.8% |
| §10 Output report | ~50 | 4.9% | 53.7% |
| §11 Recursive remediation | ~40 | 3.9% | 57.6% |
| §12 Failure classification | ~100 | 9.8% | 67.4% |
| §13 Retry policy | ~20 | 2.0% | 69.4% |
| §14 Mandatory skill gates | ~80 | 7.9% | 77.3% |
| §15 Skill framework discovery | ~30 | 3.0% | 80.3% |
| §16 Skill routing decision | ~30 | 3.0% | 83.3% |
| §17 Review node rules | ~25 | 2.5% | 85.8% |
| §18 Post-loop self-routing | ~40 | 3.9% | 89.7% |
| §19-22 Schema + Report | ~60 | 5.9% | 95.6% |
| Hard prohibitions + misc | ~45 | 4.4% | 100% |

§5 (Auto loop execution) is by far the largest section at ~20%, containing auto-continue contract, progress template, workstream rules, stop reasons, context policy, handoff protocol, auto-continue decision table, and banned phrases.

---

## 2. Evidence-Based Trigger Analysis

Based on progress-ledger entries from ~30 actual `/mf-autopilot` loops:

### Frequently Triggered (≥5 loops)
| Rule | Evidence |
|------|----------|
| §1 建立工程事实 | Every loop starts with git status/log |
| §8 Gate rules | Every loop ends with gates |
| §9 Commit/push rules | Every completed loop commits + pushes |
| §10 输出报告 | Every loop produces a report |
| §5.3 workstream rules | Multiple workstream switches tracked |

### Occasionally Triggered (2-4 loops)
| Rule | Evidence |
|------|----------|
| §2 读取工程宪法 | Read multiple times, mostly §1-3 of required files |
| §5.5 Context policy | Context < 15% triggered handoff at least once |
| §5.6 Handoff protocol | HANDOFF.md written when context low |
| §7 全局硬红线 | HARD_STOP_PRODUCT_DECISION triggered 2-3 times |
| §3 Task type selection | Task type classification used in recent loops |
| §11-12 Remediation + Failure | Used in last 3 autopilot_governance runs |
| §16 Skill routing decision | Output in recent loops |
| §18 Post-loop self-routing | OUTPUT in recent loops |

### Rarely/Never Triggered (0-1 loops)
| Rule | Evidence |
|------|----------|
| §4 Legacy phase detection (A-G) | Superseded by §3 task type selection — "Legacy" label in title |
| §5.1 Auto-continue contract | Never explicitly referenced; overridden by §5.7 table |
| §5.7 Auto-continue decision table vs §5.9 banned phrases | Largely redundant — same information |
| §6 允许自动继续的范围 vs §0 scope table | Substantial overlap with §0 Roadmap-authorized scope |
| §12 Failure class #8 (docs truth) | Never triggered independently of other classes |
| §12 Failure class #9 (skill routing) | Never triggered in practice |
| §14.4 Audit/red-team mandatory skills | Codex adversarial review never called |
| §15 Skill framework discovery | Stub — "check available skills" but never has actual discovery output |
| §17 Review node rules | Partially redundant with §18 post-loop self-routing review check |
| §19 CPS queue schema | Format documented but never validated against actual CPS |
| §20 Progress ledger schema | Documented but not enforced by gate |
| §21 HANDOFF schema | Duplicate of §5.6 handoff content |
| §22 Updated report template | Partially used; mixed with §10 original report template |

---

## 3. Redundancy Analysis

### 3.1 Direct Duplication

| Redundant Content | Location 1 | Location 2 | Overlap |
|------------------|------------|------------|---------|
| Hard prohibitions list | §7 全局硬红线 | 末尾 `硬性禁止` section | ~90% overlap |
| HANDOFF.md template | §5.6 Handoff protocol | §21 HANDOFF schema | ~80% overlap |
| Report template | §10 输出报告 | §22 Updated report template | ~70% overlap |
| Scope/allow-rules | §0 scope table | §6 允许自动继续的范围 | ~60% overlap |
| Auto-continue rules | §5.1 contract | §5.7 decision table | ~50% overlap |
| Skill routing format | §16 decision block | §18 post-loop routing block | ~40% overlap |

### 3.2 Conceptual Redundancy

- **Stop reasons** appear in 3 places: §5.4 (stop reason codes), §7 (hard red lines), §5.7 (must ask user table). Same concepts, slightly different wording.
- **Gate rules** in §8 overlap with general quality expectations already in system prompt.
- **Report template** in §10 and §22 exist side by side. Should be one.

### 3.3 Self-Referential Layers

The autopilot has at least 3 self-referential governance layers:
1. **§11-13**: Rules about how to fix rules that fail
2. **§14-16**: Rules about which skills to use when fixing rules
3. **§17-18**: Rules about how to review the output of fixing rules

Layer 1 is useful (recursive remediation). Layers 2-3 are where complexity compounds without proportional value.

---

## 4. Complexity Density Map

High complexity density (rules per line):

| Area | Density | Issue |
|------|---------|-------|
| §5.5-5.9 (Context + Handoff + Decision + Phrases) | Very high | 5 sub-sections covering essentially: "when to stop" |
| §11-18 (Remediation + Skills + Review + Routing) | Very high | 8 sections for what conceptually is: "fix failures and route correctly" |
| §0 Scope table | Medium | The table is clear but duplicates §6 |
| §3 Task type table | Medium | 9 task types with separate entry sequences — most converge on same pattern |

---

## 5. Simplification Opportunities

### 5.1 High-Impact, Low-Risk

| # | Change | Lines Saved | Risk |
|---|--------|-------------|------|
| 1 | Merge §0 scope table + §6 into one section | ~30 | Low |
| 2 | Merge §7 hard red lines + 末尾 hard prohibitions | ~20 | Low |
| 3 | Merge §10 + §22 report templates | ~30 | Low |
| 4 | Merge §5.6 + §21 HANDOFF schemas | ~25 | Low |
| 5 | Remove §4 Legacy phase detection (A-G) — superseded by §3 | ~25 | Low |
| 6 | Merge §5.1 + §5.7 auto-continue rules | ~20 | Low |
| 7 | Merge §5.4 stop reasons + §7 hard red lines + §5.7 must-ask table | ~40 | Medium |

**Subtotal: ~190 lines (~19% reduction, 1015 → ~825)**

### 5.2 Medium-Impact, Requires Care

| # | Change | Lines Saved | Risk |
|---|--------|-------------|------|
| 8 | Flatten §11-18 (remediation + skills + review) from 8 sections to 3 | ~80 | Medium |
| 9 | Remove §14.4 audit/red-team mandatory skills (never used) | ~20 | Low |
| 10 | Remove §15 skill framework discovery stub (never yields actual output) | ~30 | Low |
| 11 | Consolidate §17 review node rules into §18 post-loop self-routing | ~15 | Low |

**Subtotal: ~145 lines (~14% reduction)**

### 5.3 Total Potential

- Conservative (items 1-7): 1015 → ~825 (-19%)
- Aggressive (items 1-11): 1015 → ~680 (-33%)

---

## 6. Self-Referential Risk Assessment

**Risk: medium.** The autopilot now contains rules governing:
- How to modify itself (§14-18 skill routing for `autopilot_governance` task type)
- How to fix its own failures (§11-13 recursive remediation)
- How to check if its own output is correct (§17 review, §18 self-routing)

This creates a **self-amplifying complexity loop**: every new governance rule adds surface area for future failures, which in turn requires more remediation rules.

**Specific risks:**
1. **Skill routing for autopilot_governance**: §14 mandates Compound Engineering / G-stack / Superpowers checks for autopilot changes. But these framework skills are sometimes unavailable. The fallback path (direct mf-autopilot) then creates a "required skill not invoked" failure per §14 rules, which triggers remediation back to §12 failure class #9.
2. **Recursive remediation of remediation**: If §11-13 remediation rules themselves fail (e.g., wrong failure classification), there's no meta-remediation rule. Good — don't add one.
3. **CPS queue as source of truth**: §19 defines the queue schema, but the actual CPS queue is human-maintained HTML comments. A mismatch between schema and reality hasn't triggered any gate.

**Mitigation already in place:** §7 hard red lines prevent infinite recursion (max 2 retries, HARD_STOP after).

---

## 7. Recommendations

### Immediate (could do in P4 implementation if authorized)

1. **Merge the 7 high-impact items** (items 1-7 above). Save ~190 lines, reduce cognitive load.
2. **Flatten remediation + skills + review** (items 8-11). Save ~145 more lines.
3. **Delete §4 Legacy phase detection** — it's labeled "Legacy" and superseded.

### Deferred (needs more discussion)

4. **Consider whether §14-16 skill routing granularity is worth the complexity.** The mandatory skill gates have never actually triggered a skill invocation that changed an outcome. They add ~140 lines of rules that primarily serve as documentation of intent.
5. **Consider a periodic "autopilot health check" gate** that verifies CPS queue format matches schema, progress-ledger entries have all required fields, etc. This would catch the truth-drift that currently relies on human review.

### Do Not Do

- Do not add more remediation layers
- Do not add a "meta-autopilot" to govern the autopilot
- Do not convert analysis into implementation without explicit authorization

---

## 8. Conclusion

The `/mf-autopilot` has grown from a simple workflow router to a 1015-line self-governing system with recursive remediation, mandatory skill gates, and multi-layer review. It works — evidenced by ~30 successful loops — but carries ~35% structural overhead (redundant sections, unused rules, self-referential complexity).

The recommended simplification path reduces to ~680-825 lines without removing any functional capability. The biggest risk in simplification is accidentally removing a rule that turns out to be load-bearing, which is why this analysis recommends merging/consolidating rather than deleting.

**This analysis is the P4 deliverable.** Implementation requires a separate authorization.
