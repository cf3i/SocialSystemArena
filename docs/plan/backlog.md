# Backlog

> 所有待做的 issue，按优先级排序。使用 `- [ ]` / `- [x]` 维护状态。

## 条目编写规范

每个 backlog 条目都应至少回答 4 个问题：

1. 要交付什么结果？
2. 影响范围在哪里？
3. 做完后怎么验收？
4. 这个任务为什么存在？

对应到固定字段就是：

- 目标：这次要完成什么
- 范围：改哪里、影响哪里
- 验收：什么结果算 done，最好能映射到 `issue_test/<issue_id>.sh`
- 来源：这个任务来自哪里，例如 bug、用户反馈、代码注释、产品需求、文档缺口

## 推荐模板

### 最小版

适合大多数日常任务。保持一行，方便快速维护。

```md
- [ ] <任务标题>（目标：...；范围：...；验收：...；来源：...）
```

示例：

```md
- [ ] 为 init.sh 增加 dry-run 预览（目标：初始化前先看到将覆盖哪些模板文件；范围：init.sh 输出层；验收：执行 `init.sh --skip-fill --non-interactive` 时可先看到待写入文件清单；来源：初始化前风险确认需求）
```

### 展开版

适合跨模块、依赖较多、或验收条件不止一条的任务。

```md
- [ ] <任务标题>
  - 目标：...
  - 范围：...
  - 验收：...
  - 来源：...
  - 非目标：（可选）
  - 风险/依赖：（可选）
```

## 编写规则

1. 标题写"结果"，不要写"过程"。
2. backlog 只定义"做什么"，不展开"怎么做"；具体执行步骤写到 `docs/plan/current.md`。
3. 一个条目应尽量对应一个可闭环的 issue；过大的任务先拆分。
4. "验收"必须可判断，最好能转成 issue test，而不是"看起来差不多"。
5. 信息不完整时，至少把"目标 + 范围 + 来源"写清，避免 Stage 2 无法选任务。
6. 如果任务超出 `docs/overview.md` 当前范围，应先更新范围定义，再继续执行。

## 优先级定义

- `P0`：阻塞核心功能、线上可用性或关键交付
- `P1`：重要功能、体验改进、关键效率提升
- `P2`：技术债、文档、清理、低风险优化

## 维护说明

- 人类和 agent 都可以补充 backlog。
- Stage 2 会从这里选择一个 `- [ ]` 条目，生成 `issue_id`、`issue_test/<issue_id>.sh` 和 `docs/plan/current.md`。
- Stage 4 完成交付后，会把对应条目标记为 `- [x]`。

## P0（最高优先级）

（当前无 P0 条目）

## P1

- [ ] 添加 CI 配置（目标：在 GitHub Actions 中自动运行 pytest；范围：`.github/workflows/`；验收：push 后 CI 绿色通过；来源：`docs/progress.md` 技术债）
- [ ] 添加 `.env.example` 文件（目标：记录项目所需的环境变量及说明；范围：根目录 `.env.example`；验收：新用户按文件配置后可正常运行 adapter；来源：`docs/progress.md` 技术债）

## P2

- [ ] 引入静态检查工具（目标：配置 ruff 或 flake8 + mypy；范围：`pyproject.toml`、CI；验收：`ruff check .` 或等效命令通过；来源：`docs/progress.md` 技术债）
- [ ] 统一 commit message 格式（目标：采用 conventional commits 或类似规范；范围：git hooks 或 CI；验收：不符合格式的 commit 被拒绝或告警；来源：`docs/conventions.md`）
