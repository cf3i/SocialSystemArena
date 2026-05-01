# SocialSystemArena

**当智能体进化，制度随之而来**

[![arXiv](https://img.shields.io/badge/arXiv-2604.27691-b31b1b.svg)](https://arxiv.org/abs/2604.27691)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[**论文**](https://arxiv.org/abs/2604.27691) | [**English README**](README.md)

SocialSystemArena 将七个历史治理制度建模为声明式多智能体规范，并在真实任务上进行基准测试。每个制度由一个 **Pattern**（消息流拓扑）和可组合的 **Feature**（系统级能力）定义，编译进统一的治理运行时。最终产出是不同组织结构对 agent 任务完成率影响的实证对比。

---

## 动态

- **2026-04** — 论文发布于 [arXiv](https://arxiv.org/abs/2604.27691)，代码与基准数据开源。

---

## 概述

多智能体系统（MAS）通常采用临时性的协调策略。我们采取了不同的方法：从七个真实的历史制度——从蒙古帝国的扁平指挥链到雅典直接民主——中提取治理结构，将每个制度编码为声明式 spec（YAML / JSON / CUE）。共享的治理运行时在相同条件下执行所有 spec，实现受控对比。

### 四种拓扑 Pattern

| Pattern | 描述 | 代表制度 |
|---|---|---|
| `pipeline` | 单向链路，无阻断节点 | 蒙古帝国、苏联党国体制、秦汉郡县 |
| `gated_pipeline` | 管道中插入门控节点，可拒绝/否决/修改 | 唐三省六部、美国联邦 |
| `autonomous_cluster` | 编排者 + 内部自治闭环子系统 | 江户幕藩体制 |
| `consensus` | 集体投票决策，无单一控制节点 | 雅典直接民主 |

### 核心发现

扁平管道（蒙古帝国，97.8 分）在 agent 任务中大幅领先深层门控架构（美国联邦，64.4 分）。深度不是瓶颈，分叉与门控密度才是。所有七个历史制度均超越裸跑单 agent 基线（55.2 分），证实治理结构具有可量化的实际价值。

---

## 基准结果

> 模型：MiniMax-M2.5（pc-agent-loop adapter）| 21 个任务（排除环境限制的 `task_13`）

| 排名 | 制度 | Pattern | 校正均分 | 得分 >= 90 的任务 | 零分任务 |
|:---:|---|---|:---:|:---:|:---:|
| 1 | 蒙古帝国 | `pipeline` | **97.8** | 20 / 21 | 0 |
| 2 | 江户幕藩 | `autonomous_cluster` | **85.4** | 16 / 21 | 2 |
| 3 | 唐三省六部 | `gated_pipeline` | **82.0** | 16 / 21 | 3 |
| 4 | 苏联党国体制 | `pipeline` | **78.9** | 15 / 21 | 2 |
| 5 | 秦汉郡县 | `pipeline` | **69.4** | 11 / 21 | 2 |
| 6 | 雅典民主 | `consensus` | **68.4** | 13 / 21 | 5 |
| 7 | 美国联邦 | `gated_pipeline` | **64.4** | 12 / 21 | 7 |
| — | *裸管道（基线）* | `pipeline` | **55.1** | 10 / 21 | 8 |

### 制度指纹

均步数 = 每任务平均 agent 调用次数（回环/重试会推高此值）。

| 制度 | Pattern | 门控数 | 分支数 | 回环数 | 深度 | 均步数 | 校正均分 |
|---|---|---:|---:|---:|---:|---:|---:|
| 蒙古帝国 | `pipeline` | 0 | 0 | 0 | 6 | 5.6 | 97.8 |
| 江户幕藩 | `autonomous_cluster` | 0 | 2 | 0 | 3 | 9.0 | 85.4 |
| 唐三省六部 | `gated_pipeline` | 1 | 2 | 3 | 5 | 10.9 | 82.0 |
| 苏联党国体制 | `pipeline` | 0 | 0 | 0 | 5 | 5.0 | 78.9 |
| 秦汉郡县 | `pipeline` | 0 | 1 | 1 | 4 | 8.0 | 69.4 |
| 雅典民主 | `consensus` | 0 | 2 | 0 | 2 | 8.9 | 68.4 |
| 美国联邦 | `gated_pipeline` | 5 | 5 | 0 | 2 | 5.8 | 64.4 |
| *裸管道* | `pipeline` | 0 | 0 | 0 | 1 | 1.0 | 55.1 |

<details>
<summary>完整 22 任务分数矩阵</summary>

`†` = 运行时报错但仍被评分 | task_13 因环境限制（无图像生成 API）已从校正均分排除

| 任务 | 雅典 | 江户 | 蒙古 | 秦汉 | 苏联 | 唐 | 美联邦 | 裸跑 | 均分 |
|:-----|:------:|:---:|:------:|:------:|:------:|:----:|:------:|:----:|----:|
| `task_01` Calendar Event Creation | 100 | 100 | 100 | 100 | 100 | 100 | 83 | 100 | 98 |
| `task_02` Stock Price Research | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 100 | 88 |
| `task_03` Blog Post Writing | 96 | 100 | 96 | 96 | 78 | 95 | 100 | 91 | 94 |
| `task_04` Weather Script Creation | 100 | 100 | 100† | 0 | 14 | 100 | 100 | 100 | 77 |
| `task_05` Document Summarization | 100 | 100 | 100 | 0 | 100 | 100 | 100 | 0 | 75 |
| `task_06` Tech Conference Research | 0 | 100 | 100 | 88 | 98 | 91 | 100 | 96 | 84 |
| `task_07` Professional Email Drafting | 0 | 96 | 100 | 96 | 96 | 0 | 100 | 88 | 72 |
| `task_08` Memory Retrieval from Context | 100 | 100 | 90 | 90 | 90 | 100 | 80 | 0 | 81 |
| `task_09` File Structure Creation | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 100 | 88 |
| `task_10` Multi-step API Workflow | 94 | 92 | 98 | 8 | 100 | 100 | 0 | 36 | 66 |
| `task_11` Create Project Structure | 100 | 100 | 100† | 100 | 100 | 100 | 0 | 100 | 88 |
| `task_12` Search and Replace in Files | 17 | 83 | 100 | 100 | 100 | 100 | 0 | 100 | 75 |
| `task_13` AI Image Generation *(env)* | 0 | 54 | 25† | 0† | 30† | 33 | 0† | 21 | 20 |
| `task_14` Humanize AI-Generated Blog | 0 | 94 | 94 | 85 | 88 | 100 | 100 | 94 | 82 |
| `task_15` Daily Research Summary | 88 | 0 | 100 | 100 | 100 | 0† | 100 | 100 | 74 |
| `task_16` Email Inbox Triage | 91 | 100 | 98 | 75 | 98 | 0† | 98 | 53 | 77 |
| `task_16` Competitive Market Research | 94 | 94 | 94 | 47† | 94 | 84† | 94 | 0 | 75 |
| `task_17` Email Search and Summarization | 0 | 86 | 87 | 9 | 0 | 97 | 97 | 0 | 47 |
| `task_18` CSV/Excel Data Summarization | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 0 | 88 |
| `task_20` ELI5 PDF Summarization | 100 | 0 | 98 | 93† | 100 | 91 | 100 | 0 | 73 |
| `task_21` OpenClaw Report Comprehension | 0 | 100 | 100† | 11† | 0 | 100 | 0 | 0 | 39 |
| `task_22` Second Brain Knowledge Persistence | 57 | 50 | 100 | 60 | 2 | 65 | 0 | 0 | 42 |
| **校正均分**（排除 task_13） | **68.4** | **85.4** | **97.8** | **69.4** | **78.9** | **82.0** | **64.4** | **55.1** | |

</details>

详细失效分析与历史视角解读见 [docs/analysis.md](docs/analysis.md)。

---

## 安装

**环境要求：** Python >= 3.10

```bash
# 克隆仓库（含子模块）
git clone --recursive https://github.com/cf3i/SocialSystemArena.git
cd SocialSystemArena

# 安装
pip install -e .
```

---

## 快速开始

### 校验 spec

```bash
python -m mas_engine.cli validate \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json
```

### 使用 mock adapter 运行任务

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "测试任务" \
  --input "请完成一个复杂任务" \
  --adapter mock \
  --trace-out traces/test.jsonl
```

### 启动 Dashboard

```bash
python -m mas_engine.cli serve \
  --host 127.0.0.1 --port 8787 \
  --trace-dir traces/dashboard \
  --institutions systems/institutions.yaml
```

打开 `http://127.0.0.1:8787`，可视化拓扑、实时事件流与 trace 联动。

<details>
<summary>使用真实 adapter（pc-agent-loop / OpenClaw）</summary>

**pc-agent-loop：**

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "真实任务" --input "请执行..." \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --trace-out traces/live.jsonl
```

可选参数：`--pc-shared-instance`（所有 runtime_id 共享一个后端实例）、`--pc-llm-no N`（选择 LLM 索引）

**OpenClaw：**

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "真实任务" --input "请执行..." \
  --adapter openclaw \
  --openclaw-deliver-mode auto \
  --openclaw-project-dir /path/to/openclaw/project \
  --trace-out traces/live.jsonl
```

`--openclaw-deliver-mode`：`auto`（推荐）/ `always` / `never`

</details>

<details>
<summary>运行基准测试（PinchBench / MultiAgentBench）</summary>

**PinchBench（OpenClaw）：**

```bash
python -m mas_engine.cli bench-pinch \
  --adapter openclaw \
  --model openrouter/openai/gpt-4o \
  --suite automated-only --runs 1 \
  --spec systems/institutions/egypt_pipeline \
  --out-dir traces/benchmarks/pinchbench
```

完整配置见 [PinchBench 运行手册](docs/pinchbench_runbook.md)。

**MultiAgentBench（MAS native）：**

```bash
python -m mas_engine.cli bench-mab \
  --execution-mode mas-native \
  --adapter pc-agent-loop \
  --model minimax/MiniMax-M2.5 \
  --scenario research,database --suite all \
  --spec systems/institutions/egypt_pipeline \
  --out-dir traces/benchmarks/multiagentbench
```

完整配置见 [MultiAgentBench 运行手册](docs/multiagentbench_runbook.md)。

</details>

---

## 添加新制度

```bash
python -m mas_engine.cli init-spec \
  --id my_institution \
  --name "我的制度" \
  --pattern gated_pipeline \
  --out systems/institutions/my_institution/my_institution.json
```

编辑生成的 spec，定义 stages、transitions 和 soul 提示词，然后注册到 `systems/institutions.yaml` 即可运行与跑分。

详见 [Spec 编写指南](docs/MAS_Governance_Engine_详细文档.md) 和 [Pattern 选型参考](docs/MAS_架构模式报告_修正版.md)。

---

## 项目结构

```
mas_engine/
├── core/              运行时核心（types / errors / features / runtime）
├── spec/              规范系统（templates / compiler / validators）
├── adapters/          运行时适配器（PcAgentLoop / OpenClaw / Mock）
├── observability/     事件流 + 异步任务管理
├── web/               Dashboard 前端
├── dashboard_server.py
└── cli.py

systems/
├── institutions/<id>/   制度 spec + soul 文件
├── institutions.yaml    制度到 spec 的映射注册表
└── pattern_souls/       可复用的 pattern 级 soul 模板

dsl/       CUE schema 定义
traces/    运行输出
tests/     单元测试
```

### 运行测试

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

---

## 引用

如果本工作对您有帮助，请引用我们的论文：

```bibtex
@misc{fei2026agentsevolveinstitutionsfollow,
      title={When Agents Evolve, Institutions Follow},
      author={Chao Fei and Hongcheng Guo and Yanghua Xiao},
      year={2026},
      eprint={2604.27691},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2604.27691},
}
```

## 许可证

本项目基于 [MIT 许可证](LICENSE) 发布。
