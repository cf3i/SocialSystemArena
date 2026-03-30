# AGENTS.md

## 启动协议

每次启动，进入以下循环，不得跳过，不得改变顺序：

> 前提：`docs/stage.lock` 必须已存在。它是初始化阶段生成的 bootstrap 文件；若缺失，说明仓库尚未初始化完成或文件已损坏，必须先由人类重新运行 `init.sh` 或手动恢复。

**Step 1：确认当前 Stage**

读取 `docs/stage.lock`，获取 `current` 字段。

**Step 2：调用 build_context.py**

> 前置条件：`build_context.py` 依赖 PyYAML。若尚未安装，先执行：
> ```bash
> python3 -m pip install pyyaml
> ```

```bash
python scripts/build_context.py --stage <current>
```

脚本成功时 exit 0，输出为当前 Stage 需要加载的文件列表，逐一读取所有文件。
脚本 exit 1 时表示必须文件缺失，不得继续执行，须写入 `docs/blockers.md` 后停止。

**Step 3：执行**

读取完所有文件后，按 `docs/workflow/<current>.md` 的指令执行。

**Step 4：判断是否继续**

每个 Stage 执行后，重新读取 `docs/stage.lock`：

- 若 `status == failed` → **停止**，等待人类处理 blocker
- 若 `current == stage1` 且 `status == done` 且 `previous == stage6` → **成功停止**
  - 这表示本次 run 已完成一个 issue 闭环
  - 不得在同一次 run 中继续领取 backlog 的下一个任务
- 其他情况 → 回到 Step 1，继续下一个 Stage

---

## 文档索引

| 文档 | 职责 |
|------|------|
| `docs/workflow/stage1.md` | Stage 1 指令：Context Loading / Router |
| `docs/workflow/stage2.md` | Stage 2 指令：Task Planning |
| `docs/workflow/stage3.md` | Stage 3 指令：Implementation |
| `docs/workflow/stage4.md` | Stage 4 指令：Delivery & Verification |
| `docs/workflow/stage5.md` | Stage 5 指令：Reflection |
| `docs/workflow/stage6.md` | Stage 6 指令：Entropy Check |
| `docs/stage.lock` | 全局状态寄存器：当前 Stage + 状态 + meta |
| `docs/overview.md` | 项目目标与范围 |
| `docs/architecture.md` | 模块划分 + 依赖边界 |
| `docs/conventions.md` | 命名 + 代码风格 + git 规范 |
| `docs/decisions.md` | 时间线追加式设计决策日志 |
| `docs/quality.md` | Definition of Done + 验证方法 |
| `docs/security.md` | 敏感信息 + 安全边界 |
| `docs/progress.md` | 项目快照 |
| `docs/blockers.md` | Agent 阻塞记录（人类介入点） |
| `docs/wisdom.md` | 跨 issue 验证有效的可复用模式 |
| `docs/antipatterns.md` | 跨 issue 验证会失败的反模式 |
| `docs/plan/backlog.md` | issue 队列 |
| `docs/plan/current.md` | 当前 issue 执行步骤 |
| `issue_test/README.md` | issue 级回归脚本约定 |
| `scripts/run_issue_tests.sh` | 执行 `issue_test/*.sh` 的累积回归入口 |

---

## 全局硬规则

1. 启动协议三步必须执行，不得跳过。
2. Stage 判断不明确时，以 `stage.lock` 为准，不得自行猜测。
3. 每个 Stage 结束前必须完成该 Stage 的 Exit Checklist，不得跳过。
4. `stage.lock` 每次更新必须单独 git commit，不得与业务代码混提。格式：`chore(stage): <from> → <to> [<reason>]`，例：`chore(stage): stage2 → stage3 [done]`、`chore(stage): stage3 [failed]`。
5. 架构边界违规必须先修复。若 `docs/architecture.md` 中标注"由静态检查或 CI 强制执行"，则以对应工具输出为准；若尚未配置自动检查，则依赖 agent 自觉遵守，并在 `docs/decisions.md` 记录该约束仍为手动执行状态。
6. 涉及凭据、认证、敏感文件前先读 `docs/security.md`。
7. 重要技术取舍必须追加到 `docs/decisions.md`（禁止覆写历史条目）。
8. 进入 Stage 3 前，必须存在当前 issue 对应的 `issue_test/<meta.issue_id>.sh`；后续 issue 不得删除、跳过或弱化历史 issue tests 来规避回归。
9. 单次 run 只允许完成一个 issue 闭环；若检测到 `current: stage1`、`status: done`、`previous: stage6`，必须停止，不得在同一次 run 中继续领取新 issue。
10. 遇到无法自行解决的问题，写入 `docs/blockers.md` 后停止，不得绕过阻塞继续执行。
11. Stage 4 负责创建或更新 PR，不负责最终 merge；Stage 6 才负责最终 merge / auto-merge。若 Stage 4 或 Stage 6 的远端交付受网络、权限或宿主环境限制阻塞，可以退化为“本地交付 / merge handoff”，但必须把本地 commit hash、失败命令和下一步人工动作写进归档记录。
