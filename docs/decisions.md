# Decisions

> 本文档回答：之前为什么这样决定的？
>
> 按时间线追加，不按领域分类。历史条目不可修改。

## 当前有效决策摘要

> 此区域由 Stage 6（Entropy Check）维护。当 Superseded 条目过多时，agent 将所有状态为 Accepted 的决策提炼为一句话摘要放在此处。Agent 日常只需读此摘要即可。

当前仅有 D-001，无需摘要。

## 维护规则（强制）

1. **只追加，不修改**历史条目内容。
2. 若决策失效，新增一条"替代决策"，并引用旧编号，旧条目状态改为 `Superseded by D-0XX`。
3. 每条必须包含：背景、决策、原因、被拒绝方案。
4. **Compaction 规则**：当 Superseded 条目超过总条目的 30% 时，在 Stage 6 执行 compaction——将所有 Accepted 条目提炼为一句话摘要，更新到"当前有效决策摘要"区域。历史记录区域保持不变。

## 记录模板

```markdown
## D-00X 标题
- 日期：YYYY-MM-DD
- 状态：Proposed | Accepted | Superseded by D-0XX
- 背景：
- 决策：
- 原因：
- 被拒绝方案：
  - 方案 A：拒绝原因
  - 方案 B：拒绝原因
- 影响：
```

## 决策记录

## D-001 初始化 Agent Workflow 文档体系
- 日期：2026-03-30
- 状态：Accepted
- 背景：该仓库在已有代码和实验资产的基础上接入 Agent Workflow Template，需要先把当前事实沉淀为可维护文档，再逐步收敛到统一流程。
- 决策：采用 Agent Workflow Template 的 AGENTS.md + docs/ + issue_test/ + scripts/ 结构。
- 原因：文档驱动的工作流架构，每个文档职责单一且解耦；SubGraph 状态机提供清晰的 Stage 跳转逻辑；issue_test/ + scripts/run_issue_tests.sh 提供按 issue 累积的确定性回归检查；build_context.py 强制 Agent 在正确的 context 下执行。
- 被拒绝方案：
  - 纯 prompt 约束：缺乏持久化和可审计的流程文档
  - 单 README 承载全部规则：难维护，无法结构化引用
- 影响：后续所有 Agent 开发流程按此文档体系执行；stage.lock 记录全局状态，build_context.py 机械组装 context，issue_test/ 持续沉淀历史回归脚本。
