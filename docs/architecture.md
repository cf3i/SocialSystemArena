# Architecture

> 本文档回答：什么东西在哪里？什么能依赖什么？
>
> 收录标准：本文档只收录**被 linter / CI 机械执行**的结构性约束。靠 agent 自觉遵守的风格性规则归 `conventions.md`。

## 分层模型

当前项目未采用经典四层分层架构，而是按**功能模块**组织：

| 模块 | 职责 | 允许依赖 | 禁止依赖 |
| --- | --- | --- | --- |
| `mas_engine/spec/` | Spec 编译与校验（YAML/JSON/CUE → IR） | `mas_engine/core/types` | 运行时、adapter |
| `mas_engine/core/` | 治理运行时（GovernanceRuntime）、类型定义、Feature 处理 | `mas_engine/spec/` | adapter 具体实现 |
| `mas_engine/adapters/` | LLM/Agent 框架桥接（mock / pc-agent-loop / openclaw） | `mas_engine/core/` | spec 编译 |
| `mas_engine/benchmark/` | 基准评测（PinchBench / ClaweBench / MultiAgentBench） | `mas_engine/core/`, `mas_engine/adapters/` | — |
| `mas_engine/cli.py` | CLI 入口 | 所有 mas_engine 子模块 | — |
| `mas_engine/dashboard_server.py` | Web Dashboard | `mas_engine/core/`, `mas_engine/observability/` | — |
| `systems/` | 制度 spec 定义、pattern soul 模板 | 纯数据/配置，无代码依赖 | — |
| `dsl/` | CUE schema 定义 | 纯 schema | — |
| `third_party/` | 外部子模块（pc-agent-loop / pinchbench / multiagentbench / claw-eval） | 独立子模块 | 不被 mas_engine 直接 import，通过 adapter 或 subprocess 调用 |

## 目录结构

```
SocialSystemArena/
├── mas_engine/             # 核心 Python 包
│   ├── core/               # 运行时、类型、Feature 处理
│   │   ├── runtime.py
│   │   ├── types.py
│   │   ├── features.py
│   │   └── errors.py
│   ├── spec/               # Spec 编译器与校验器
│   │   ├── compiler.py
│   │   ├── validators.py
│   │   └── templates.py
│   ├── adapters/           # LLM/Agent 桥接层
│   │   ├── mock.py
│   │   ├── pc_agent_loop.py
│   │   └── openclaw.py
│   ├── benchmark/          # 基准评测框架
│   │   ├── pinchbench.py
│   │   └── clawebench.py
│   ├── observability/      # 事件流与 trace
│   ├── storage/            # 持久化
│   ├── web/                # Dashboard 静态资源
│   ├── cli.py              # CLI 入口
│   └── dashboard_server.py # Dashboard HTTP 服务
├── systems/
│   ├── institutions/       # 各制度的 spec（JSON/YAML）
│   ├── institutions.yaml   # 制度注册表
│   └── pattern_souls/      # Pattern 级 soul 模板
├── dsl/                    # CUE schema
├── tests/                  # pytest 测试
├── third_party/            # git submodule
├── traces/                 # 评测 trace 输出
├── figures/                # 拓扑可视化图
├── scripts/                # 辅助脚本
└── pyproject.toml          # 包定义（setuptools）
```

## Import Boundary 规则

当前未配置静态 import boundary 检查工具。以下为代码中事实上遵循的依赖方向：

1. `mas_engine/spec/` 不 import `mas_engine/core/runtime` 或 `mas_engine/adapters/`。
2. `mas_engine/adapters/` 通过 `mas_engine/adapters/base.py` 定义 `typing.Protocol` 接口，具体 adapter 实现该协议。
3. `third_party/` 子模块不被 `mas_engine` 直接 import，而是通过 subprocess 或 adapter 包装调用。

## 执行方式

- 静态检查工具：当前未配置（无 linter / import boundary 自动检查）
- 规则文件位置：当前未配置
- CI 校验命令：当前未配置（无 `.github/workflows/`）

## 维护规则

1. 修改边界前先记录决策到 `docs/decisions.md`。
2. 边界变化必须同步更新 lint 规则。（待 lint 工具引入后生效，当前依赖 agent 自觉遵守）
3. lint 规则未更新前，不算架构更新完成。（待 lint 工具引入后生效，当前依赖 agent 自觉遵守）
