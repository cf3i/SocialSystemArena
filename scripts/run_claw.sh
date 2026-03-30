#!/usr/bin/env bash

#SBATCH --job-name=clawebench
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200GB
#SBATCH --time=48:00:00
#SBATCH --output=slurm-%x-%j.out
#SBATCH --error=slurm-%x-%j.err

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# In sbatch jobs, BASH_SOURCE points to a temporary spool script path.
# Prefer user-provided REPO_ROOT, then SLURM_SUBMIT_DIR, then script-adjacent fallback.
if [[ -n "${REPO_ROOT:-}" ]]; then
  REPO_ROOT_CANDIDATE="${REPO_ROOT}"
elif [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
  REPO_ROOT_CANDIDATE="${SLURM_SUBMIT_DIR}"
else
  REPO_ROOT_CANDIDATE="${SCRIPT_REPO_ROOT}"
fi

if [[ ! -f "${REPO_ROOT_CANDIDATE}/pyproject.toml" && -f "${REPO_ROOT_CANDIDATE}/../pyproject.toml" ]]; then
  REPO_ROOT_CANDIDATE="$(cd "${REPO_ROOT_CANDIDATE}/.." && pwd)"
fi

if [[ -f "${REPO_ROOT_CANDIDATE}/pyproject.toml" && -d "${REPO_ROOT_CANDIDATE}/mas_engine" ]]; then
  REPO_ROOT="$(cd "${REPO_ROOT_CANDIDATE}" && pwd)"
elif [[ -f "${SCRIPT_REPO_ROOT}/pyproject.toml" && -d "${SCRIPT_REPO_ROOT}/mas_engine" ]]; then
  REPO_ROOT="${SCRIPT_REPO_ROOT}"
else
  echo "[error] cannot locate repo root automatically." >&2
  echo "        set REPO_ROOT explicitly, e.g.:" >&2
  echo "        sbatch --export=ALL,REPO_ROOT=/home/feic/pjs/SocialSystemArena scripts/run_claw.sh" >&2
  exit 1
fi

cd "${REPO_ROOT}"

MODEL="${MODEL:-MiniMax-M2.5}"
ADAPTER="${ADAPTER:-pc-agent-loop}"
CLAW_ROOT="${CLAW_ROOT:-third_party/claw-eval}"
PC_AGENT_ROOT="${PC_AGENT_ROOT:-third_party/pc-agent-loop}"
PC_MYKEY="${PC_MYKEY:-third_party/pc-agent-loop/mykey.py}"
PC_LLM_NO="${PC_LLM_NO:-0}"
PC_SHARED_INSTANCE="${PC_SHARED_INSTANCE:-0}"
SUITE="${SUITE:-all}"
RUNS="${RUNS:-1}"
WORKER_TIMEOUT="${WORKER_TIMEOUT:-0}"
OUT_ROOT="${OUT_ROOT:-traces/benchmarks/clawebench}"
USE_JUDGE="${USE_JUDGE:-1}"
JUDGE_MODEL="${JUDGE_MODEL:-}"
JUDGE_TIMEOUT="${JUDGE_TIMEOUT:-180}"

SPECS=(
  "systems/institutions/athens_democracy/athens_democracy.yaml"
  "systems/institutions/qinhan_junxian/qinhan_junxian.yaml"
  "systems/institutions/tang_sanshengliubu/tang_sanshengliubu.yaml"
  "systems/institutions/mongol_empire/mongol_empire.yaml"
  "systems/institutions/us_federal/us_federal_gated.yaml"
  "systems/institutions/soviet_party_state/soviet_party_state.yaml"
  "systems/institutions/edo_bakuhan/edo_bakuhan.yaml"
)

# Optional override, space separated.
# Example:
# SPECS_OVERRIDE="systems/institutions/us_federal/us_federal_gated.yaml"
if [[ -n "${SPECS_OVERRIDE:-}" ]]; then
  # shellcheck disable=SC2206
  SPECS=( ${SPECS_OVERRIDE} )
fi

if ! command -v python >/dev/null 2>&1; then
  echo "[error] python not found in PATH" >&2
  exit 1
fi

if [[ ! -d "${CLAW_ROOT}/tasks" ]]; then
  echo "[error] claw-eval tasks dir not found: ${CLAW_ROOT}/tasks" >&2
  echo "        run: git submodule update --init --recursive" >&2
  exit 1
fi

if [[ "${ADAPTER}" == "pc-agent-loop" ]]; then
  if [[ ! -d "${PC_AGENT_ROOT}" ]]; then
    echo "[error] pc-agent-loop root not found: ${PC_AGENT_ROOT}" >&2
    exit 1
  fi
  if [[ ! -f "${PC_MYKEY}" ]]; then
    echo "[error] mykey file not found: ${PC_MYKEY}" >&2
    exit 1
  fi
fi

if ! [[ "${RUNS}" =~ ^[0-9]+$ ]] || [[ "${RUNS}" -lt 1 ]]; then
  echo "[error] RUNS must be a positive integer, got: ${RUNS}" >&2
  exit 1
fi

if ! [[ "${WORKER_TIMEOUT}" =~ ^[0-9]+$ ]]; then
  echo "[error] WORKER_TIMEOUT must be a non-negative integer, got: ${WORKER_TIMEOUT}" >&2
  exit 1
fi

if ! [[ "${PC_LLM_NO}" =~ ^[0-9]+$ ]]; then
  echo "[error] PC_LLM_NO must be a non-negative integer, got: ${PC_LLM_NO}" >&2
  exit 1
fi

if [[ "${USE_JUDGE}" != "0" && "${USE_JUDGE}" != "1" ]]; then
  echo "[error] USE_JUDGE must be 0 or 1, got: ${USE_JUDGE}" >&2
  exit 1
fi

for spec in "${SPECS[@]}"; do
  if [[ ! -f "${spec}" ]]; then
    echo "[error] spec file not found: ${spec}" >&2
    exit 1
  fi
done

COMMON_ARGS=(
  --claw-root "${CLAW_ROOT}"
  --model "${MODEL}"
  --adapter "${ADAPTER}"
  --suite "${SUITE}"
  --runs "${RUNS}"
  --worker-timeout "${WORKER_TIMEOUT}"
)

if [[ "${ADAPTER}" == "pc-agent-loop" ]]; then
  COMMON_ARGS+=(
    --pc-agent-root "${PC_AGENT_ROOT}"
    --pc-mykey "${PC_MYKEY}"
    --pc-llm-no "${PC_LLM_NO}"
  )
  if [[ "${PC_SHARED_INSTANCE}" == "1" ]]; then
    COMMON_ARGS+=(--pc-shared-instance)
  fi
fi

if [[ "${USE_JUDGE}" == "0" ]]; then
  COMMON_ARGS+=(--no-judge)
else
  COMMON_ARGS+=(--judge-timeout "${JUDGE_TIMEOUT}")
  if [[ -n "${JUDGE_MODEL}" ]]; then
    COMMON_ARGS+=(--judge-model "${JUDGE_MODEL}")
  fi
fi

echo "[info] repo_root=${REPO_ROOT}"
echo "[info] model=${MODEL} adapter=${ADAPTER} suite=${SUITE} runs=${RUNS}"
echo "[info] claw_root=${CLAW_ROOT} out_root=${OUT_ROOT} use_judge=${USE_JUDGE}"
echo "[info] worker_timeout=${WORKER_TIMEOUT}"
if [[ "${ADAPTER}" == "pc-agent-loop" ]]; then
  echo "[info] pc_agent_root=${PC_AGENT_ROOT} pc_mykey=${PC_MYKEY} pc_llm_no=${PC_LLM_NO} shared=${PC_SHARED_INSTANCE}"
fi

total="${#SPECS[@]}"
for i in "${!SPECS[@]}"; do
  spec="${SPECS[$i]}"
  inst="$(basename "$(dirname "${spec}")")"
  out_dir="${OUT_ROOT}/${inst}"

  echo "[info] [$((i + 1))/${total}] running spec=${spec}"
  python -m mas_engine.cli bench-claw \
    "${COMMON_ARGS[@]}" \
    --spec "${spec}" \
    --out-dir "${out_dir}"
done

echo "[done] all runs finished."
