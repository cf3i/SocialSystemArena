# Archive

已完成 issue 的 plan 存档。纯历史记录。

## 命名规范

- `001-feature-name.md`
- `002-fix-xxx.md`

## 归档流程

1. 复制 `docs/plan/current.md` 内容到新归档文件。
2. 在归档文件中补充以下内容：
   - PR 链接
   - 若 Stage 6 无法完成最终 merge：补充“merge handoff”说明（失败命令、报错摘要、人工下一步）
   - 若 Stage 4 就已退化为本地交付：补充“本地交付 + 人工 handoff”说明
   - 最终结论
   - 对应测试脚本路径（`issue_test/<issue_id>.sh`）
   - 本地交付 commit hash
3. 清空并重置 `docs/plan/current.md`。
4. 不要移动或删除 `issue_test/<issue_id>.sh`；历史 issue test 必须继续保留用于后续回归。
