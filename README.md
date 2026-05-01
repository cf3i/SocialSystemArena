# SocialSystemArena

**When Agents Evolve, Institutions Follow**

[![arXiv](https://img.shields.io/badge/arXiv-2604.27691-b31b1b.svg)](https://arxiv.org/abs/2604.27691)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[**Paper**](https://arxiv.org/abs/2604.27691) | [**中文版 README**](README_zh.md)

SocialSystemArena models seven historical governance systems as declarative multi-agent specifications and benchmarks them on real-world tasks. Each institution is defined by a **Pattern** (message-flow topology) and composable **Features** (system-level capabilities), compiled into a unified governance runtime. The result is an empirical comparison of how different organizational structures affect agent task completion.

---

## News

- **2026-04** — Paper released on [arXiv](https://arxiv.org/abs/2604.27691). Code and benchmark data open-sourced.

---

## Overview

Multi-agent systems (MAS) often adopt ad-hoc coordination strategies. We take a different approach: drawing from seven real historical institutions — from the Mongol Empire's flat command chain to Athenian direct democracy — and encoding each as a declarative spec (YAML / JSON / CUE). A shared governance runtime executes all specs under identical conditions, enabling controlled comparison.

### Four Topology Patterns

| Pattern | Description | Example Institutions |
|---|---|---|
| `pipeline` | Linear chain, no blocking gates | Mongol Empire, Soviet Party State, Qin-Han Junxian |
| `gated_pipeline` | Pipeline with gate nodes that can reject / veto / modify | Tang Sanshengliubu, US Federal |
| `autonomous_cluster` | Orchestrator + internally autonomous subsystems | Edo Bakuhan |
| `consensus` | Collective voting, no single control node | Athens Democracy |

### Key Finding

Flat pipelines (Mongol Empire, 97.8) dramatically outperform deep gated architectures (US Federal, 64.4) on agent tasks. Depth is not the bottleneck — branching and gate density are. All seven historical institutions outperform a bare single-agent baseline (55.2), confirming that governance structure adds measurable value.

---

## Benchmark Results

> Model: MiniMax-M2.5 (pc-agent-loop adapter) | 21 tasks (excluding `task_13` due to environment constraints)

| Rank | Institution | Pattern | Adj. Mean | Tasks ≥ 90 | Zero-Score Tasks |
|:---:|---|---|:---:|:---:|:---:|
| 1 | Mongol Empire | `pipeline` | **97.8** | 20 / 21 | 0 |
| 2 | Edo Bakuhan | `autonomous_cluster` | **85.4** | 16 / 21 | 2 |
| 3 | Tang Sanshengliubu | `gated_pipeline` | **82.0** | 16 / 21 | 3 |
| 4 | Soviet Party State | `pipeline` | **78.9** | 15 / 21 | 2 |
| 5 | Qin-Han Junxian | `pipeline` | **69.4** | 11 / 21 | 2 |
| 6 | Athens Democracy | `consensus` | **68.4** | 13 / 21 | 5 |
| 7 | US Federal | `gated_pipeline` | **64.4** | 12 / 21 | 7 |
| — | *Bare Pipeline (baseline)* | `pipeline` | **55.1** | 10 / 21 | 8 |

### Institution Fingerprints

Avg. steps = measured per-task mean agent invocations (loops and retries increase this value).

| Institution | Pattern | Gates | Branches | Loops | Depth | Avg. Steps | Adj. Mean |
|---|---|---:|---:|---:|---:|---:|---:|
| Mongol Empire | `pipeline` | 0 | 0 | 0 | 6 | 5.6 | 97.8 |
| Edo Bakuhan | `autonomous_cluster` | 0 | 2 | 0 | 3 | 9.0 | 85.4 |
| Tang Sanshengliubu | `gated_pipeline` | 1 | 2 | 3 | 5 | 10.9 | 82.0 |
| Soviet Party State | `pipeline` | 0 | 0 | 0 | 5 | 5.0 | 78.9 |
| Qin-Han Junxian | `pipeline` | 0 | 1 | 1 | 4 | 8.0 | 69.4 |
| Athens Democracy | `consensus` | 0 | 2 | 0 | 2 | 8.9 | 68.4 |
| US Federal | `gated_pipeline` | 5 | 5 | 0 | 2 | 5.8 | 64.4 |
| *Bare Pipeline* | `pipeline` | 0 | 0 | 0 | 1 | 1.0 | 55.1 |

<details>
<summary>Full 22-task score matrix</summary>

`†` = runtime error but still scored | task_13 excluded from adjusted mean (no image generation API available)

| Task | Athens | Edo | Mongol | Qinhan | Soviet | Tang | US Fed | Bare | Mean |
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
| **Adj. Mean** (excl. task_13) | **68.4** | **85.4** | **97.8** | **69.4** | **78.9** | **82.0** | **64.4** | **55.1** | |

</details>

For detailed failure analysis and historical interpretation, see [docs/analysis.md](docs/analysis.md).

---

## Installation

**Requirements:** Python >= 3.10

```bash
# Clone with submodules
git clone --recursive https://github.com/cf3i/SocialSystemArena.git
cd SocialSystemArena

# Install
pip install -e .
```

---

## Quick Start

### Validate a spec

```bash
python -m mas_engine.cli validate \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json
```

### Run a task with the mock adapter

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "Test task" \
  --input "Complete a complex task" \
  --adapter mock \
  --trace-out traces/test.jsonl
```

### Launch the dashboard

```bash
python -m mas_engine.cli serve \
  --host 127.0.0.1 --port 8787 \
  --trace-dir traces/dashboard \
  --institutions systems/institutions.yaml
```

Open `http://127.0.0.1:8787` for topology visualization, live event streams, and trace exploration.

<details>
<summary>Using real adapters (pc-agent-loop / OpenClaw)</summary>

**pc-agent-loop:**

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "Real task" --input "Execute..." \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --trace-out traces/live.jsonl
```

Optional flags: `--pc-shared-instance` (share one backend instance across all runtime IDs), `--pc-llm-no N` (select LLM index).

**OpenClaw:**

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "Real task" --input "Execute..." \
  --adapter openclaw \
  --openclaw-deliver-mode auto \
  --openclaw-project-dir /path/to/openclaw/project \
  --trace-out traces/live.jsonl
```

`--openclaw-deliver-mode`: `auto` (recommended) / `always` / `never`

</details>

<details>
<summary>Running benchmarks (PinchBench / MultiAgentBench)</summary>

**PinchBench (OpenClaw):**

```bash
python -m mas_engine.cli bench-pinch \
  --adapter openclaw \
  --model openrouter/openai/gpt-4o \
  --suite automated-only --runs 1 \
  --spec systems/institutions/egypt_pipeline \
  --out-dir traces/benchmarks/pinchbench
```

See [PinchBench runbook](docs/pinchbench_runbook.md) for full configuration.

**MultiAgentBench (MAS native):**

```bash
python -m mas_engine.cli bench-mab \
  --execution-mode mas-native \
  --adapter pc-agent-loop \
  --model minimax/MiniMax-M2.5 \
  --scenario research,database --suite all \
  --spec systems/institutions/egypt_pipeline \
  --out-dir traces/benchmarks/multiagentbench
```

See [MultiAgentBench runbook](docs/multiagentbench_runbook.md) for full configuration.

</details>

---

## Adding a New Institution

```bash
python -m mas_engine.cli init-spec \
  --id my_institution \
  --name "My Institution" \
  --pattern gated_pipeline \
  --out systems/institutions/my_institution/my_institution.json
```

Edit the generated spec to define stages, transitions, and soul prompts, then register it in `systems/institutions.yaml`.

See [Spec authoring guide](docs/MAS_Governance_Engine_详细文档.md) and [Pattern selection reference](docs/MAS_架构模式报告_修正版.md) for details.

---

## Project Structure

```
mas_engine/
├── core/              Runtime core (types, errors, features, runtime)
├── spec/              Spec system (templates, compiler, validators)
├── adapters/          Runtime adapters (PcAgentLoop, OpenClaw, Mock)
├── observability/     Event stream + async task management
├── web/               Dashboard frontend
├── dashboard_server.py
└── cli.py

systems/
├── institutions/<id>/   Institution specs + soul files
├── institutions.yaml    Institution-to-spec registry
└── pattern_souls/       Reusable pattern-level soul templates

dsl/       CUE schema definitions
traces/    Run outputs
tests/     Unit tests
```

### Running Tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

---

## Citation

If you find this work useful, please cite our paper:

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

## License

This project is released under the [MIT License](LICENSE).
