# SocialSystemArena

A general MAS governance engine that models historical/social institutions as **declarative specs**.

This repository now contains a **new implementation** (independent from `sample/`) with:

- Pattern runtime: `pipeline`, `gated_pipeline`, `autonomous_cluster`, `consensus`
- Feature plugins: `monitor`, `shared_state`, `system_protocol`, `emergency_handler`, `human_confirmation`
- Spec compiler: `CUE/JSON/YAML -> normalized JSON IR`
- Adapter layer: `PcAgentLoopAdapter`, `OpenClawAdapter`, `MockAdapter`
- Dashboard backend: HTTP API + SSE event stream + real-time topology view

## Structure

- `mas_engine/core/`: runtime core (`types/errors/features/runtime`)
- `mas_engine/spec/`: spec system (`templates/compiler/validators`)
- `mas_engine/storage/`: trace storage backends
- `mas_engine/adapters/`: runtime adapter implementations
- `mas_engine/observability/`: event stream + async task manager
- `mas_engine/web/`: dashboard frontend
- `mas_engine/dashboard_server.py`: API/SSE server
- `mas_engine/cli.py`: CLI entry
- `dsl/`: CUE schema
- `systems/pattern_souls/`: reusable pattern-level SOUL files
- `systems/institutions/<institution_id>/`: institution specs + institution souls
- `systems/institutions.yaml`: institution -> spec mapping registry
- `tests/`: unit tests
- `third_party/pc-agent-loop`: git submodule backend runtime used by `PcAgentLoopAdapter`
- `third_party/pinchbench-skill`: PinchBench task/asset submodule for benchmark runs
- `third_party/multiagentbench`: MultiAgentBench (MARBLE) submodule for benchmark runs

## Why CUE + JSON/YAML

- Author specs in CUE for stronger constraints and composition
- Compile to JSON IR for stable runtime execution and auditing
- YAML is supported for easier manual editing

## Quickstart

Initialize third-party submodules first:

```bash
git submodule update --init --recursive
```

### 0) Generate a starter template

```bash
python -m mas_engine.cli init-spec \
  --id my_institution \
  --name "我的制度" \
  --pattern gated_pipeline \
  --out systems/my_institution.json
```

### 1) Validate spec

```bash
python -m mas_engine.cli validate --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json
```

YAML works the same way:

```bash
python -m mas_engine.cli validate --spec systems/institutions/egypt_pipeline/egypt_pipeline.yaml
```

### 2) Compile spec to IR

```bash
python -m mas_engine.cli compile \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --out build/tang.ir.json
```

### 3) Run task with mock adapter

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "测试任务" \
  --input "请完成一个复杂任务" \
  --adapter mock \
  --trace-out traces/tang.jsonl
```

### 4) Run with pc-agent-loop adapter

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "真实任务" \
  --input "请执行..." \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --trace-out traces/live.jsonl
```

Optional pc-agent-loop flags:
- `--pc-shared-instance`: one backend instance shared across all runtime_ids
- `--pc-llm-no N`: choose LLM backend index from `mykey` list
- `--pc-mykey`: explicit `mykey.py` / `mykey.json` path

Trace (`--trace-out`) now writes two record types:
- `stage_event`: stage-level transition record
- `agent_trace`: one row per agent dispatch, with `sequential_id`

### 5) Run with OpenClaw adapter

```bash
python -m mas_engine.cli run \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json \
  --title "真实任务" \
  --input "请执行..." \
  --adapter openclaw \
  --openclaw-deliver-mode auto \
  --openclaw-project-dir /path/to/openclaw/project \
  --trace-out traces/live.jsonl
```

`--openclaw-deliver-mode` options:
- `auto`: try `--deliver`, fallback if CLI does not support it
- `always`: always append `--deliver`
- `never`: never append `--deliver`

### 6) Start Dashboard + event backend

```bash
python -m mas_engine.cli serve \
  --host 127.0.0.1 \
  --port 8787 \
  --trace-dir traces/dashboard \
  --institutions systems/institutions.yaml
```

Then open: `http://127.0.0.1:8787`

Dashboard capabilities:
- Choose by institution name instead of raw file path
- Switch spec versions under one institution
- Customize spec in Builder (`pattern + features + stages`) and generate YAML
- Advanced Stage Inspector for `consensus` voters and `cluster` members
- Submit tasks from UI (`institution/spec + adapter + input`)
- Live stream per-task events via SSE
- Visualize topology as interactive SVG graph with node-edge labels
- Stage-event-trace linkage: click node/event/trace to focus by stage
- Filter/search events and traces in real time
- Show per-agent trace rows (`sequential_id`, `agent_id`, `decision`, `summary`)

Prompt composition (runtime):
- `stage.description` (node objective)
- `systems/pattern_souls/<pattern>/<stage.kind>.md` (pattern-level node rules, optional)
- `stage.soul_file_path` (institution node soul)
- precedence: `Stage Objective > Institution SOP > Pattern Rules`
- rendered with fixed labeled sections (`[Stage Objective] / [Pattern Rules] / [Institution SOP]`)
- runtime applies line dedup + length clipping to reduce repeated/overlong prompts

Core API endpoints:
- `POST /api/runs`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/topology`
- `GET /api/tasks/{task_id}/events?since=0&limit=200`
- `GET /api/tasks/{task_id}/stream?since=0` (SSE)
- `GET /api/institutions`
- `GET /api/institutions/{institution_id}`
- `GET /api/specs/{spec_id}`
- `POST /api/specs/validate`
- `POST /api/specs/to-yaml`

### 7) Run PinchBench with MAS runtime

PinchBench tasks can be executed through this engine with either `openclaw` or `pc-agent-loop` adapter.

OpenClaw backend example:

```bash
python -m mas_engine.cli bench-pinch \
  --adapter openclaw \
  --model openrouter/openai/gpt-4o \
  --suite automated-only \
  --runs 1 \
  --spec systems/institutions/egypt_pipeline \
  --out-dir traces/benchmarks/pinchbench
```

pc-agent-loop backend example:

```bash
python -m mas_engine.cli bench-pinch \
  --adapter pc-agent-loop \
  --model minimax/MiniMax-M2.5 \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --pc-llm-no 0 \
  --suite automated-only \
  --runs 1 \
  --spec systems/institutions/egypt_pipeline \
  --out-dir traces/benchmarks/pinchbench
```

Notes:
- `--pinch-root` defaults to `third_party/pinchbench-skill`.
- `--spec` is optional. You can pass a spec file or an institution directory.
- `bench-pinch` defaults `--openclaw-deliver-mode` to `never` (benchmark runs are local workspace tasks).
- `--adapter` defaults to `openclaw`; use `pc-agent-loop` to run via `third_party/pc-agent-loop`.
- `--suite` supports `all`, `automated-only`, or comma-separated task ids.
- `llm_judge/hybrid` tasks use judge model from `--judge-model` (or fall back to `--model`).
- Outputs are saved under `--out-dir/<UTC timestamp>/results/{summary.json,details.jsonl}`.

### 8) Run MultiAgentBench with MAS runtime or MARBLE native runtime

MAS runtime (with governance spec + adapter) example:

```bash
python -m mas_engine.cli bench-mab \
  --execution-mode mas-native \
  --adapter pc-agent-loop \
  --model minimax/MiniMax-M2.5 \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --pc-llm-no 0 \
  --pc-shared-instance \
  --mab-root third_party/multiagentbench \
  --scenario research,database \
  --suite all \
  --spec systems/institutions/egypt_pipeline \
  --out-dir traces/benchmarks/multiagentbench
```

MARBLE native example:

```bash
python -m mas_engine.cli bench-mab \
  --execution-mode marble-native \
  --model minimax/MiniMax-M2.5 \
  --mab-root third_party/multiagentbench \
  --scenario all \
  --suite all \
  --marble-python python \
  --out-dir traces/benchmarks/multiagentbench/marble_native
```

SLURM helper scripts:

```bash
# full run
sbatch --export=ALL,REPO_ROOT=/home/feic/pjs/SocialSystemArena scripts/run_mab.sh

# rerun failed tasks from latest run
sbatch --export=ALL,REPO_ROOT=/home/feic/pjs/SocialSystemArena scripts/rerun_mab_errors.sh
```

Notes:
- `--mab-root` defaults to `third_party/multiagentbench`.
- `--scenario` supports `all` or comma-separated: `research,bargaining,coding,database,minecraft`.
- `--suite` supports `all`, comma-separated task ids, `scenario:id`, or full task uid (for rerun).
- `bench-mab` supports two execution modes:
  - `mas-native`: through GovernanceRuntime + adapter + optional governance spec.
  - `marble-native`: direct call to `third_party/multiagentbench/marble/main.py`.
- Outputs are saved under `--out-dir/<UTC timestamp>/results/{summary.json,details.jsonl}`.

## Built-in sample specs

- `systems/institutions/egypt_pipeline/egypt_pipeline.json`
- `systems/institutions/qinhan_junxian/qinhan_junxian.json`
- `systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json`
- `systems/institutions/us_federal/us_federal_gated.json`
- `systems/institutions/athens_democracy/athens_consensus.json`
- `systems/institutions/egypt_pipeline/egypt_pipeline.yaml` (YAML example)

## Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Notes

- CUE export requires `cue` CLI when loading `.cue` files
- JSON/YAML specs work without CUE installed

## Documentation

- Detailed Chinese doc: `docs/MAS_Governance_Engine_详细文档.md`
- PinchBench runbook: `docs/pinchbench_runbook.md`
- MultiAgentBench runbook: `docs/multiagentbench_runbook.md`
