# Claw-Eval Runbook

Run [claw-eval](https://github.com/claw-eval/claw-eval) tasks under MAS governance institutions.

## How it works

claw-eval owns the full agent loop: LLM calls, tool dispatch, mock service lifecycle, and grading.
MAS governance is injected via `system_prompt_prefix` — a compact rendering of the active
governance spec (pattern, stages, soul instructions) is prepended to claw-eval's system prompt.
No changes to the claw-eval codebase are required.

## Setup

```bash
# Install claw-eval with mock services support (one-time)
pip install -e "third_party/claw-eval[mock]"

# Verify
claw-eval list
```

Set your API key:
```bash
export OPENROUTER_API_KEY=sk-or-...
```

## Single run (one spec)

```bash
python -m mas_engine.cli bench-claw \
  --model anthropic/claude-opus-4-6 \
  --spec systems/institutions/egypt_pipeline/egypt_pipeline.yaml \
  --suite all \
  --trials 1 \
  --out-dir traces/benchmarks/clawebench/egypt_pipeline
```

### Pass³ evaluation (recommended)

claw-eval's primary metric is Pass³: a task passes only if the agent succeeds in all 3 trials.

```bash
python -m mas_engine.cli bench-claw \
  --model anthropic/claude-opus-4-6 \
  --spec systems/institutions/tang_sanshengliubu/tang_sanshengliubu.yaml \
  --trials 3 \
  --out-dir traces/benchmarks/clawebench/tang_sanshengliubu
```

### No governance spec (baseline)

Omit `--spec` to run without any MAS governance injection:

```bash
python -m mas_engine.cli bench-claw \
  --model anthropic/claude-opus-4-6 \
  --suite all \
  --trials 3 \
  --out-dir traces/benchmarks/clawebench/baseline
```

## Batch run (all 7 institutions)

```bash
# Quick single-trial sweep
bash scripts/run_claw.sh

# Full Pass³ sweep
TRIALS=3 MODEL=anthropic/claude-opus-4-6 bash scripts/run_claw.sh

# Subset of tasks
SUITE=en TRIALS=3 bash scripts/run_claw.sh

# SLURM
sbatch --export=ALL,MODEL=anthropic/claude-opus-4-6,TRIALS=3 scripts/run_claw.sh
```

## Suite options

| Value | Selects |
|---|---|
| `all` | All 104 tasks |
| `en` | English-language tasks |
| `zh` | Chinese-language tasks |
| `category:productivity` | Tasks in the `productivity` category |
| `difficulty:medium` | Tasks with `difficulty: medium` |
| `T04_calendar_scheduling,T01zh_email_triage` | Specific task IDs |

## Output structure

```
traces/benchmarks/clawebench/<institution>/
  <timestamp>/
    claw_config.yaml          # Generated claw-eval config for this run
    results/
      summary.json            # Overall scores and Pass³ rates
      details.jsonl           # Per-trial scores
    traces/
      <task_id>/
        trial_01/
          stdout.txt          # claw-eval run output
          stderr.txt
          *.jsonl             # claw-eval trace files
```

### summary.json fields

```json
{
  "run_dir": "...",
  "spec": "tang_sanshengliubu",
  "model": "anthropic/claude-opus-4-6",
  "suite": "all",
  "trials": 3,
  "tasks": 104,
  "overall_score": 0.72,
  "pass3_rate": 0.61,
  "pass3_count": 63,
  "task_count": 104,
  "task_scores": {
    "T04_calendar_scheduling": {"avg_score": 0.85, "pass3": true},
    ...
  }
}
```

## All CLI options

```
python -m mas_engine.cli bench-claw --help

  --claw-root       path to claw-eval repo root (default: third_party/claw-eval)
  --model           model id (OpenRouter format, required)
  --api-key         API key (default: OPENROUTER_API_KEY env var)
  --base-url        API base URL
  --spec            governance spec file or directory (optional)
  --suite           task selection filter (default: all)
  --trials          trials per task (default: 1; use 3 for Pass³)
  --out-dir         output directory (default: traces/benchmarks/clawebench)
  --judge-model     judge model id
  --no-judge        disable LLM judge
  --task-timeout    per-task timeout in seconds (default: 600)
  --claw-eval-bin   claw-eval executable path (default: claw-eval)
```
