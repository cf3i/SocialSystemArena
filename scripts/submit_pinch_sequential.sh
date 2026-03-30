#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT_DEFAULT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_ROOT="${REPO_ROOT:-${REPO_ROOT_DEFAULT}}"
MODEL="${MODEL:-gemini-2.5-flash}"
PC_MYKEY="${PC_MYKEY:-third_party/pc-agent-loop/mykey_gemini.py}"
OUT_ROOT="${OUT_ROOT:-traces/benchmarks/gemini_2.5_flash/pinchbench}"
DEPENDENCY_MODE="${DEPENDENCY_MODE:-afterok}"

if [[ "${DEPENDENCY_MODE}" != "afterok" && "${DEPENDENCY_MODE}" != "afterany" ]]; then
  echo "[error] DEPENDENCY_MODE must be afterok or afterany, got: ${DEPENDENCY_MODE}" >&2
  exit 1
fi

JOB_NAMES=(
  pinch_athens
  pinch_qinhan
  pinch_tang
  pinch_mongol
  pinch_us
  pinch_soviet
  pinch_edo
  pinch_bare
)

SPECS=(
  systems/institutions/athens_democracy/athens_democracy.yaml
  systems/institutions/qinhan_junxian/qinhan_junxian.yaml
  systems/institutions/tang_sanshengliubu/tang_sanshengliubu.yaml
  systems/institutions/mongol_empire/mongol_empire.yaml
  systems/institutions/us_federal/us_federal_gated.yaml
  systems/institutions/soviet_party_state/soviet_party_state.yaml
  systems/institutions/edo_bakuhan/edo_bakuhan.yaml
  systems/institutions/bare_pipeline/bare_pipeline.yaml
)

if [[ "${#JOB_NAMES[@]}" -ne "${#SPECS[@]}" ]]; then
  echo "[error] JOB_NAMES and SPECS length mismatch" >&2
  exit 1
fi

cd "${REPO_ROOT}"

for spec in "${SPECS[@]}"; do
  if [[ ! -f "${spec}" ]]; then
    echo "[error] spec file not found: ${spec}" >&2
    exit 1
  fi
done

prev_job_id=""

for i in "${!JOB_NAMES[@]}"; do
  job_name="${JOB_NAMES[$i]}"
  spec="${SPECS[$i]}"

  export_arg="ALL,REPO_ROOT=${REPO_ROOT},MODEL=${MODEL},PC_MYKEY=${PC_MYKEY},OUT_ROOT=${OUT_ROOT},SPECS_OVERRIDE=${spec}"
  submit_args=(--parsable -J "${job_name}" --export="${export_arg}")

  if [[ -n "${prev_job_id}" ]]; then
    submit_args+=(--dependency="${DEPENDENCY_MODE}:${prev_job_id}")
  fi

  submit_output="$(sbatch "${submit_args[@]}" scripts/run_pinch.sh)"
  job_id="${submit_output%%;*}"

  if [[ -z "${job_id}" ]]; then
    echo "[error] failed to parse job id from sbatch output: ${submit_output}" >&2
    exit 1
  fi

  if [[ -n "${prev_job_id}" ]]; then
    echo "[submitted] ${job_name} -> ${job_id} (${DEPENDENCY_MODE}:${prev_job_id})"
  else
    echo "[submitted] ${job_name} -> ${job_id} (root job)"
  fi

  prev_job_id="${job_id}"
done
