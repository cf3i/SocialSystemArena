# PinchBench pc-agent-loop Patch

This folder contains a patch that adds `pc-agent-loop` adapter support to `bench-pinch`.

## Patch file

- `0001-bench-pinch-add-pc-agent-loop.patch`

## Apply

```bash
git apply third_party/pinchbench_patch/0001-bench-pinch-add-pc-agent-loop.patch
```

## What it changes

- Adds `--adapter {openclaw,pc-agent-loop}` and pc-agent-loop flags to `bench-pinch` CLI.
- Extends PinchBench runtime config with pc-agent-loop settings.
- Adds adapter branching in benchmark runtime (OpenClaw vs pc-agent-loop).
- Adds pc-agent-loop transcript extraction/normalization for automated grading compatibility.
- Adds tests and README examples.

## Quick smoke test

```bash
python -m mas_engine.cli bench-pinch \
  --adapter pc-agent-loop \
  --model minimax/MiniMax-M2.5 \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --pc-llm-no 0 \
  --suite task_00_sanity \
  --runs 1 \
  --no-judge \
  --spec systems/institutions/egypt_pipeline
```
