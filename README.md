# SocialSystemArena

A general MAS governance engine that models historical/social institutions as **declarative specs**.

This repository now contains a **new implementation** (independent from `sample/`) with:

- Pattern runtime: `pipeline`, `gated_pipeline`, `autonomous_cluster`, `consensus`
- Feature plugins: `monitor`, `shared_state`, `system_protocol`, `emergency_handler`, `human_confirmation`
- Spec compiler: `CUE/JSON -> normalized JSON IR`
- Adapter layer: `OpenClawAdapter` and `MockAdapter`

## Structure

- `mas_engine/core/`: runtime core (`types/errors/features/runtime`)
- `mas_engine/spec/`: spec system (`templates/compiler/validators`)
- `mas_engine/storage/`: trace storage backends
- `mas_engine/adapters/`: runtime adapter implementations
- `mas_engine/cli.py`: CLI entry
- `dsl/`: CUE schema
- `systems/`: institution specs (JSON/CUE)
- `tests/`: unit tests
- `sample/`: legacy reference code (not used by new engine)

## Why CUE + JSON

- Author specs in CUE for stronger constraints and composition
- Compile to JSON IR for stable runtime execution and auditing

## Quickstart

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

### 4) Run with OpenClaw adapter

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

## Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Notes

- CUE export requires `cue` CLI when loading `.cue` files
- JSON specs work without CUE installed

## Documentation

- Detailed Chinese doc: `docs/MAS_Governance_Engine_详细文档.md`
