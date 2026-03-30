# Progress

> 本文档回答：项目现在长什么样？
>
> 只记录事实状态，不写未来意图。未来意图归 `docs/plan/backlog.md`。

## 更新时间

- 日期：2026-03-30
- 维护人：Agent

## 项目阶段

- 当前阶段：研究原型 / 实验完成
- 当前里程碑：已完成 7 个历史制度 + 1 个 bare baseline 的完整基准评测（MiniMax-M2.5，21 个任务），结果已发布于 README

## 已完成功能

- [x] 声明式 spec 编译器（支持 YAML / JSON / CUE 输入）
- [x] GovernanceRuntime：支持 4 种 Pattern（pipeline / gated_pipeline / autonomous_cluster / consensus）
- [x] Feature 系统：Monitor、递归 Executor、Emergency Handler 等可叠加特性
- [x] 3 个 Adapter：mock、pc-agent-loop、openclaw
- [x] 9 个制度建模（Mongol Empire / Edo Bakuhan / Tang Sanshengliubu / Soviet Party State / Qinhan Junxian / Athens Democracy / US Federal / Bare Pipeline / Egypt Pipeline（测试用））
- [x] Pattern Soul 模板系统（4 种 pattern 对应的 soul prompt）
- [x] CLI 工具：validate / run / serve / init-spec / bench-pinch / bench-mab
- [x] Web Dashboard：拓扑可视化、实时事件流、任务提交
- [x] 基准评测框架集成：PinchBench、MultiAgentBench、ClaweBench
- [x] 拓扑可视化图生成
- [x] 完整 22 任务评测跑分（MiniMax-M2.5）
- [x] pytest 测试套件

## 已知问题

- `tests/test_token_tracking.py` 因缺少文件（`FileNotFoundError`）在 pytest 收集阶段报错，无法正常运行
- 仅在单一模型（MiniMax-M2.5）上完成了完整评测，其他模型的评测结果尚未系统收录

## 技术债

- 无 CI/CD 配置（无 `.github/workflows/`）
- 无静态检查工具（linter / type checker）
- 无 `.env.example` 文件记录所需环境变量
- commit message 无统一格式约束
