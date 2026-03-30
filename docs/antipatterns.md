# Antipatterns

> 被历史 issue 验证会导致失败的做法。
>
> 记录"这类做法为什么会失败"，而不是"卡在哪里"（那是 blockers.md 的职责）。

## 维护规则

1. 只在 Stage 5（Reflection）写入，禁止在其他 Stage 追加
2. 每条必须有来源 blocker 编号或 issue_id，不写假设性警告
3. 失败信号（早期症状）为必填——让 Agent 在走向失败之前就能识别
4. 正确替代做法为必填——不只是"不要做 X"，要给出具体替代方案
5. 只追加，不修改历史条目

## 记录模板

```markdown
## A-00X 标题

- 来源：<B-00X blocker> / <issue_id>
- 失败信号（早期症状）：
- 根本原因：
- 正确替代做法：
```

## 反模式记录

（暂无，由 Stage 5 Reflection 逐步积累）
