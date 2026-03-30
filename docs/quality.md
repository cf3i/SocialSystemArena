# Quality

> 本文档回答：什么叫做完？怎么验证做完了？

## Definition of Done

### 代码质量

- [ ] 功能实现与 `docs/plan/current.md` 一致
- [ ] 无明显重复逻辑和死代码
- [ ] 涉及架构/安全/决策边界的变更已同步更新对应文档

### Issue 回归质量

- [ ] 当前 issue 对应的 `issue_test/<issue_id>.sh` 已存在并覆盖目标行为
- [ ] 实现前已运行历史回归基线：`bash scripts/run_issue_tests.sh --exclude issue_test/<issue_id>.sh`
- [ ] 提交前已运行完整回归：`bash scripts/run_issue_tests.sh`
- [ ] 若修改了历史 `issue_test/*.sh`，已记录原因与影响范围

### 文档同步

- [ ] 变更已同步到相关文档
- [ ] 重要决策已写入 `docs/decisions.md`
- [ ] `docs/progress.md` 已反映当前状态
- [ ] 已记录交付状态：归档中已有 PR URL，且 Stage 6 已完成 merge / auto-merge，或已补充"本地交付 / merge handoff"信息

### 安全

- [ ] 未泄漏敏感信息
- [ ] 认证/鉴权相关改动经过复核（如适用）
- [ ] 若存在 PR，变更风险已在 PR 描述中注明

## issue_test 机制（固定）

- 目录：`issue_test/`
- 命名：`issue_test/<issue_id>.sh`
- 执行入口：`bash scripts/run_issue_tests.sh`
- 历史脚本策略：默认长期保留，后续 issue 必须全部通过

## 项目原生检查

- 单元/集成测试框架：pytest（`tests/` 目录）
- 静态检查工具：当前未配置
- 其他交付前命令：当前未配置

## 常用验证命令

```bash
# 运行全部 issue 回归
bash scripts/run_issue_tests.sh

# 实现当前 issue 前，先跑历史回归基线
bash scripts/run_issue_tests.sh --exclude issue_test/<issue_id>.sh

# 项目原生检查（如有）
python -m pytest tests/ -q
```

## 失败处理流程

1. 先修复 deterministic 的 issue 回归失败，再处理 flaky 场景。
2. 禁止通过删除、跳过或弱化历史 `issue_test/*.sh` 来"修复"失败。
3. 若需临时跳过，必须记录原因和恢复计划。

## 维护规则

1. 新的质量门槛必须先写入本文件，再纳入 CI。
2. 本文件是提交前强制自查列表，不应弱化。
3. 每个 issue 都必须新增或绑定一个可复现的 `issue_test/<issue_id>.sh`。
