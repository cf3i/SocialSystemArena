"""MultiAgentBench integration powered by MAS runtime."""

from __future__ import annotations

import copy
import json
import logging
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - guarded in runtime usage
    raise RuntimeError(
        "MultiAgentBench integration requires PyYAML. Install with `pip install pyyaml`."
    ) from exc

from ..adapters import AgentAdapter
from ..core.runtime import GovernanceRuntime
from ..spec.compiler import compile_spec, compile_spec_obj
from ..storage.jsonl import JsonlStore
from .common import (
    average,
    build_runtime_adapter,
    clip01,
    count_by,
    extract_pc_agent_loop_transcript,
    load_latest_openclaw_transcript,
    make_agent_id,
    make_run_dir,
    parse_judge_payload,
    write_result_files,
)

_LOG = logging.getLogger("mas_engine.benchmark.multiagentbench")

SUPPORTED_SCENARIOS = {"research", "bargaining", "coding", "database", "minecraft"}
_DATABASE_LABEL_FALLBACK = [
    "INSERT_LARGE_DATA",
    "MISSING_INDEXES",
    "LOCK_CONTENTION",
    "VACUUM",
    "REDUNDANT_INDEX",
    "FETCH_LARGE_DATA",
    "POOR_JOIN_PERFORMANCE",
    "CPU_CONTENTION",
]

_SCENARIO_DEFAULTS: dict[str, dict[str, Any]] = {
    "research": {
        "coordinate_mode": "graph",
        "environment": {
            "type": "Research",
            "name": "Research Collaboration Environment",
            "max_iterations": 5,
        },
        "memory": {"type": "BaseMemory"},
        "output": {"file_path": "result/research_output.jsonl"},
    },
    "bargaining": {
        "coordinate_mode": "graph",
        "environment": {
            "type": "WorldSimulation",
            "name": "World Simulation Environment",
            "max_iterations": 5,
        },
        "memory": {"type": "BaseMemory"},
        "output": {"file_path": "result/bargaining_output.jsonl"},
    },
    "coding": {
        "coordinate_mode": "graph",
        "environment": {
            "type": "Coding",
            "name": "Coding Environment",
            "max_iterations": 5,
            "workspace_dir": "workspace",
        },
        "memory": {"type": "SharedMemory"},
        "output": {"file_path": "result/coding_output.jsonl"},
    },
    "database": {
        "coordinate_mode": "graph",
        "environment": {
            "type": "DB",
            "name": "DB Simulation Environment",
            "max_iterations": 5,
        },
        "memory": {"type": "SharedMemory"},
        "output": {"file_path": "result/database_output.jsonl"},
    },
    "minecraft": {
        "coordinate_mode": "graph",
        "environment": {
            "type": "Minecraft",
            "name": "Minecraft Environment",
            "max_iterations": 20,
        },
        "memory": {"type": "BaseMemory"},
        "output": {"file_path": "result/minecraft_output.jsonl"},
    },
}


@dataclass
class MultiAgentBenchTask:
    scenario: str
    task_id: int
    task_uid: str
    coordinate_mode: str
    relationships: list[list[str]]
    agents: list[dict[str, Any]]
    llm: str
    environment: dict[str, Any]
    memory: dict[str, Any]
    metrics: dict[str, Any]
    engine_planner: dict[str, Any]
    output: dict[str, Any]
    prompt: str
    output_format: str
    labels: list[str]
    root_causes: list[str]
    number_of_labels_pred: int
    source_file: str
    raw_payload: dict[str, Any]


@dataclass
class MultiAgentBenchGradeResult:
    task_uid: str
    scenario: str
    grading_type: str
    score: float
    max_score: float
    breakdown: dict[str, float]
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_uid": self.task_uid,
            "scenario": self.scenario,
            "grading_type": self.grading_type,
            "score": self.score,
            "max_score": self.max_score,
            "breakdown": dict(self.breakdown),
            "notes": self.notes,
        }


@dataclass
class MultiAgentBenchRunConfig:
    mab_root: Path
    model: str
    scenario: str = "all"
    suite: str = "all"
    runs: int = 1
    output_dir: Path = Path("traces/benchmarks/multiagentbench")
    adapter: str = "openclaw"
    openclaw_bin: str = "openclaw"
    openclaw_deliver_mode: str = "auto"
    openclaw_project_dir: str | None = None
    pc_agent_root: str = "third_party/pc-agent-loop"
    pc_mykey: str | None = None
    pc_llm_no: int | None = None
    pc_shared_instance: bool = False
    worker_timeout_sec: int = 0
    judge_model: str | None = None
    judge_timeout_sec: int = 180
    no_judge: bool = False
    keep_agents: bool = False
    benchmark_spec_path: Path | None = None
    execution_mode: str = "mas-native"
    marble_python_bin: str = "python"


def run_multiagentbench(config: MultiAgentBenchRunConfig) -> dict[str, Any]:
    mab_root = config.mab_root.expanduser().resolve()
    tasks = load_multiagent_tasks(mab_root, default_model=config.model)
    selected_tasks = select_multiagent_tasks(tasks, config.scenario, config.suite)
    if not selected_tasks:
        raise ValueError(
            f"No MultiAgentBench tasks selected by scenario='{config.scenario}' suite='{config.suite}'"
        )

    run_dir = make_run_dir(config.output_dir)
    rows: list[dict[str, Any]] = []

    mode = str(config.execution_mode or "mas-native").strip().lower()
    if mode == "mas-native":
        rows = _run_multiagentbench_mas_mode(config, selected_tasks, run_dir)
    elif mode == "marble-native":
        rows = _run_multiagentbench_marble_mode(config, selected_tasks, run_dir)
    else:
        raise ValueError(
            f"unsupported execution mode '{config.execution_mode}', expected mas-native or marble-native"
        )

    summary = _build_summary(rows=rows, run_dir=run_dir, config=config, selected=selected_tasks)
    write_result_files(rows=rows, summary=summary, run_dir=run_dir)
    return summary


def load_multiagent_tasks(
    mab_root: str | Path,
    default_model: str = "",
) -> list[MultiAgentBenchTask]:
    root = Path(mab_root).expanduser().resolve()
    data_root = root / "multiagentbench"
    if not data_root.exists():
        raise FileNotFoundError(f"MultiAgentBench data directory not found: {data_root}")

    out: list[MultiAgentBenchTask] = []
    for scenario_dir in sorted(p for p in data_root.iterdir() if p.is_dir()):
        scenario = scenario_dir.name.strip().lower()
        if scenario not in SUPPORTED_SCENARIOS:
            continue

        files = sorted(scenario_dir.glob("*.jsonl"))
        for path in files:
            lines = path.read_text(encoding="utf-8").splitlines()
            task_no = 0
            for raw_line in lines:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    _LOG.warning("skip invalid JSONL line: %s", path)
                    continue
                if not isinstance(payload, dict):
                    continue

                task_no += 1
                task_id = _coerce_task_id(payload.get("task_id"), fallback=task_no)
                task = _normalize_task_payload(
                    payload=payload,
                    scenario=scenario,
                    task_id=task_id,
                    source_file=path,
                    default_model=default_model,
                )
                out.append(task)
    return out


def select_multiagent_tasks(
    tasks: list[MultiAgentBenchTask],
    scenario: str,
    suite: str,
) -> list[MultiAgentBenchTask]:
    scenario_mode = str(scenario or "all").strip().lower()
    if scenario_mode == "all":
        scenario_filtered = list(tasks)
    else:
        scenarios = {
            x.strip().lower()
            for x in scenario_mode.split(",")
            if x.strip()
        }
        unknown = sorted(x for x in scenarios if x not in SUPPORTED_SCENARIOS)
        if unknown:
            raise ValueError(
                f"unsupported scenario(s): {', '.join(unknown)}; expected one of {sorted(SUPPORTED_SCENARIOS)}"
            )
        scenario_filtered = [t for t in tasks if t.scenario in scenarios]

    mode = str(suite or "all").strip().lower()
    if mode == "all":
        return scenario_filtered

    ids = {x.strip().lower() for x in str(suite).split(",") if x.strip()}
    selected: list[MultiAgentBenchTask] = []
    for task in scenario_filtered:
        aliases = {
            task.task_uid.lower(),
            f"{task.scenario}:{task.task_id}".lower(),
            f"task_{task.task_id}".lower(),
            str(task.task_id).lower(),
        }
        if aliases & ids:
            selected.append(task)
    return selected


def grade_multiagent_database(
    task: MultiAgentBenchTask,
    transcript: list[dict[str, Any]],
    final_text: str,
) -> MultiAgentBenchGradeResult:
    labels = [x.strip().upper() for x in (task.labels or _DATABASE_LABEL_FALLBACK) if x.strip()]
    gold = {x.strip().upper() for x in task.root_causes if x.strip()}
    text = "\n".join(
        [
            str(final_text or ""),
            _extract_text_from_transcript(transcript),
        ]
    ).upper()

    found: list[str] = []
    for label in labels:
        if re.search(rf"\b{re.escape(label)}\b", text):
            found.append(label)
    uniq_found = sorted(set(found))

    if not gold:
        score = 0.0
        precision = 0.0
        recall = 0.0
        f1 = 0.0
    else:
        matched = len(gold & set(uniq_found))
        precision = (matched / len(uniq_found)) if uniq_found else 0.0
        recall = matched / len(gold)
        if precision + recall <= 0:
            f1 = 0.0
        else:
            f1 = (2 * precision * recall) / (precision + recall)
        score = clip01(f1)

    breakdown = {
        "database.precision": clip01(precision),
        "database.recall": clip01(recall),
        "database.f1": clip01(f1),
    }
    notes = f"predicted={uniq_found} gold={sorted(gold)}"
    return MultiAgentBenchGradeResult(
        task_uid=task.task_uid,
        scenario=task.scenario,
        grading_type="database_rule",
        score=score,
        max_score=1.0,
        breakdown=breakdown,
        notes=notes,
    )


def _run_multiagentbench_mas_mode(
    config: MultiAgentBenchRunConfig,
    selected_tasks: list[MultiAgentBenchTask],
    run_dir: Path,
) -> list[dict[str, Any]]:
    adapter, use_openclaw_agent_lifecycle = build_runtime_adapter(
        adapter=config.adapter,
        openclaw_bin=config.openclaw_bin,
        openclaw_deliver_mode=config.openclaw_deliver_mode,
        openclaw_project_dir=config.openclaw_project_dir,
        pc_agent_root=config.pc_agent_root,
        pc_mykey=config.pc_mykey,
        pc_llm_no=config.pc_llm_no,
        pc_shared_instance=config.pc_shared_instance,
        source="mas_engine.multiagentbench",
    )

    base_spec = None
    if config.benchmark_spec_path is not None:
        resolved_spec = _resolve_spec_path(config.benchmark_spec_path)
        base_spec = compile_spec(resolved_spec)
        _LOG.info("multiagentbench using custom governance spec: %s", resolved_spec)

    judge_agent_id = ""
    judge_workspace = run_dir / "_judge_workspace"
    if _requires_judge(selected_tasks) and not config.no_judge:
        judge_model = (config.judge_model or config.model).strip()
        if not judge_model:
            raise ValueError("judge model is empty")
        judge_agent_id = make_agent_id("mas-mab-judge", judge_model, "judge")
        if use_openclaw_agent_lifecycle:
            _recreate_openclaw_agent(
                openclaw_bin=config.openclaw_bin,
                agent_id=judge_agent_id,
                model=judge_model,
                workspace=judge_workspace,
            )

    rows: list[dict[str, Any]] = []
    try:
        for task in selected_tasks:
            for run_idx in range(1, max(1, int(config.runs)) + 1):
                row = _run_single_task_mas(
                    task=task,
                    run_idx=run_idx,
                    config=config,
                    adapter=adapter,
                    run_dir=run_dir,
                    judge_agent_id=judge_agent_id,
                    base_spec=base_spec,
                    use_openclaw_agent_lifecycle=use_openclaw_agent_lifecycle,
                )
                rows.append(row)
                _LOG.info(
                    "mab scenario=%s task=%s run=%s status=%s score=%.3f",
                    task.scenario,
                    task.task_id,
                    run_idx,
                    row.get("runtime_status"),
                    float(row.get("score", 0.0)),
                )
    finally:
        if judge_agent_id and not config.keep_agents and use_openclaw_agent_lifecycle:
            _delete_openclaw_agent(config.openclaw_bin, judge_agent_id)

    return rows


def _run_single_task_mas(
    task: MultiAgentBenchTask,
    run_idx: int,
    config: MultiAgentBenchRunConfig,
    adapter: AgentAdapter,
    run_dir: Path,
    judge_agent_id: str,
    base_spec: Any = None,
    use_openclaw_agent_lifecycle: bool = True,
) -> dict[str, Any]:
    workspace = run_dir / "workspaces" / task.task_uid / f"run_{run_idx:02d}"
    _prepare_workspace(task=task, workspace=workspace)

    worker_timeout_floor = max(0, int(config.worker_timeout_sec or 0))
    task_input = _build_task_input(task=task, workspace=workspace)
    max_steps = max(4, int(task.environment.get("max_iterations", 5)) + 2)
    worker_agent_ids: list[str] = []

    if base_spec is None:
        worker_agent_ids.append(
            make_agent_id("mas-mab-worker", config.model, f"{task.task_uid}-{run_idx}")
        )
        spec = _build_task_spec(
            task=task,
            runtime_id=worker_agent_ids[0],
            workspace=workspace,
            worker_timeout_sec=worker_timeout_floor,
        )
    else:
        spec = copy.deepcopy(base_spec)
        _apply_benchmark_stage_objectives(spec=spec, task=task, workspace=workspace)
        for agent_key, agent in sorted(spec.agents.items()):
            runtime_id = make_agent_id(
                "mas-mab-worker",
                config.model,
                f"{task.task_uid}-{run_idx}-{agent_key}",
            )
            agent.runtime_id = runtime_id
            agent.timeout_sec = max(
                int(getattr(agent, "timeout_sec", 300)),
                60,
                worker_timeout_floor,
            )
            worker_agent_ids.append(runtime_id)
        max_steps = max(4, int(getattr(spec.policy, "max_steps", 0) or 0))

    if use_openclaw_agent_lifecycle:
        for runtime_id in worker_agent_ids:
            _recreate_openclaw_agent(
                openclaw_bin=config.openclaw_bin,
                agent_id=runtime_id,
                model=config.model,
                workspace=workspace,
            )

    trace_path = run_dir / "traces" / f"{task.task_uid}.run{run_idx:02d}.jsonl"
    started_at = time.time()
    state = None
    runtime_error = ""
    try:
        runtime = GovernanceRuntime(
            spec=spec,
            adapter=adapter,
            store=JsonlStore(trace_path),
        )
        state = runtime.run(
            task_id=f"{task.task_uid}-r{run_idx:02d}",
            title=f"{task.scenario}:{task.task_id}",
            input_text=task_input,
            max_steps=max_steps,
        )
    except Exception as exc:  # noqa: BLE001 - benchmark should continue
        runtime_error = str(exc)

    transcript: list[dict[str, Any]] = []
    if use_openclaw_agent_lifecycle:
        for runtime_id in worker_agent_ids:
            transcript.extend(
                load_latest_openclaw_transcript(
                    agent_id=runtime_id,
                    started_at=started_at,
                )
            )
    elif state is not None:
        transcript.extend(extract_pc_agent_loop_transcript(state.history))

    final_summary = ""
    if state is not None and state.history:
        final_summary = str(state.history[-1].summary or "")

    grade = _grade_task(
        task=task,
        transcript=transcript,
        final_summary=final_summary,
        workspace=workspace,
        adapter=adapter,
        config=config,
        run_dir=run_dir,
        judge_agent_id=judge_agent_id,
    )
    runtime_status = (
        (str(state.status or "error") if state is not None else "error")
        if not runtime_error
        else "error"
    )
    grade = _enforce_runtime_outcome(
        grade=grade,
        runtime_status=runtime_status,
        runtime_error=runtime_error,
    )

    if not config.keep_agents and use_openclaw_agent_lifecycle:
        for runtime_id in worker_agent_ids:
            _delete_openclaw_agent(config.openclaw_bin, runtime_id)

    return {
        "task_uid": task.task_uid,
        "task_id": task.task_id,
        "scenario": task.scenario,
        "coordinate_mode": task.coordinate_mode,
        "run_index": run_idx,
        "execution_mode": "mas-native",
        "runtime_status": runtime_status,
        "runtime_error": runtime_error,
        "steps": (len(state.history) if state is not None else 0),
        "score": grade.score,
        "max_score": grade.max_score,
        "score_ratio": (grade.score / grade.max_score if grade.max_score > 0 else 0.0),
        "grade_breakdown": grade.breakdown,
        "grade_notes": grade.notes,
        "trace_path": str(trace_path.resolve()),
        "workspace": str(workspace.resolve()),
        "worker_agents": list(worker_agent_ids),
        "transcript_events": len(transcript),
        "final_summary": final_summary,
        "history": (
            [
                {
                    "idx": e.index,
                    "stage": e.stage_id,
                    "decision": e.decision,
                    "next": e.next_stage,
                    "summary": e.summary,
                }
                for e in state.history
            ]
            if state is not None
            else []
        ),
    }


def _run_multiagentbench_marble_mode(
    config: MultiAgentBenchRunConfig,
    selected_tasks: list[MultiAgentBenchTask],
    run_dir: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mab_root = config.mab_root.expanduser().resolve()

    for task in selected_tasks:
        for run_idx in range(1, max(1, int(config.runs)) + 1):
            row = _run_single_task_marble(
                task=task,
                run_idx=run_idx,
                config=config,
                run_dir=run_dir,
                mab_root=mab_root,
            )
            rows.append(row)
            _LOG.info(
                "mab-native scenario=%s task=%s run=%s status=%s score=%.3f",
                task.scenario,
                task.task_id,
                run_idx,
                row.get("runtime_status"),
                float(row.get("score", 0.0)),
            )
    return rows


def _run_single_task_marble(
    task: MultiAgentBenchTask,
    run_idx: int,
    config: MultiAgentBenchRunConfig,
    run_dir: Path,
    mab_root: Path,
) -> dict[str, Any]:
    workspace = run_dir / "workspaces" / task.task_uid / f"run_{run_idx:02d}"
    _prepare_workspace(task=task, workspace=workspace)

    cfg = _build_marble_config(task=task, workspace=workspace, config=config)
    cfg_path = workspace / "marble_task.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    output_file = Path(str(cfg.get("output", {}).get("file_path", "")).strip() or "")
    if not output_file.is_absolute():
        output_file = (mab_root / output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    command = [
        str(config.marble_python_bin or "python"),
        "marble/main.py",
        "--config_path",
        str(cfg_path.resolve()),
    ]
    proc = subprocess.run(
        command,
        cwd=str(mab_root),
        check=False,
        capture_output=True,
        text=True,
    )
    runtime_error = ""
    runtime_status = "done" if proc.returncode == 0 else "error"
    if proc.returncode != 0:
        runtime_error = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()[-1200:]

    payload = _load_latest_json_line(output_file)
    grade = _grade_marble_payload(task=task, payload=payload, raw_output=(proc.stdout or "") + "\n" + (proc.stderr or ""))
    grade = _enforce_runtime_outcome(
        grade=grade,
        runtime_status=runtime_status,
        runtime_error=runtime_error,
    )

    return {
        "task_uid": task.task_uid,
        "task_id": task.task_id,
        "scenario": task.scenario,
        "coordinate_mode": task.coordinate_mode,
        "run_index": run_idx,
        "execution_mode": "marble-native",
        "runtime_status": runtime_status,
        "runtime_error": runtime_error,
        "steps": _extract_marble_iterations(payload),
        "score": grade.score,
        "max_score": grade.max_score,
        "score_ratio": (grade.score / grade.max_score if grade.max_score > 0 else 0.0),
        "grade_breakdown": grade.breakdown,
        "grade_notes": grade.notes,
        "trace_path": "",
        "workspace": str(workspace.resolve()),
        "worker_agents": [a.get("agent_id", "") for a in task.agents if isinstance(a, dict)],
        "transcript_events": 0,
        "final_summary": str(payload.get("final_output", "")) if isinstance(payload, dict) else "",
        "history": payload.get("iterations", []) if isinstance(payload, dict) else [],
        "marble_output_file": str(output_file),
        "marble_command": command,
    }


def _grade_task(
    task: MultiAgentBenchTask,
    transcript: list[dict[str, Any]],
    final_summary: str,
    workspace: Path,
    adapter: AgentAdapter,
    config: MultiAgentBenchRunConfig,
    run_dir: Path,
    judge_agent_id: str,
) -> MultiAgentBenchGradeResult:
    if task.scenario == "database":
        auto = grade_multiagent_database(task, transcript, final_summary)
        if config.no_judge or not judge_agent_id:
            return auto
        llm = _grade_llm_judge(
            task=task,
            transcript=transcript,
            final_summary=final_summary,
            adapter=adapter,
            config=config,
            run_dir=run_dir,
            judge_agent_id=judge_agent_id,
        )
        if _judge_failed(llm):
            return _fallback_to_automated(
                automated=auto,
                llm=llm,
                grading_type="database_rule_fallback",
            )
        return _combine_scores(
            task=task,
            automated=auto,
            llm=llm,
            automated_weight=0.7,
            llm_weight=0.3,
            grading_type="database_hybrid",
        )

    if task.scenario == "coding":
        auto = _grade_coding_automated(task, transcript, workspace)
        if config.no_judge or not judge_agent_id:
            return auto
        llm = _grade_llm_judge(
            task=task,
            transcript=transcript,
            final_summary=final_summary,
            adapter=adapter,
            config=config,
            run_dir=run_dir,
            judge_agent_id=judge_agent_id,
        )
        if _judge_failed(llm):
            return _fallback_to_automated(
                automated=auto,
                llm=llm,
                grading_type="coding_automated_fallback",
            )
        return _combine_scores(
            task=task,
            automated=auto,
            llm=llm,
            automated_weight=0.4,
            llm_weight=0.6,
            grading_type="coding_hybrid",
        )

    if config.no_judge or not judge_agent_id:
        return _grade_activity_automated(task, transcript, final_summary)

    llm = _grade_llm_judge(
        task=task,
        transcript=transcript,
        final_summary=final_summary,
        adapter=adapter,
        config=config,
        run_dir=run_dir,
        judge_agent_id=judge_agent_id,
    )
    if _judge_failed(llm):
        auto = _grade_activity_automated(task, transcript, final_summary)
        return _fallback_to_automated(
            automated=auto,
            llm=llm,
            grading_type="activity_automated_fallback",
        )
    return llm


def _grade_activity_automated(
    task: MultiAgentBenchTask,
    transcript: list[dict[str, Any]],
    final_summary: str,
) -> MultiAgentBenchGradeResult:
    text = (final_summary or "") + "\n" + _extract_text_from_transcript(transcript)
    has_output = len(text.strip()) > 20
    has_tools = "toolcall" in text.lower() or "tool_call" in text.lower()
    score = 0.0
    if has_output:
        score += 0.7
    if has_tools:
        score += 0.3
    score = clip01(score)
    breakdown = {
        "activity.has_output": 1.0 if has_output else 0.0,
        "activity.has_tools": 1.0 if has_tools else 0.0,
    }
    return MultiAgentBenchGradeResult(
        task_uid=task.task_uid,
        scenario=task.scenario,
        grading_type="activity_automated",
        score=score,
        max_score=1.0,
        breakdown=breakdown,
        notes="fallback automated grading (judge skipped)",
    )


def _grade_coding_automated(
    task: MultiAgentBenchTask,
    transcript: list[dict[str, Any]],
    workspace: Path,
) -> MultiAgentBenchGradeResult:
    py_files = [p for p in workspace.rglob("*.py") if p.is_file()]
    non_empty_py = [p for p in py_files if p.stat().st_size > 0]
    wrote_file = bool(non_empty_py)

    transcript_text = _extract_text_from_transcript(transcript).lower()
    touched_code = any(
        k in transcript_text
        for k in ["write_file", "solution.py", "python", "execute_command"]
    )

    score = 0.0
    if wrote_file:
        score += 0.7
    if touched_code:
        score += 0.3
    score = clip01(score)
    breakdown = {
        "coding.file_created": 1.0 if wrote_file else 0.0,
        "coding.code_related_activity": 1.0 if touched_code else 0.0,
    }
    return MultiAgentBenchGradeResult(
        task_uid=task.task_uid,
        scenario=task.scenario,
        grading_type="coding_automated",
        score=score,
        max_score=1.0,
        breakdown=breakdown,
        notes=f"python_files={len(non_empty_py)}",
    )


def _grade_llm_judge(
    task: MultiAgentBenchTask,
    transcript: list[dict[str, Any]],
    final_summary: str,
    adapter: AgentAdapter,
    config: MultiAgentBenchRunConfig,
    run_dir: Path,
    judge_agent_id: str,
) -> MultiAgentBenchGradeResult:
    prompt = _build_judge_prompt(task=task, transcript=transcript, final_summary=final_summary)
    try:
        result = adapter.dispatch(
            runtime_id=judge_agent_id,
            message=prompt,
            timeout_sec=max(30, int(config.judge_timeout_sec)),
            retries=1,
        )
    except Exception as exc:  # noqa: BLE001
        return MultiAgentBenchGradeResult(
            task_uid=task.task_uid,
            scenario=task.scenario,
            grading_type="llm_judge",
            score=0.0,
            max_score=1.0,
            breakdown={},
            notes=f"judge dispatch failed: {exc}",
        )

    parsed = parse_judge_payload(result.raw_output or result.summary or "")
    scores = _normalize_scores(
        parsed.get("scores", parsed.get("criteria_scores", {}))
        if isinstance(parsed, dict)
        else {}
    )
    total_raw = parsed.get("total", parsed.get("score")) if isinstance(parsed, dict) else None
    if not isinstance(total_raw, (int, float)) and not scores:
        return MultiAgentBenchGradeResult(
            task_uid=task.task_uid,
            scenario=task.scenario,
            grading_type="llm_judge",
            score=0.0,
            max_score=1.0,
            breakdown={},
            notes="judge parse failed: missing score fields",
        )
    if not isinstance(total_raw, (int, float)):
        total = average(list(scores.values()))
    else:
        total = float(total_raw)
    notes = ""
    if isinstance(parsed, dict):
        notes = str(parsed.get("notes", parsed.get("justification", "")))
    return MultiAgentBenchGradeResult(
        task_uid=task.task_uid,
        scenario=task.scenario,
        grading_type="llm_judge",
        score=clip01(float(total or 0.0)),
        max_score=1.0,
        breakdown=scores,
        notes=notes,
    )


def _judge_failed(grade: MultiAgentBenchGradeResult) -> bool:
    notes = str(grade.notes or "").strip().lower()
    if "judge dispatch failed" in notes:
        return True
    if "judge parse failed" in notes:
        return True
    return False


def _runtime_is_done(runtime_status: str) -> bool:
    return str(runtime_status or "").strip().lower() in {"done", "completed", "success"}


def _enforce_runtime_outcome(
    grade: MultiAgentBenchGradeResult,
    runtime_status: str,
    runtime_error: str,
) -> MultiAgentBenchGradeResult:
    if _runtime_is_done(runtime_status):
        return grade

    breakdown = dict(grade.breakdown)
    breakdown["runtime.ok"] = 0.0
    notes_parts = [f"runtime_not_done: status={str(runtime_status or '').strip() or 'unknown'}"]
    err = str(runtime_error or "").strip()
    if err:
        notes_parts.append(f"runtime_error={err[:240]}")
    if str(grade.notes or "").strip():
        notes_parts.append(str(grade.notes or "").strip())

    return MultiAgentBenchGradeResult(
        task_uid=grade.task_uid,
        scenario=grade.scenario,
        grading_type=f"{grade.grading_type}_runtime_guard",
        score=0.0,
        max_score=(grade.max_score if float(grade.max_score) > 0 else 1.0),
        breakdown=breakdown,
        notes=" | ".join(notes_parts),
    )


def _fallback_to_automated(
    automated: MultiAgentBenchGradeResult,
    llm: MultiAgentBenchGradeResult,
    grading_type: str,
) -> MultiAgentBenchGradeResult:
    auto_notes = str(automated.notes or "").strip()
    llm_notes = str(llm.notes or "").strip()
    notes = " | ".join(x for x in [auto_notes, f"llm_judge_failed: {llm_notes}"] if x)
    return MultiAgentBenchGradeResult(
        task_uid=automated.task_uid,
        scenario=automated.scenario,
        grading_type=grading_type,
        score=automated.score,
        max_score=automated.max_score,
        breakdown=dict(automated.breakdown),
        notes=notes,
    )


def _combine_scores(
    task: MultiAgentBenchTask,
    automated: MultiAgentBenchGradeResult,
    llm: MultiAgentBenchGradeResult,
    automated_weight: float,
    llm_weight: float,
    grading_type: str,
) -> MultiAgentBenchGradeResult:
    w_auto = float(automated_weight)
    w_llm = float(llm_weight)
    total_w = w_auto + w_llm
    if total_w <= 0:
        w_auto, w_llm, total_w = 0.5, 0.5, 1.0
    score = ((automated.score * w_auto) + (llm.score * w_llm)) / total_w
    breakdown = {
        **{f"automated.{k}": v for k, v in automated.breakdown.items()},
        **{f"llm_judge.{k}": v for k, v in llm.breakdown.items()},
    }
    notes = " | ".join(x for x in [automated.notes, llm.notes] if x.strip())
    return MultiAgentBenchGradeResult(
        task_uid=task.task_uid,
        scenario=task.scenario,
        grading_type=grading_type,
        score=clip01(score),
        max_score=1.0,
        breakdown=breakdown,
        notes=notes,
    )


def _build_summary(
    rows: list[dict[str, Any]],
    run_dir: Path,
    config: MultiAgentBenchRunConfig,
    selected: list[MultiAgentBenchTask],
) -> dict[str, Any]:
    per_task: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        per_task.setdefault(str(row["task_uid"]), []).append(row)

    by_task: list[dict[str, Any]] = []
    for task in selected:
        group = per_task.get(task.task_uid, [])
        if not group:
            continue
        scores = [float(x.get("score", 0.0)) for x in group]
        by_task.append(
            {
                "task_uid": task.task_uid,
                "task_id": task.task_id,
                "scenario": task.scenario,
                "coordinate_mode": task.coordinate_mode,
                "runs": len(group),
                "avg_score": average(scores),
                "best_score": max(scores),
                "worst_score": min(scores),
                "status_counts": count_by(group, "runtime_status"),
            }
        )

    by_scenario: list[dict[str, Any]] = []
    scenario_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        scenario_groups.setdefault(str(row.get("scenario", "")), []).append(row)
    for scenario, group in sorted(scenario_groups.items()):
        scores = [float(x.get("score", 0.0)) for x in group]
        by_scenario.append(
            {
                "scenario": scenario,
                "runs": len(group),
                "avg_score": average(scores),
                "status_counts": count_by(group, "runtime_status"),
            }
        )

    overall_score = average([float(x.get("score", 0.0)) for x in rows])
    return {
        "benchmark": "MultiAgentBench",
        "run_dir": str(run_dir.resolve()),
        "execution_mode": config.execution_mode,
        "model": config.model,
        "adapter": config.adapter,
        "mab_root": str(config.mab_root.expanduser().resolve()),
        "scenario": config.scenario,
        "suite": config.suite,
        "runs_per_task": max(1, int(config.runs)),
        "selected_tasks": len(selected),
        "executed_runs": len(rows),
        "overall_score": overall_score,
        "status_counts": count_by(rows, "runtime_status"),
        "by_scenario": by_scenario,
        "by_task": by_task,
        "results_jsonl": str((run_dir / "results" / "details.jsonl").resolve()),
        "summary_json": str((run_dir / "results" / "summary.json").resolve()),
    }


def _normalize_task_payload(
    *,
    payload: dict[str, Any],
    scenario: str,
    task_id: int,
    source_file: Path,
    default_model: str,
) -> MultiAgentBenchTask:
    raw = copy.deepcopy(payload)
    scenario_key = scenario if scenario in _SCENARIO_DEFAULTS else "research"
    defaults = _SCENARIO_DEFAULTS[scenario_key]

    coordinate_mode = str(raw.get("coordinate_mode", "") or defaults["coordinate_mode"]).strip() or defaults[
        "coordinate_mode"
    ]

    llm = str(raw.get("llm", "") or default_model or "gpt-4o-mini").strip()

    env = raw.get("environment") if isinstance(raw.get("environment"), dict) else {}
    env = dict(env)
    for k, v in defaults["environment"].items():
        cur = env.get(k)
        if k not in env or cur is None or (isinstance(cur, str) and not cur.strip()):
            env[k] = v

    memory = raw.get("memory") if isinstance(raw.get("memory"), dict) else {}
    memory = dict(memory)
    if not str(memory.get("type", "")).strip():
        memory["type"] = defaults["memory"]["type"]

    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    metrics = dict(metrics)
    eval_llm = metrics.get("evaluate_llm")
    if not isinstance(eval_llm, str) or not eval_llm.strip():
        metrics["evaluate_llm"] = llm

    output = raw.get("output") if isinstance(raw.get("output"), dict) else {}
    output = dict(output)
    if not str(output.get("file_path", "")).strip():
        output["file_path"] = defaults["output"]["file_path"]

    relationships_raw = raw.get("relationships")
    relationships: list[list[str]] = []
    if isinstance(relationships_raw, list):
        for item in relationships_raw:
            if isinstance(item, list):
                relationships.append([str(x) for x in item])

    agents_raw = raw.get("agents")
    agents: list[dict[str, Any]] = []
    if isinstance(agents_raw, list):
        for idx, item in enumerate(agents_raw, start=1):
            if not isinstance(item, dict):
                continue
            agent = dict(item)
            if not str(agent.get("agent_id", "")).strip():
                agent["agent_id"] = f"agent_{idx}"
            if not str(agent.get("llm", "")).strip():
                agent["llm"] = llm
            agents.append(agent)

    task = raw.get("task") if isinstance(raw.get("task"), dict) else {}
    prompt = str(task.get("content", "")).strip()
    output_format = str(task.get("output_format", "")).strip()

    labels = [str(x).strip() for x in task.get("labels", [])] if isinstance(task.get("labels"), list) else []
    root_causes = (
        [str(x).strip() for x in task.get("root_causes", [])]
        if isinstance(task.get("root_causes"), list)
        else []
    )
    number_of_labels_pred = _coerce_int(task.get("number_of_labels_pred"), default=0)

    task_uid = f"{scenario}:{task_id:03d}"
    return MultiAgentBenchTask(
        scenario=scenario,
        task_id=task_id,
        task_uid=task_uid,
        coordinate_mode=coordinate_mode,
        relationships=relationships,
        agents=agents,
        llm=llm,
        environment=env,
        memory=memory,
        metrics=metrics,
        engine_planner=(
            raw.get("engine_planner")
            if isinstance(raw.get("engine_planner"), dict)
            else {"initial_progress": "Starting the simulation."}
        ),
        output=output,
        prompt=prompt,
        output_format=output_format,
        labels=labels,
        root_causes=root_causes,
        number_of_labels_pred=number_of_labels_pred,
        source_file=str(source_file.resolve()),
        raw_payload=raw,
    )


def _prepare_workspace(task: MultiAgentBenchTask, workspace: Path) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "task.json").write_text(
        json.dumps(task.raw_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (workspace / "TASK.md").write_text(
        f"# {task.task_uid}\n\n"
        f"Scenario: {task.scenario}\n"
        f"Coordinate mode: {task.coordinate_mode}\n\n"
        f"## Prompt\n{task.prompt}\n\n"
        f"## Expected Output Format\n{task.output_format or '(not specified)'}\n",
        encoding="utf-8",
    )


def _build_task_spec(
    task: MultiAgentBenchTask,
    runtime_id: str,
    workspace: Path,
    worker_timeout_sec: int = 0,
):
    timeout_sec = max(60, int(task.environment.get("max_iterations", 5)) * 60, max(0, int(worker_timeout_sec)))
    prompt = _build_worker_prompt(task, workspace)
    raw = {
        "meta": {
            "id": f"mab_{task.scenario}_{task.task_id}",
            "name": f"MultiAgentBench {task.task_uid}",
            "version": "0.1.0",
            "pattern": "pipeline",
            "description": f"MultiAgentBench task {task.task_uid}",
        },
        "entry_stage": "execute",
        "agents": {
            "worker": {
                "runtime_id": runtime_id,
                "role": "executor",
                "timeout_sec": timeout_sec,
            }
        },
        "stages": [
            {
                "id": "execute",
                "kind": "executor",
                "agent": "worker",
                "prompt_template": prompt,
                "transitions": [
                    {"decision": "next", "to": "completed"},
                    {"decision": "default", "to": "completed"},
                ],
            },
            {"id": "completed", "kind": "terminal"},
        ],
        "features": [
            {"name": "monitor", "enabled": True, "config": {}},
            {"name": "shared_state", "enabled": True, "config": {}},
        ],
        "policy": {
            "require_json_decision": False,
            "max_steps": max(4, int(task.environment.get("max_iterations", 5)) + 2),
        },
    }
    return compile_spec_obj(raw)


def _build_worker_prompt(task: MultiAgentBenchTask, workspace: Path) -> str:
    agent_lines = _format_agent_lines(task)
    output_format = task.output_format.strip() or "Produce a concise final deliverable matching the task intent."
    return (
        "You are solving a MultiAgentBench task through tools in your runtime environment.\n"
        f"Task UID: {task.task_uid}\n"
        f"Scenario: {task.scenario}\n"
        f"Coordinate mode (reference): {task.coordinate_mode}\n"
        f"Workspace path: {workspace}\n\n"
        "[Scenario Agents Reference]\n"
        f"{agent_lines}\n\n"
        "[User Task]\n"
        f"{task.prompt.strip()}\n\n"
        "[Expected Output Format]\n"
        f"{output_format}\n\n"
        "Execution requirements:\n"
        "- Use tools/filesystem actions when useful and create concrete artifacts in workspace.\n"
        "- Do not stop at planning; finish deliverables.\n"
        "- Final answer must be valid JSON only:\n"
        '{"decision":"next","summary":"what you completed","updates":{"artifacts":[]}}'
    )


def _build_task_input(task: MultiAgentBenchTask, workspace: Path) -> str:
    agent_lines = _format_agent_lines(task)
    output_format = task.output_format.strip() or "(not specified)"
    return (
        f"MultiAgentBench task_uid={task.task_uid}\n"
        f"scenario={task.scenario}\n"
        f"coordinate_mode={task.coordinate_mode}\n"
        f"workspace={workspace}\n\n"
        "[Scenario Agents Reference]\n"
        f"{agent_lines}\n\n"
        "[User Task]\n"
        f"{task.prompt.strip()}\n\n"
        "[Expected Output Format]\n"
        f"{output_format}\n\n"
        "Execution constraints:\n"
        "- Complete real tool/file operations in workspace when needed.\n"
        "- Prefer concrete outputs over process-only narration.\n"
    )


def _build_judge_prompt(
    task: MultiAgentBenchTask,
    transcript: list[dict[str, Any]],
    final_summary: str,
) -> str:
    rubric = _default_judge_rubric(task)
    return (
        "You are a strict benchmark grader.\n"
        "Return a single JSON object only, no markdown.\n\n"
        "[Scenario]\n"
        f"{task.scenario}\n\n"
        "[Task Prompt]\n"
        f"{task.prompt.strip()}\n\n"
        "[Expected Output Format]\n"
        f"{(task.output_format.strip() or '(not specified)')}\n\n"
        "[Final Summary]\n"
        f"{final_summary.strip()}\n\n"
        "[Transcript Summary]\n"
        f"{_summarize_transcript(transcript)}\n\n"
        "[Rubric]\n"
        f"{rubric}\n\n"
        "Output schema:\n"
        '{"scores":{"task_completion":0.0,"collaboration":0.0,"format":0.0},"total":0.0,"notes":"brief justification"}'
    )


def _format_agent_lines(task: MultiAgentBenchTask) -> str:
    lines: list[str] = []
    for agent in task.agents:
        if not isinstance(agent, dict):
            continue
        aid = str(agent.get("agent_id", "")).strip() or "agent"
        role = str(agent.get("role", "")).strip()
        profile = str(agent.get("profile", "")).strip().replace("\n", " ")
        if len(profile) > 160:
            profile = profile[:157] + "..."
        seg = f"- {aid}"
        if role:
            seg += f" ({role})"
        if profile:
            seg += f": {profile}"
        lines.append(seg)
    return "\n".join(lines) if lines else "- (no explicit agent profile in source task)"


def _summarize_transcript(transcript: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for evt in transcript:
        if not isinstance(evt, dict):
            continue
        if evt.get("type") != "message":
            continue
        msg = evt.get("message", {})
        role = str(msg.get("role", ""))
        content = msg.get("content", [])
        if role == "assistant":
            for item in content if isinstance(content, list) else []:
                if isinstance(item, dict) and item.get("type") == "toolCall":
                    name = str(item.get("name", ""))
                    args = item.get("arguments")
                    if not isinstance(args, dict):
                        args = item.get("params", {})
                    rows.append(f"tool_call:{name} args={json.dumps(args, ensure_ascii=False)}")
                elif isinstance(item, dict) and item.get("type") == "text":
                    rows.append(f"assistant_text:{str(item.get('text', ''))[:200]}")
        elif role == "toolResult":
            rows.append(f"tool_result:{str(content)[:240]}")
        elif role == "user":
            rows.append(f"user:{str(content)[:240]}")
    if not rows:
        return "(no transcript events captured)"
    return "\n".join(rows[:200])


def _default_judge_rubric(task: MultiAgentBenchTask) -> str:
    scenario = task.scenario
    if scenario == "research":
        return "- Task completion quality of the proposed 5q research idea\n- Collaboration depth and diversity of perspectives\n- Format adherence to requested structure"
    if scenario == "bargaining":
        return "- Negotiation progression and coherence\n- Multi-agent interaction quality\n- Output format and clarity"
    if scenario == "coding":
        return "- Task requirement coverage\n- Executability and code quality\n- Output format and artifact completeness"
    if scenario == "database":
        return "- Correct diagnosis and root cause reasoning\n- Use of evidence from analysis steps\n- Output precision and label correctness"
    if scenario == "minecraft":
        return "- Task completion toward in-game objective\n- Coordination quality\n- Output clarity"
    return "- Task completion\n- Collaboration quality\n- Output format correctness"


def _build_marble_config(
    task: MultiAgentBenchTask,
    workspace: Path,
    config: MultiAgentBenchRunConfig,
) -> dict[str, Any]:
    cfg = copy.deepcopy(task.raw_payload)
    cfg["coordinate_mode"] = task.coordinate_mode
    cfg["relationships"] = copy.deepcopy(task.relationships)
    cfg["agents"] = copy.deepcopy(task.agents)
    cfg["memory"] = copy.deepcopy(task.memory)
    cfg["environment"] = copy.deepcopy(task.environment)
    cfg["task"] = cfg.get("task") if isinstance(cfg.get("task"), dict) else {}
    cfg["metrics"] = cfg.get("metrics") if isinstance(cfg.get("metrics"), dict) else {}
    cfg["engine_planner"] = (
        cfg.get("engine_planner")
        if isinstance(cfg.get("engine_planner"), dict)
        else {"initial_progress": "Starting the simulation."}
    )
    cfg["output"] = cfg.get("output") if isinstance(cfg.get("output"), dict) else {}

    model = (config.model or task.llm or "gpt-4o-mini").strip()
    cfg["llm"] = model

    metrics = cfg["metrics"]
    eval_llm = metrics.get("evaluate_llm")
    if not isinstance(eval_llm, str) or not eval_llm.strip():
        metrics["evaluate_llm"] = (config.judge_model or model)

    if task.scenario == "coding":
        env = cfg["environment"]
        if not isinstance(env, dict):
            env = {}
            cfg["environment"] = env
        env["workspace_dir"] = str(workspace.resolve())

    output = cfg["output"]
    out_file = workspace / "marble_result.jsonl"
    output["file_path"] = str(out_file.resolve())

    return cfg


def _grade_marble_payload(
    task: MultiAgentBenchTask,
    payload: dict[str, Any],
    raw_output: str,
) -> MultiAgentBenchGradeResult:
    if not isinstance(payload, dict) or not payload:
        return MultiAgentBenchGradeResult(
            task_uid=task.task_uid,
            scenario=task.scenario,
            grading_type="marble_native",
            score=0.0,
            max_score=1.0,
            breakdown={},
            notes=f"empty marble payload; output_tail={raw_output[-320:]}",
        )

    task_eval_score, task_eval_breakdown = _score_from_marble_task_evaluation(payload.get("task_evaluation"))

    planning_scores = _normalize_numeric_list(payload.get("planning_scores"))
    comm_scores = _normalize_numeric_list(payload.get("communication_scores"))

    planning = average([clip01(x / 5.0 if x > 1 else x) for x in planning_scores])
    comm = average([clip01(x / 5.0 if x > 1 else x) for x in comm_scores])

    final = clip01((task_eval_score * 0.7) + (planning * 0.2) + (comm * 0.1))
    breakdown = {
        "marble.task_eval": task_eval_score,
        "marble.planning": planning,
        "marble.communication": comm,
        **task_eval_breakdown,
    }

    return MultiAgentBenchGradeResult(
        task_uid=task.task_uid,
        scenario=task.scenario,
        grading_type="marble_native",
        score=final,
        max_score=1.0,
        breakdown=breakdown,
        notes="score normalized from MARBLE output payload",
    )


def _score_from_marble_task_evaluation(task_eval: Any) -> tuple[float, dict[str, float]]:
    if isinstance(task_eval, (int, float)):
        score = clip01(float(task_eval) / 5.0 if float(task_eval) > 1 else float(task_eval))
        return score, {"marble.task_eval.raw": score}

    if isinstance(task_eval, dict):
        flat_vals: list[float] = []
        for v in task_eval.values():
            if isinstance(v, (int, float)):
                flat_vals.append(float(v))
            elif isinstance(v, dict):
                for vv in v.values():
                    if isinstance(vv, (int, float)):
                        flat_vals.append(float(vv))
        if flat_vals:
            norm = [clip01(x / 5.0 if x > 1 else x) for x in flat_vals]
            return average(norm), {"marble.task_eval.avg": average(norm)}

    return 0.0, {"marble.task_eval.avg": 0.0}


def _load_latest_json_line(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8").splitlines()
    for line in reversed(text):
        src = line.strip()
        if not src:
            continue
        try:
            obj = json.loads(src)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


def _normalize_numeric_list(raw: Any) -> list[float]:
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for x in raw:
        try:
            out.append(float(x))
        except (TypeError, ValueError):
            continue
    return out


def _extract_marble_iterations(payload: dict[str, Any]) -> int:
    if not isinstance(payload, dict):
        return 0
    rows = payload.get("iterations")
    if isinstance(rows, list):
        return len(rows)
    return 0


def _extract_text_from_transcript(transcript: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for evt in transcript:
        if not isinstance(evt, dict):
            continue
        msg = evt.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            rows.append(content)
            continue
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        rows.append(str(item.get("text", "")))
                    elif "name" in item:
                        rows.append(str(item.get("name", "")))
                else:
                    rows.append(str(item))
    return "\n".join(rows)


def _normalize_scores(raw: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = clip01(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _requires_judge(tasks: list[MultiAgentBenchTask]) -> bool:
    return any(t.scenario in {"research", "bargaining", "coding", "minecraft", "database"} for t in tasks)


def _resolve_spec_path(raw: str | Path) -> Path:
    src = Path(raw).expanduser()
    if not src.is_absolute():
        src = (Path.cwd() / src).resolve()
    else:
        src = src.resolve()
    if src.is_file():
        return src
    if not src.is_dir():
        raise FileNotFoundError(f"benchmark spec path not found: {src}")

    candidates = sorted(src.glob("*.yaml")) + sorted(src.glob("*.yml")) + sorted(src.glob("*.json"))
    if not candidates:
        raise FileNotFoundError(
            f"no spec file found under directory: {src} (expected .yaml/.yml/.json)"
        )

    base = src.name.lower().strip()
    for c in candidates:
        if c.stem.lower().strip() == base:
            return c.resolve()
    return candidates[0].resolve()


def _apply_benchmark_stage_objectives(spec: Any, task: MultiAgentBenchTask, workspace: Path) -> None:
    for stage in getattr(spec, "stages", []):
        if getattr(stage, "kind", "") == "terminal":
            continue
        kind = str(getattr(stage, "kind", "")).strip().lower()
        if kind in {"planner", "initiator", "orchestrator"}:
            stage.description = (
                "You are in planning stage. Produce a concise and concrete execution plan for this "
                "MultiAgentBench task, referencing exact filenames and tools. Do not claim completion."
            )
            continue
        if kind == "consensus":
            stage.description = (
                "You are a voter in a consensus stage. Your ONLY task is to evaluate the proposal "
                "and output yes or no. Do NOT use any tools or execute code. "
                'Return JSON: {"decision":"yes","summary":"brief reason"}'
            )
            continue
        if kind in {"gate", "auditor"}:
            continue
        if kind not in {"executor", "cluster"}:
            continue
        stage.description = (
            "You are in execution stage. Execute the task end-to-end using tools and filesystem actions "
            f"in workspace `{workspace}`. Ensure deliverables required by task `{task.task_uid}` are "
            "actually created with correct names/content before responding.\n\n"
            "Tool call format (pc-agent-loop rules):\n"
            "- PREFERRED: use code_run with Python to create files. Write the Python code in a "
            "```python block in your reply body BEFORE the tool call JSON. "
            "Example: ```python\\nimport pathlib\\npathlib.Path('/path/to/file').write_text('content')\\n```\n"
            "- file_write (fallback): put file content in a <file_content>...</file_content> tag "
            "in your reply body BEFORE the tool call JSON. Do NOT put content in JSON parameters.\n"
            "- After writing, verify the file exists with file_read before claiming completion."
        )


def _recreate_openclaw_agent(
    openclaw_bin: str,
    agent_id: str,
    model: str,
    workspace: Path,
) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [openclaw_bin, "agents", "delete", agent_id, "--force"],
        check=False,
        capture_output=True,
        text=True,
    )
    proc = subprocess.run(
        [
            openclaw_bin,
            "agents",
            "add",
            agent_id,
            "--model",
            model,
            "--workspace",
            str(workspace),
            "--non-interactive",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        msg = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
        raise RuntimeError(
            f"failed to create OpenClaw agent '{agent_id}' with model '{model}': {msg[-800:]}"
        )


def _delete_openclaw_agent(openclaw_bin: str, agent_id: str) -> None:
    subprocess.run(
        [openclaw_bin, "agents", "delete", agent_id, "--force"],
        check=False,
        capture_output=True,
        text=True,
    )


def _coerce_task_id(raw: Any, fallback: int) -> int:
    if isinstance(raw, bool):
        return fallback
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    txt = str(raw or "").strip()
    if not txt:
        return fallback
    m = re.search(r"\d+", txt)
    if not m:
        return fallback
    try:
        return int(m.group(0))
    except ValueError:
        return fallback


def _coerce_int(raw: Any, default: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default
