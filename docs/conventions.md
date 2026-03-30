# Conventions

> 本文档回答：代码长什么样？git 操作怎么做？
>
> 收录标准：本文档只收录**靠 agent 自觉遵守**的风格性约束。被 linter / CI 机械执行的结构性规则归 `architecture.md`。

## 命名规范

- 文件名：`snake_case`（Python 模块）
- 类名：`PascalCase`
- 变量和函数：`snake_case`（Python 标准风格）
- 常量：`UPPER_SNAKE_CASE`
- 制度 spec 目录 / 文件：`snake_case`（如 `tang_sanshengliubu/tang_sanshengliubu.json`）

## 函数契约

1. 函数输入输出必须可预测，错误路径可测试。
2. 公共函数需声明参数、返回值、异常语义。
3. 禁止隐式全局状态修改。

## 错误处理模式

- 错误表示方式：Python 异常（`mas_engine/core/errors.py` 中定义自定义异常类）
- 日志级别约定：当前未有统一约定
- 重试策略：当前未有统一约定；部分 pattern（如 Tang 的回环重试）在 spec 层面定义

## Git 规范

### Commit Message

- 格式：当前无严格格式约束，历史 commit 使用自然语言短句（如 `Upload traces`、`Optimize structure and soul`）
- subject 语言：英文

### Branch 命名

- 当前只有 `main` 分支，无多分支开发历史
- 建议格式：`issue/<issue_id>`

### PR 规范

- 当前未配置 PR 模板或 CI 检查
- 建议描述必填项：背景、方案、测试、风险

## 维护规则

1. 风格冲突时，以本文件为准。
2. 引入新模式前先补充本文件再推广。
3. 当某条规则被 linter 强制执行后，从本文件迁移到 `architecture.md`。
