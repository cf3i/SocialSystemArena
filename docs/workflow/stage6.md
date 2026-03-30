# Stage 6 — Entropy Check

> 回答：文档和代码还同步吗？

## 执行步骤

### Step 1：对比文档与代码

逐一检查 `docs/` 下的文档与代码实现，找出所有偏差：

- 文档描述的行为与代码实际行为不符
- 文档中的目录结构、模块划分与代码不符
- `docs/progress.md` 的已完成功能与代码不符

### Step 2：处理偏差

**路径 A（只改文档）：** 偏差是文档落后于代码 → 更新文档以匹配代码

**路径 B（需改代码）：** 代码与文档记录的意图矛盾 → 修代码并补测试，同时在 stage.lock 标记：

```yaml
meta:
  code_changed: true
```

### Step 3：decisions.md compaction（按需执行）

检查 `docs/decisions.md`：

- Superseded 条目超过总条目的 30% → 执行 compaction
- 将所有 Accepted 条目提炼为一句话摘要，更新到"当前有效决策摘要"区域
- 历史记录区域保持不变（只追加，不修改）

### Step 4：更新 stage.lock

**路径 A（只改文档）：**

```yaml
current: stage1
status: done
previous: stage6
meta:
  issue_id: null
  code_changed: null
```

- 写回上述状态后，进入 Step 5 做最终远端交付
- 先单独 git commit：`chore(stage): stage6 → stage1 [done]`
- 不要在同一次 run 中继续领取 backlog 的下一个任务；下一次启动再从 Stage 1 开始新的 issue

**路径 B（改了代码）：**

```yaml
current: stage3
status: in_progress
previous: stage6
meta:
  code_changed: null
  # issue_id 保留，走完整 S3 → S4 → S5 闭环
```

- 单独 git commit：`chore(stage): stage6 → stage3 [code-changed]`

### Step 5：最终远端交付（仅路径 A）

优先执行：

```bash
git push
bash scripts/deliver_pr.sh merge --merge-method squash
```

- `ACTION=MERGED` → PR 已完成最终 merge，本次 run 成功结束
- `ACTION=AUTO_MERGE_ENABLED` → 已开启 auto-merge，本次 run 成功结束
- 若因网络、DNS、权限、宿主沙箱限制、`gh` 不可用或仓库设置阻塞，最多重试 3 次，然后在 `docs/plan/archive/<issue_id>.md` 追加 merge handoff：
  - 已有 PR URL（若存在）
  - 当前最终本地 commit hash
  - 失败命令与报错摘要
  - 人类下一步动作（例如补权限、补凭据、重试 `bash scripts/deliver_pr.sh merge --merge-method squash`）
- 追加 handoff 后，如有新文档修改，必须新增一个普通 commit；**不要 amend 或混入 Stage 6 的 stage.lock commit**
- merge handoff 不是失败：只要最终状态和人工下一步已经写清，本次 run 也可结束

## Exit Checklist

- [ ] 文档与代码已对齐，无已知偏差
- [ ] `docs/decisions.md` 已处理（compaction 或确认不需要）
- [ ] `stage.lock` 已按路径 A 或路径 B 正确更新
- [ ] 若走路径 A：已回到 `stage1/done`，并将其视为本次 run 的成功终点
- [ ] `stage.lock` 更新已单独 git commit
  - 路径 A 格式：`chore(stage): stage6 → stage1 [done]`
  - 路径 B 格式：`chore(stage): stage6 → stage3 [code-changed]`
- [ ] 若走路径 A，已满足以下三者之一：
  - PR 已直接 merge
  - PR 已启用 auto-merge
  - `docs/plan/archive/<issue_id>.md` 已追加 merge handoff，且失败原因与人工下一步明确
- [ ] 若走路径 B：本次 run 未尝试 merge，准备回到 Stage 3 继续闭环

## Failure Path

- 发现文档和代码的矛盾无法判断谁对 → 写入 `docs/blockers.md`，更新 stage.lock（status: failed），停止，通知人类
- 路径 A 中无法判断 merge 失败是否已完整转写为 handoff → 写入 `docs/blockers.md`，更新 stage.lock（status: failed），停止，通知人类
