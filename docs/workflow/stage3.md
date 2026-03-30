# Stage 3 — Implementation

> 回答：代码写完了吗？能通过验证吗？

## 执行步骤

### Step 1：先跑历史 issue 回归基线

```bash
bash scripts/run_issue_tests.sh --exclude issue_test/<meta.issue_id>.sh
```

- FAIL → 先修复已有回归，再继续当前 issue
- 同一错误修复超过 3 次未解决 → 进入 **Failure Path A**

### Step 2：运行当前 issue 的测试脚本，确认基线

```bash
bash issue_test/<meta.issue_id>.sh
```

- 如果当前 issue 代表新增/修复行为，理想结果通常是“尚未通过”或明确暴露缺失行为
- 如果当前 issue 是重构、清理或非行为变更，允许脚本在实现前就通过，但必须能说明它在保护什么不变式
- 如果脚本失败但没有提供足够诊断信息，先补足测试脚本输出，再继续
- 若脚本结果与 issue 目标明显不符（例如应失败却通过，且看不出是在验证目标行为）→ 先修正测试脚本，再继续
- 无法判断脚本是否有效 → 进入 **Failure Path B**

### Step 3：实现代码

按 `docs/plan/current.md` 的步骤逐一实现，每完成一步立即勾选（`- [x]`）。

涉及敏感内容（认证、密钥、权限）时，先读 `docs/security.md`。

实现过程中如发现架构边界需要调整（新增模块、依赖关系变化、层级职责变化）：

1. 立即更新 `docs/architecture.md`，不要等到 Stage 6
2. 追加一条决策到 `docs/decisions.md`，说明为什么需要这个架构调整
3. 如果调整涉及 lint 规则，同步更新对应规则文件

### Step 4：运行完整 issue 回归套件

```bash
bash scripts/run_issue_tests.sh
```

- FAIL → 修复并重跑，直到全部通过
- 同一错误修复超过 3 次未解决 → 进入 **Failure Path A**

### Step 5：更新 stage.lock

```yaml
current: stage4
status: in_progress
previous: stage3
```

## Exit Checklist

- [ ] `docs/plan/current.md` 所有步骤已勾选
- [ ] `bash scripts/run_issue_tests.sh --exclude issue_test/<meta.issue_id>.sh` 已通过
- [ ] `issue_test/<meta.issue_id>.sh` 已在实现前执行过，结果与 issue 目标一致，且失败时输出了足够诊断信息
- [ ] 架构边界有变化时，`docs/architecture.md` 已更新并追加 decisions.md
- [ ] `bash scripts/run_issue_tests.sh` 输出 `ISSUE TESTS: PASS`
- [ ] `stage.lock` 已更新（current: stage4）
- [ ] `stage.lock` 更新已单独 git commit（格式：`chore(stage): stage3 → stage4 [done]`）

## Failure Path

### Failure Path A：同一错误修复超过 3 次

- 写入 `docs/blockers.md`，明确记录：
  - 已尝试的修复思路
  - 最近一次失败命令与报错摘要
  - 需要人类确认的问题
- 更新 stage.lock（status: failed），停止，通知人类

### Failure Path B：当前 issue test 有效性无法判断

写入 `docs/blockers.md`，更新 stage.lock（status: failed），停止，通知人类确认。
