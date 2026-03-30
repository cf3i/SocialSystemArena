# Stage 5 — Reflection

> 回答：这次学到了什么？有什么可以沉淀为规则？

## 执行步骤

### Step 1：写 REFLECT 文件（硬约束，不可跳过）

创建 `docs/plan/archive/REFLECT-<meta.issue_id>.md`，必须包含以下三个必答项：

```markdown
# REFLECT-<issue-id>

## 1. 本次遇到的问题
<!-- 明确写出，可以是"无"，但不能留空 -->

## 2. 是否有新 wisdom 条目
<!-- 给出结论（是/否）和原因 -->
<!-- 如果是：描述模式，将在 Step 2 写入 wisdom.md -->

## 3. 是否有新 antipattern 条目
<!-- 给出结论（是/否）和原因 -->
<!-- 如果是：描述失败模式，将在 Step 3 写入 antipatterns.md -->
```

### Step 2：更新 wisdom.md（如有）

如果 Step 1 中判断有新的可复用成功模式，追加到 `docs/wisdom.md`：

- 必须有来源 issue_id
- 必须有适用场景
- 必须有反例（不适用时）

### Step 3：更新 antipatterns.md（如有）

如果 Step 1 中判断有新的失败模式，追加到 `docs/antipatterns.md`：

- 必须有来源 blocker 或 issue_id
- 必须有失败信号（早期症状）
- 必须有正确替代做法

### Step 4：更新其他文档（如有变化）

- 重要设计决策 → 追加到 `docs/decisions.md`
- 架构边界变化 → 更新 `docs/architecture.md`
- 规范变化 → 更新 `docs/conventions.md`

### Step 5：更新 stage.lock

```yaml
current: stage6
status: in_progress
previous: stage5
```

## Exit Checklist

- [ ] `docs/plan/archive/REFLECT-<meta.issue_id>.md` 已创建（必须存在）
- [ ] REFLECT 文件包含三个必答项，无空白项
- [ ] `docs/wisdom.md` 已处理（追加或明确写"无"在 REFLECT 中）
- [ ] `docs/antipatterns.md` 已处理（追加或明确写"无"在 REFLECT 中）
- [ ] `stage.lock` 已更新（current: stage6）
- [ ] `stage.lock` 更新已单独 git commit（格式：`chore(stage): stage5 → stage6 [done]`）

## Failure Path

- REFLECT 文件不存在或缺少必答项 → 不得进入 Stage 6，补全后重新检查
- 更新 stage.lock（status: failed），停止，通知人类
