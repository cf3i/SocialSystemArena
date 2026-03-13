# Pattern Souls Hardening Rules

This directory stores pattern-level default SOP templates used by runtime prompt composition.

## Scope
- `Pattern Rules` are cross-institution defaults.
- Institution-specific semantics must live in `systems/institutions/*/souls/*.md`.
- Runtime precedence is: `Institution SOP` overrides `Pattern Rules`.

## Authoring Rules
1. Keep pattern templates generic; do not include specific institutions or historical actors.
2. Every file must include these sections:
   - `任务上下文:`
   - `模式定位（默认规则）:`
   - `硬规则:`
   - `决策策略:`
   - `建议输出:`
3. Every file should constrain `decision` to `allowed_decisions` (except ballot-only stage in consensus, which remains `yes/no`).
4. Keep alias files identical with their canonical files:
   - pipeline: `planner.md == plan.md`, `executor.md == execute.md`
   - gated_pipeline: `planner.md == draft.md`, `gate.md == review.md`, `executor.md == execute.md`
   - autonomous_cluster: `orchestrator.md == orchestrate.md`, `cluster.md == cluster_exec.md`, `auditor.md == audit.md`
   - consensus: `planner.md == propose.md`, `consensus.md == vote.md`, `executor.md == execute.md`

## Regression Guard
- Enforced by `tests/test_pattern_souls_hardening.py`.
