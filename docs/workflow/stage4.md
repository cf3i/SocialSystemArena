# Stage 4 — Delivery & Verification

> 回答：能交付了吗？

## 执行步骤

### Step 1：最终 issue 回归 Gate

```bash
bash scripts/run_issue_tests.sh
```

- 输出 `ISSUE TESTS: PASS` → 继续
- 输出 `ISSUE TESTS: FAIL` → 回到 **Stage 3** 修复（更新 stage.lock: current: stage3）

### Step 2：人工自查

对照 `docs/quality.md` 中无法脚本化的条目逐一自查，全部通过才继续。

### Step 3：本地交付提交

```bash
git add <相关文件>
git commit   # message 格式见 docs/conventions.md
```

- 若当前 issue 的业务改动已经在本地提交完成，不要制造空提交
- 本步骤的目标是确保存在一个可 handoff 的本地 commit

### Step 4：创建或更新 PR（本阶段不 merge）

优先执行：

```bash
bash scripts/deliver_pr.sh ensure --base <base-branch>
```

- 该脚本会先推送当前分支，再创建或复用对应 PR
- 若需要自定义标题或正文，可额外传 `--title`、`--body-file`
- PR 已存在或新建成功 → 在归档记录中写入 PR URL，并标记“Stage 6 将尝试最终 merge”，继续
- 若因为网络、DNS、权限、宿主沙箱限制或 `gh` 不可用导致失败，最多重试 3 次，然后转为 **本地交付 + 人工 handoff**
- 本地交付 + 人工 handoff 不是失败：只要本地 commit 已存在且验证通过，就继续后续步骤
- handoff 记录必须包含：
  - 本地 commit hash
  - 失败命令与报错摘要
  - 人类下一步要做什么（例如 push、开 PR、补凭据）

### Step 5：更新 progress.md

在 `docs/progress.md` 中记录本次完成的功能/修复。

### Step 6：归档 current.md

```bash
# 将 current.md 内容复制到 archive
cp docs/plan/current.md docs/plan/archive/<meta.issue_id>.md
```

- 归档内容中必须保留当前 issue 对应的测试脚本路径：`issue_test/<meta.issue_id>.sh`
- 归档内容中必须补充交付状态：
  - 已创建或复用 PR：写明 PR URL，并写明“Stage 6 将尝试最终 merge”
  - 本地交付 + 人工 handoff：写明本地 commit hash、失败原因和人工下一步
- 不要移动或删除 `issue_test/<meta.issue_id>.sh`；它必须留在 `issue_test/` 里参与后续回归

### Step 7：清理

- 清空 `docs/plan/current.md`
- 重置内容必须严格回到以下模板，不得自行省略或重复段落：

```markdown
# Current Plan

## 当前状态

- 当前无进行中的 issue。
- 开始新任务时，再由 agent 或人类将本文件改写为具体任务计划，并先创建 `issue_test/<issue_id>.sh`。

## 启动新任务时需要补充

1. 任务名称、来源 issue、开始日期、状态
2. 当前 issue 对应的测试脚本路径与覆盖目标
3. 可逐步勾选的执行步骤
4. 对应的验证记录（至少包含历史回归基线和完整回归结果）

## 维护说明

- 该文件只记录当前正在执行的一个 issue。
- 对应测试脚本固定放在 `issue_test/<issue_id>.sh`，完成任务后继续保留在 `issue_test/` 中。
- 任务完成后，将本文件归档到 `docs/plan/archive/`，然后重置为“当前无进行中的 issue”状态。
```

- 在 `docs/plan/backlog.md` 中将对应条目标记为 `[x]`

### Step 8：更新 stage.lock

```yaml
current: stage5
status: in_progress
previous: stage4
```

## Exit Checklist

- [ ] `bash scripts/run_issue_tests.sh` 输出 `ISSUE TESTS: PASS`
- [ ] `docs/quality.md` 人工自查条目全部通过
- [ ] 已存在可交付的本地 commit
- [ ] 已完成以下两者之一：
  - PR 已创建或复用，且归档中已记录 PR URL 与“Stage 6 将尝试最终 merge”
  - 归档中已记录“本地交付 + 人工 handoff”的 commit hash、失败原因和下一步
- [ ] `docs/progress.md` 已更新
- [ ] `docs/plan/archive/<meta.issue_id>.md` 已创建
- [ ] `issue_test/<meta.issue_id>.sh` 仍保留在 `issue_test/` 中
- [ ] `docs/plan/current.md` 已清空
- [ ] `docs/plan/backlog.md` 对应条目已标记 `[x]`
- [ ] `stage.lock` 已更新（current: stage5）
- [ ] `stage.lock` 更新已单独 git commit（格式：`chore(stage): stage4 → stage5 [done]`）

## Failure Path

- `scripts/run_issue_tests.sh` FAIL → 更新 stage.lock（current: stage3, status: in_progress），回到 Stage 3
- 无法形成可复现的本地交付提交 → 写入 `docs/blockers.md`，更新 stage.lock（status: failed），停止，通知人类
- 无法判断 PR 创建失败是否已经完整转写为 handoff 信息 → 写入 `docs/blockers.md`，更新 stage.lock（status: failed），停止，通知人类
