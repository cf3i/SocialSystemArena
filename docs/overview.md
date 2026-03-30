# Overview

> 本文档回答：这个项目是什么？什么不做？

## 项目摘要

- 项目名称：SocialSystemArena（王朝大乱斗）
- 一句话目标：将历史政治制度建模为 AI 治理规范（声明式 spec），在统一的多智能体运行时中用真实任务对它们进行基准评测。
- 目标用户：多智能体系统研究者、AI 治理架构设计者
- 业务价值：量化比较不同消息流拓扑（pipeline / gated_pipeline / autonomous_cluster / consensus）对 agent 任务完成率的影响，为 MAS 架构选型提供实证依据。

## 范围定义

### In Scope

- 声明式 spec 编译器（YAML / JSON / CUE → 内部 IR）
- 通用治理运行时（GovernanceRuntime）：驱动多 agent 按 spec 定义的 stages / transitions / features 执行
- 多 adapter 接入：mock、pc-agent-loop、OpenClaw
- 基准评测框架：PinchBench、ClaweBench、MultiAgentBench
- 拓扑可视化 Dashboard（Web UI）
- Pattern Soul 模板系统（pipeline / gated_pipeline / autonomous_cluster / consensus）

### Out of Scope

- 自研 LLM 推理服务——依赖外部模型 API
- 生产级用户身份认证与权限管理
- 前端 SPA 应用——Dashboard 仅为开发/研究用途的轻量 Web 服务

## 核心概念

| 概念 | 定义 | 备注 |
| --- | --- | --- |
| Pattern | 消息流拓扑类型（pipeline / gated_pipeline / autonomous_cluster / consensus） | 决定 agent 间的协作方式 |
| Feature | 可叠加的系统级特性（Monitor、递归 Executor、Emergency Handler 等） | 正交于 Pattern，声明式开关 |
| Spec | 声明式治理规范（YAML / JSON / CUE），定义 stages、transitions、pattern、features | 每个"制度"对应一个 spec |
| Stage | spec 中的执行节点，绑定一个或多个 agent 角色 | |
| Transition | stage 间的转移规则，由 decision 触发 | |
| Soul | Pattern 级别的系统提示词模板，指导 agent 行为风格 | 存放于 `systems/pattern_souls/` |
| Adapter | 将运行时事件翻译为具体 LLM / agent 框架调用的桥接层 | mock / pc-agent-loop / openclaw |
| Institution | 一个完整的历史制度建模实例（spec + soul + 配置） | 存放于 `systems/institutions/` |

## 成功标准

当前研究阶段不设定量化指标。

## 维护规则

1. 仅在项目目标或范围发生变化时更新。
2. 范围变更需同步记录决策到 `docs/decisions.md`。
