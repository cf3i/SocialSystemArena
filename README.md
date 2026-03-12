# SocialSystemArena

A general MAS governance engine that models historical/social institutions as **declarative specs**.

This repository now contains a **new implementation** (independent from `sample/`) with:

- Pattern runtime: `pipeline`, `gated_pipeline`, `autonomous_cluster`, `consensus`
- Feature plugins: `monitor`, `shared_state`, `system_protocol`, `emergency_handler`, `human_confirmation`
- Spec compiler: `CUE/JSON/YAML -> normalized JSON IR`
- Adapter layer: `PcAgentLoopAdapter`, `OpenClawAdapter`, `MockAdapter`

## Structure

- `mas_engine/core/`: runtime core (`types/errors/features/runtime`)
- `mas_engine/spec/`: spec system (`templates/compiler/validators`)
- `mas_engine/storage/`: trace storage backends
- `mas_engine/adapters/`: runtime adapter implementations
- `mas_engine/cli.py`: CLI entry
- `dsl/`: CUE schema
- `systems/`: institution specs (JSON/CUE/YAML)
- `tests/`: unit tests
- `third_party/pc-agent-loop`: git submodule backend runtime used by `PcAgentLoopAdapter`

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
python -m mas_engine.cli validate --spec systems/tang_sanshengliubu.json
```

YAML works the same way:

```bash
python -m mas_engine.cli validate --spec systems/egypt_pipeline.yaml
```

### 2) Compile spec to IR

```bash
python -m mas_engine.cli compile \
  --spec systems/tang_sanshengliubu.json \
  --out build/tang.ir.json
```

### 3) Run task with mock adapter

```bash
python -m mas_engine.cli run \
  --spec systems/tang_sanshengliubu.json \
  --title "测试任务" \
  --input "请完成一个复杂任务" \
  --adapter mock \
  --trace-out traces/tang.jsonl
```

### 4) Run with pc-agent-loop adapter

```bash
python -m mas_engine.cli run \
  --spec systems/tang_sanshengliubu.json \
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
  --spec systems/tang_sanshengliubu.json \
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

## Built-in sample specs

- `systems/egypt_pipeline.json`
- `systems/qinhan_junxian.json`
- `systems/tang_sanshengliubu.json`
- `systems/us_federal_gated.json`
- `systems/edo_cluster.json`
- `systems/athens_consensus.json`
- `systems/egypt_pipeline.yaml` (YAML example)

## Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Notes

- CUE export requires `cue` CLI when loading `.cue` files
- JSON/YAML specs work without CUE installed

## Documentation

- Detailed Chinese doc: `docs/MAS_Governance_Engine_详细文档.md`
