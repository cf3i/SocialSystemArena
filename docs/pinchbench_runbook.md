# PinchBench 复用运行手册（MAS + pc-agent-loop + MiniMax）

本文档记录在本仓库中可直接复用的 PinchBench 跑法，目标是稳定复现实验并沉淀结果数据。

## 1. 前置条件

1. 在仓库根目录执行，当前项目路径示例：`/Users/feic/Pjs/SocialSystemArena`
2. 子模块已拉取：

```bash
git submodule update --init --recursive
```

3. `pc-agent-loop` 的 `mykey.py` 已配置可用模型（你当前是 MiniMax）
4. Python 依赖可用（至少包含 `PyYAML`）：

```bash
pip install -e .
```

## 2. 任务规模确认

PinchBench 任务文件在 `third_party/pinchbench-skill/tasks`。

快速统计：

```bash
python - <<'PY'
from pathlib import Path
import re
tasks = sorted(Path("third_party/pinchbench-skill/tasks").glob("task_*.md"))
print("total:", len(tasks))
types = {"automated": 0, "llm_judge": 0, "hybrid": 0}
pat = re.compile(r"^grading_type:\s*(.+)$", re.MULTILINE)
for p in tasks:
    m = pat.search(p.read_text(encoding="utf-8"))
    if m:
        t = m.group(1).strip()
        types[t] = types.get(t, 0) + 1
print(types)
PY
```

你当前这套任务是 23 个（`task_00` 到 `task_22`）。

## 3. 10-task 冒烟（建议先跑）

```bash
python -m mas_engine.cli bench-pinch \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --pc-llm-no 0 \
  --pc-shared-instance \
  --model minimax \
  --spec systems/institutions/egypt_pipeline \
  --suite task_00,task_01,task_02,task_03,task_04,task_05,task_06,task_07,task_08,task_09
```

## 4. 全量 23-task（正式跑）

```bash
python -m mas_engine.cli bench-pinch \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --pc-llm-no 0 \
  --pc-shared-instance \
  --model minimax \
  --spec systems/institutions/egypt_pipeline \
  --suite all
```

可选参数：

1. `--runs N`：每个任务重复 N 次
2. `--judge-model <model>`：给 `llm_judge/hybrid` 单独指定 judge 模型（不填则跟 `--model` 一致）
3. `--no-judge`：跳过 judge（注意会影响 `llm_judge/hybrid` 的分数解释）
4. `--out-dir <dir>`：自定义输出目录（默认 `traces/benchmarks/pinchbench`）

## 5. 输出目录与结果文件

每次运行会在 `traces/benchmarks/pinchbench/<UTC时间戳>/` 下产生：

1. `results/summary.json`：总览（`overall_score`、`by_task`、状态统计）
2. `results/details.jsonl`：每个任务每次 run 的明细
3. `traces/*.jsonl`：MAS runtime trace
4. `workspaces/<task_id>/run_xx/`：任务执行工作区产物

## 6. 结果提取命令

查看最新 run 的总分与任务数：

```bash
latest=$(ls -1t traces/benchmarks/pinchbench | head -n1)
python - <<PY
import json, pathlib
p = pathlib.Path("traces/benchmarks/pinchbench") / "$latest" / "results" / "summary.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("run_dir:", d["run_dir"])
print("overall_score:", d["overall_score"])
print("selected_tasks:", d["selected_tasks"])
print("executed_runs:", d["executed_runs"])
print("status_counts:", d["status_counts"])
PY
```

导出按任务分数表：

```bash
latest=$(ls -1t traces/benchmarks/pinchbench | head -n1)
python - <<PY
import json, pathlib
p = pathlib.Path("traces/benchmarks/pinchbench") / "$latest" / "results" / "summary.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("task_id,grading_type,avg_score,best_score,worst_score")
for row in d.get("by_task", []):
    print(
        f'{row["task_id"]},{row["grading_type"]},'
        f'{row["avg_score"]:.4f},{row["best_score"]:.4f},{row["worst_score"]:.4f}'
    )
PY
```

## 7. 常见坑

1. `--no-judge` 会让 `llm_judge` 任务直接 0 分，`hybrid` 只保留 automated 部分，不能当作完整最终分。
2. `--spec systems/institutions/egypt_pipeline` 会自动解析目录里的规范文件（当前主要用 `egypt_pipeline.yaml`）。
3. `pc-agent-loop` 建议使用 `--pc-shared-instance`，可减少重复初始化开销。
4. 如果输出目录出现只有 `workspaces/` 没有 `results/summary.json`，通常是运行中断，直接重跑即可。

## 8. 复现实验推荐顺序

1. 先跑 10-task 冒烟，确认流程和产物稳定
2. 再跑 `--suite all` 做全量
3. 最后导出 `summary.json` 与 `details.jsonl` 做对比分析
