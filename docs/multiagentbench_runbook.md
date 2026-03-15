# MultiAgentBench 复用运行手册（MAS native + MARBLE native）

本文档记录在本仓库中可直接复用的 MultiAgentBench 跑法，覆盖两种执行模式：

1. `mas-native`：通过本仓库 `GovernanceRuntime` 执行（可挂制度 spec）。
2. `marble-native`：直接调用子模块 `MARBLE` 原生执行。

## 1. 前置条件

1. 在仓库根目录执行，路径示例：`/home/feic/pjs/SocialSystemArena`
2. 子模块已拉取：

```bash
git submodule update --init --recursive
```

3. `pc-agent-loop` 的 `mykey.py` 已配置可用模型（若使用 `pc-agent-loop` 适配器）
4. Python 依赖可用（至少包含 `PyYAML`）：

```bash
pip install -e .
```

## 2. 数据规模确认

任务数据位于：`third_party/multiagentbench/multiagentbench/<scenario>/*.jsonl`。

快速统计：

```bash
python - <<'PY'
from pathlib import Path
import json

root = Path("third_party/multiagentbench/multiagentbench")
total = 0
by_scenario = {}
for scenario_dir in sorted(p for p in root.iterdir() if p.is_dir()):
    n = 0
    for f in sorted(scenario_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)
                n += 1
    by_scenario[scenario_dir.name] = n
    total += n

print("total:", total)
print("by_scenario:", by_scenario)
PY
```

## 3. 冒烟建议（先跑小子集）

建议先挑一个场景前几个任务：

```bash
python -m mas_engine.cli bench-mab \
  --execution-mode mas-native \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --pc-llm-no 0 \
  --pc-shared-instance \
  --model minimax/MiniMax-M2.5 \
  --mab-root third_party/multiagentbench \
  --scenario research \
  --suite research:1,research:2,research:3 \
  --spec systems/institutions/egypt_pipeline \
  --runs 1
```

## 4. 正式跑（MAS native）

```bash
python -m mas_engine.cli bench-mab \
  --execution-mode mas-native \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --pc-llm-no 0 \
  --pc-shared-instance \
  --model minimax/MiniMax-M2.5 \
  --mab-root third_party/multiagentbench \
  --scenario all \
  --suite all \
  --spec systems/institutions/egypt_pipeline
```

可选参数：

1. `--runs N`：每个任务重复 N 次
2. `--judge-model <model>`：指定 judge 模型（默认跟 `--model` 一致）
3. `--no-judge`：跳过 judge（会影响部分场景分数解释）
4. `--worker-timeout <sec>`：为 stage dispatch 提供超时下限
5. `--out-dir <dir>`：自定义输出目录（默认 `traces/benchmarks/multiagentbench`）

## 5. 正式跑（MARBLE native）

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

说明：

1. `marble-native` 会直接调用 `third_party/multiagentbench/marble/main.py --config_path ...`
2. 该模式不依赖 `--spec`
3. `--adapter` 参数会被保留但不参与执行路径

## 6. SLURM 脚本

全量多制度运行（MAS native）：

```bash
sbatch --export=ALL,REPO_ROOT=/home/feic/pjs/SocialSystemArena scripts/run_mab.sh
```

从最近一次结果中抽取失败任务并重跑：

```bash
sbatch --export=ALL,REPO_ROOT=/home/feic/pjs/SocialSystemArena scripts/rerun_mab_errors.sh
```

常用环境变量：

1. `MODEL`、`ADAPTER`、`SCENARIO`、`RUNS`
2. `EXECUTION_MODE=mas-native|marble-native`
3. `RETRY_STATUSES`（默认 `error`）
4. `SPECS_OVERRIDE`（空格分隔 spec 路径，覆盖默认制度列表）

## 7. 输出目录与结果文件

每次运行会在 `traces/benchmarks/multiagentbench/<group>/<UTC时间戳>/`（或直接 `<UTC时间戳>/`）下产生：

1. `results/summary.json`：总览（`overall_score`、`by_task`、`status_counts`）
2. `results/details.jsonl`：每个任务每次 run 的明细
3. `traces/*.jsonl`：MAS runtime trace（仅 `mas-native`）
4. `workspaces/<task_uid>/run_xx/`：任务执行工作区产物

## 8. 结果提取命令

查看最新 run 的总分：

```bash
latest=$(ls -1t traces/benchmarks/multiagentbench | head -n1)
python - <<PY
import json, pathlib
p = pathlib.Path("traces/benchmarks/multiagentbench") / "$latest" / "results" / "summary.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("run_dir:", d["run_dir"])
print("execution_mode:", d["execution_mode"])
print("overall_score:", d["overall_score"])
print("selected_tasks:", d["selected_tasks"])
print("executed_runs:", d["executed_runs"])
print("status_counts:", d["status_counts"])
PY
```

按场景输出平均分：

```bash
latest=$(ls -1t traces/benchmarks/multiagentbench | head -n1)
python - <<PY
import json, pathlib
p = pathlib.Path("traces/benchmarks/multiagentbench") / "$latest" / "results" / "summary.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("scenario,avg_score,runs,status_counts")
for row in d.get("by_scenario", []):
    print(f'{row["scenario"]},{row["avg_score"]:.4f},{row["runs"]},{row["status_counts"]}')
PY
```

## 9. 常见坑

1. 没有初始化子模块会报 `MultiAgentBench data directory not found`
2. `--no-judge` 会让需要 judge 的场景退化为自动评分/简化评分
3. `marble-native` 下如果 `marble/main.py` 入口不存在，通常是子模块版本或目录错误
4. `suite` 推荐用 `task_uid`（如 `research:1`）以避免跨场景 task id 重名
