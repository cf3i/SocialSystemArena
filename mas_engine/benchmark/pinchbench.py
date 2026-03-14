"""PinchBench integration powered by MAS runtime."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - guarded in runtime usage
    raise RuntimeError(
        "PinchBench integration requires PyYAML. Install with `pip install pyyaml`."
    ) from exc

from ..adapters import AgentAdapter, OpenClawAdapter, PcAgentLoopAdapter
from ..core.runtime import GovernanceRuntime
from ..spec.compiler import compile_spec, compile_spec_obj
from ..storage.jsonl import JsonlStore

_LOG = logging.getLogger("mas_engine.benchmark.pinchbench")

_TASK_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_SECTION_HEADER_RE = re.compile(r"^##\s+(.+)$")
_CRITERION_RE = re.compile(r"^-\s+\[[ x]\]\s+(.+)$")
_PC_TOOL_MD_RE = re.compile(
    r"\*\*正在调用工具:\*\*\s*`([^`]+)`.*?(?:📥\s*)?\*\*参数:\*\*\s*`{3,4}text\s*(\{.*?\})\s*`{3,4}",
    re.DOTALL,
)
_PC_TOOL_USE_RE = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL | re.IGNORECASE)
_PC_READ_HINT_RE = re.compile(
    r"(?:读取|read(?:ing)?(?:\s+file)?)\s*[`\"']?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)",
    re.IGNORECASE,
)
_PC_WRITE_HINT_RE = re.compile(
    r"(?:写入|保存(?:到)?|write(?:\s+to)?|create(?:d)?)\s*[`\"']?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)",
    re.IGNORECASE,
)


@dataclass
class PinchTask:
    task_id: str
    name: str
    category: str
    grading_type: str
    timeout_seconds: int
    workspace_files: list[dict[str, Any]]
    prompt: str
    expected_behavior: str
    grading_criteria: list[str]
    automated_checks: str = ""
    llm_judge_rubric: str = ""
    grading_weights: dict[str, float] | None = None
    file_path: str = ""


@dataclass
class PinchGradeResult:
    task_id: str
    grading_type: str
    score: float
    max_score: float
    breakdown: dict[str, float]
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "grading_type": self.grading_type,
            "score": self.score,
            "max_score": self.max_score,
            "breakdown": dict(self.breakdown),
            "notes": self.notes,
        }


@dataclass
class PinchBenchRunConfig:
    pinch_root: Path
    model: str
    suite: str = "all"
    runs: int = 1
    output_dir: Path = Path("traces/benchmarks/pinchbench")
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


def run_pinchbench(config: PinchBenchRunConfig) -> dict[str, Any]:
    pinch_root = config.pinch_root.expanduser().resolve()
    tasks_dir = pinch_root / "tasks"
    assets_dir = pinch_root / "assets"
    if not tasks_dir.exists():
        raise FileNotFoundError(f"PinchBench tasks directory not found: {tasks_dir}")

    tasks = load_pinch_tasks(tasks_dir)
    selected_tasks = select_pinch_tasks(tasks, config.suite)
    if not selected_tasks:
        raise ValueError(f"No tasks selected by suite '{config.suite}'")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_out = config.output_dir.expanduser().resolve()
    run_dir = base_out / stamp
    nonce = 1
    while run_dir.exists():
        run_dir = base_out / f"{stamp}-{nonce:02d}"
        nonce += 1
    (run_dir / "traces").mkdir(parents=True, exist_ok=True)
    (run_dir / "workspaces").mkdir(parents=True, exist_ok=True)
    (run_dir / "results").mkdir(parents=True, exist_ok=True)

    adapter, use_openclaw_agent_lifecycle = _build_runtime_adapter(config)

    base_spec = None
    if config.benchmark_spec_path is not None:
        resolved_spec = _resolve_spec_path(config.benchmark_spec_path)
        base_spec = compile_spec(resolved_spec)
        _LOG.info("pinchbench using custom governance spec: %s", resolved_spec)

    judge_agent_id = ""
    judge_workspace = run_dir / "_judge_workspace"
    if _requires_judge(selected_tasks) and not config.no_judge:
        judge_model = (config.judge_model or config.model).strip()
        if not judge_model:
            raise ValueError("judge model is empty")
        judge_agent_id = _build_agent_id("mas-pinch-judge", judge_model, "judge")
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
                row = _run_single_task(
                    task=task,
                    run_idx=run_idx,
                    config=config,
                    adapter=adapter,
                    run_dir=run_dir,
                    assets_dir=assets_dir,
                    judge_agent_id=judge_agent_id,
                    base_spec=base_spec,
                    use_openclaw_agent_lifecycle=use_openclaw_agent_lifecycle,
                )
                rows.append(row)
                _LOG.info(
                    "pinch task=%s run=%s status=%s score=%.3f",
                    task.task_id,
                    run_idx,
                    row.get("runtime_status"),
                    float(row.get("score", 0.0)),
                )
    finally:
        if judge_agent_id and not config.keep_agents and use_openclaw_agent_lifecycle:
            _delete_openclaw_agent(config.openclaw_bin, judge_agent_id)

    summary = _build_summary(rows=rows, run_dir=run_dir, config=config, selected=selected_tasks)
    _write_results(rows=rows, summary=summary, run_dir=run_dir)
    return summary


def _build_runtime_adapter(config: PinchBenchRunConfig) -> tuple[AgentAdapter, bool]:
    mode = str(config.adapter or "openclaw").strip().lower()
    if mode == "openclaw":
        return (
            OpenClawAdapter(
                executable=config.openclaw_bin,
                deliver_mode=config.openclaw_deliver_mode,
                project_dir=config.openclaw_project_dir,
            ),
            True,
        )
    if mode == "pc-agent-loop":
        return (
            PcAgentLoopAdapter(
                agent_root=config.pc_agent_root,
                shared_instance=bool(config.pc_shared_instance),
                llm_no=config.pc_llm_no,
                mykey_path=config.pc_mykey,
            ),
            False,
        )
    raise ValueError(
        f"unsupported pinchbench adapter '{config.adapter}', expected openclaw or pc-agent-loop"
    )


def load_pinch_tasks(tasks_dir: str | Path) -> list[PinchTask]:
    root = Path(tasks_dir).expanduser().resolve()
    files = sorted(root.glob("task_*.md"))
    out: list[PinchTask] = []
    for path in files:
        out.append(_load_single_task(path))
    return out


def select_pinch_tasks(tasks: list[PinchTask], suite: str) -> list[PinchTask]:
    mode = str(suite or "all").strip().lower()
    if mode == "all":
        return list(tasks)
    if mode == "automated-only":
        return [t for t in tasks if t.grading_type == "automated"]

    ids = {x.strip() for x in str(suite).split(",") if x.strip()}
    return [t for t in tasks if t.task_id in ids]


def grade_pinch_task_automated(
    task: PinchTask,
    transcript: list[dict[str, Any]],
    workspace_path: str | Path,
) -> PinchGradeResult:
    code = _extract_python_code(task.automated_checks)
    if not code:
        return PinchGradeResult(
            task_id=task.task_id,
            grading_type="automated",
            score=0.0,
            max_score=1.0,
            breakdown={},
            notes="automated checks missing",
        )

    namespace: dict[str, Any] = {}
    exec(code, namespace)
    fn = namespace.get("grade")
    if not callable(fn):
        return PinchGradeResult(
            task_id=task.task_id,
            grading_type="automated",
            score=0.0,
            max_score=1.0,
            breakdown={},
            notes="grade function missing",
        )

    try:
        raw = fn(transcript, str(Path(workspace_path).expanduser().resolve()))
    except Exception as exc:  # noqa: BLE001 - grading should not crash whole run
        return PinchGradeResult(
            task_id=task.task_id,
            grading_type="automated",
            score=0.0,
            max_score=1.0,
            breakdown={},
            notes=f"automated grading failed: {exc}",
        )

    if not isinstance(raw, dict):
        raw = {}
    breakdown = _normalize_scores(raw)
    score = _average(list(breakdown.values()))
    return PinchGradeResult(
        task_id=task.task_id,
        grading_type="automated",
        score=score,
        max_score=1.0,
        breakdown=breakdown,
    )


def _run_single_task(
    task: PinchTask,
    run_idx: int,
    config: PinchBenchRunConfig,
    adapter: AgentAdapter,
    run_dir: Path,
    assets_dir: Path,
    judge_agent_id: str,
    base_spec: Any = None,
    use_openclaw_agent_lifecycle: bool = True,
) -> dict[str, Any]:
    workspace = run_dir / "workspaces" / task.task_id / f"run_{run_idx:02d}"
    _prepare_workspace(task=task, workspace=workspace, assets_dir=assets_dir)

    worker_timeout_floor = max(0, int(config.worker_timeout_sec or 0))
    task_input = task.prompt
    max_steps = 4
    worker_agent_ids: list[str] = []
    if base_spec is None:
        worker_agent_ids.append(
            _build_agent_id("mas-pinch-worker", config.model, f"{task.task_id}-{run_idx}")
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
        task_input = _build_task_input(task=task, workspace=workspace)
        for agent_key, agent in sorted(spec.agents.items()):
            runtime_id = _build_agent_id(
                "mas-pinch-worker",
                config.model,
                f"{task.task_id}-{run_idx}-{agent_key}",
            )
            agent.runtime_id = runtime_id
            agent.timeout_sec = max(
                int(getattr(agent, "timeout_sec", 300)),
                int(task.timeout_seconds),
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

    trace_path = run_dir / "traces" / f"{task.task_id}.run{run_idx:02d}.jsonl"
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
            task_id=f"{task.task_id}-{run_idx:02d}",
            title=task.name,
            input_text=task_input,
            max_steps=max_steps,
        )
    except Exception as exc:  # noqa: BLE001 - benchmark should continue
        runtime_error = str(exc)

    transcript: list[dict[str, Any]] = []
    if use_openclaw_agent_lifecycle:
        for runtime_id in worker_agent_ids:
            transcript.extend(
                _load_latest_openclaw_transcript(
                    agent_id=runtime_id,
                    started_at=started_at,
                )
            )
    elif state is not None:
        transcript.extend(_extract_pc_agent_loop_transcript(state.history))

    grade = _grade_task(
        task=task,
        transcript=transcript,
        workspace=workspace,
        adapter=adapter,
        config=config,
        run_dir=run_dir,
        judge_agent_id=judge_agent_id,
    )

    if not config.keep_agents and use_openclaw_agent_lifecycle:
        for runtime_id in worker_agent_ids:
            _delete_openclaw_agent(config.openclaw_bin, runtime_id)

    return {
        "task_id": task.task_id,
        "task_name": task.name,
        "category": task.category,
        "grading_type": task.grading_type,
        "run_index": run_idx,
        "runtime_status": (
            (state.status if state is not None else "error")
            if not runtime_error
            else "error"
        ),
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


def _grade_task(
    task: PinchTask,
    transcript: list[dict[str, Any]],
    workspace: Path,
    adapter: AgentAdapter,
    config: PinchBenchRunConfig,
    run_dir: Path,
    judge_agent_id: str,
) -> PinchGradeResult:
    grading_type = task.grading_type
    normalized_transcript = _normalize_transcript_for_grading(transcript)
    if grading_type == "automated":
        return grade_pinch_task_automated(task, normalized_transcript, workspace)

    if grading_type == "llm_judge":
        if config.no_judge or not judge_agent_id:
            return PinchGradeResult(
                task_id=task.task_id,
                grading_type="llm_judge",
                score=0.0,
                max_score=1.0,
                breakdown={},
                notes="judge skipped (--no-judge)",
            )
        return _grade_llm_judge(
            task=task,
            transcript=transcript,
            adapter=adapter,
            config=config,
            run_dir=run_dir,
            judge_agent_id=judge_agent_id,
        )

    if grading_type == "hybrid":
        auto = grade_pinch_task_automated(task, normalized_transcript, workspace)
        if config.no_judge or not judge_agent_id:
            auto.notes = (auto.notes + " | judge skipped (--no-judge)").strip(" |")
            return auto
        llm = _grade_llm_judge(
            task=task,
            transcript=transcript,
            adapter=adapter,
            config=config,
            run_dir=run_dir,
            judge_agent_id=judge_agent_id,
        )
        return _combine_hybrid_scores(task=task, automated=auto, llm=llm)

    return PinchGradeResult(
        task_id=task.task_id,
        grading_type=grading_type,
        score=0.0,
        max_score=1.0,
        breakdown={},
        notes=f"unsupported grading_type '{grading_type}'",
    )


def _grade_llm_judge(
    task: PinchTask,
    transcript: list[dict[str, Any]],
    adapter: AgentAdapter,
    config: PinchBenchRunConfig,
    run_dir: Path,
    judge_agent_id: str,
) -> PinchGradeResult:
    rubric = task.llm_judge_rubric.strip() or _format_criteria(task.grading_criteria)
    prompt = _build_judge_prompt(task=task, transcript=transcript, rubric=rubric)
    try:
        result = adapter.dispatch(
            runtime_id=judge_agent_id,
            message=prompt,
            timeout_sec=max(30, int(config.judge_timeout_sec)),
            retries=1,
        )
    except Exception as exc:  # noqa: BLE001
        return PinchGradeResult(
            task_id=task.task_id,
            grading_type="llm_judge",
            score=0.0,
            max_score=1.0,
            breakdown={},
            notes=f"judge dispatch failed: {exc}",
        )

    parsed = _parse_judge_payload(result.raw_output or result.summary or "")
    scores = _normalize_scores(
        parsed.get("scores", parsed.get("criteria_scores", {}))
        if isinstance(parsed, dict)
        else {}
    )
    total = parsed.get("total", parsed.get("score")) if isinstance(parsed, dict) else None
    if not isinstance(total, (int, float)):
        total = _average(list(scores.values()))
    notes = ""
    if isinstance(parsed, dict):
        notes = str(parsed.get("notes", parsed.get("justification", "")))
    return PinchGradeResult(
        task_id=task.task_id,
        grading_type="llm_judge",
        score=_clip01(float(total)),
        max_score=1.0,
        breakdown=scores,
        notes=notes,
    )


def _combine_hybrid_scores(
    task: PinchTask,
    automated: PinchGradeResult,
    llm: PinchGradeResult,
) -> PinchGradeResult:
    weights = task.grading_weights or {"automated": 0.5, "llm_judge": 0.5}
    w_auto = float(weights.get("automated", 0.5))
    w_llm = float(weights.get("llm_judge", 0.5))
    total_w = w_auto + w_llm
    if total_w <= 0:
        w_auto, w_llm, total_w = 0.5, 0.5, 1.0
    score = ((automated.score * w_auto) + (llm.score * w_llm)) / total_w
    breakdown = {
        **{f"automated.{k}": v for k, v in automated.breakdown.items()},
        **{f"llm_judge.{k}": v for k, v in llm.breakdown.items()},
    }
    notes = " | ".join(x for x in [automated.notes, llm.notes] if x.strip())
    return PinchGradeResult(
        task_id=task.task_id,
        grading_type="hybrid",
        score=_clip01(score),
        max_score=1.0,
        breakdown=breakdown,
        notes=notes,
    )


def _build_summary(
    rows: list[dict[str, Any]],
    run_dir: Path,
    config: PinchBenchRunConfig,
    selected: list[PinchTask],
) -> dict[str, Any]:
    per_task: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        per_task.setdefault(str(row["task_id"]), []).append(row)

    by_task: list[dict[str, Any]] = []
    for task in selected:
        group = per_task.get(task.task_id, [])
        if not group:
            continue
        avg_score = _average([float(x.get("score", 0.0)) for x in group])
        by_task.append(
            {
                "task_id": task.task_id,
                "task_name": task.name,
                "category": task.category,
                "grading_type": task.grading_type,
                "runs": len(group),
                "avg_score": avg_score,
                "best_score": max(float(x.get("score", 0.0)) for x in group),
                "worst_score": min(float(x.get("score", 0.0)) for x in group),
                "status_counts": _count_by(group, "runtime_status"),
            }
        )

    overall_score = _average([float(x.get("score", 0.0)) for x in rows])
    return {
        "benchmark": "PinchBench",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir.resolve()),
        "model": config.model,
        "adapter": config.adapter,
        "benchmark_spec_path": (
            str(config.benchmark_spec_path.expanduser().resolve())
            if config.benchmark_spec_path is not None
            else ""
        ),
        "suite": config.suite,
        "runs_per_task": max(1, int(config.runs)),
        "selected_tasks": len(selected),
        "executed_runs": len(rows),
        "overall_score": overall_score,
        "status_counts": _count_by(rows, "runtime_status"),
        "by_task": by_task,
        "results_jsonl": str((run_dir / "results" / "details.jsonl").resolve()),
        "summary_json": str((run_dir / "results" / "summary.json").resolve()),
    }


def _write_results(rows: list[dict[str, Any]], summary: dict[str, Any], run_dir: Path) -> None:
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    details = results_dir / "details.jsonl"
    with details.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (results_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _prepare_workspace(task: PinchTask, workspace: Path, assets_dir: Path) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    for item in task.workspace_files:
        if not isinstance(item, dict):
            continue
        if "content" in item and "path" in item:
            dest = workspace / str(item["path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(str(item.get("content", "")), encoding="utf-8")
            continue

        source = str(item.get("source", "")).strip()
        dest_rel = str(item.get("dest", "")).strip()
        if not source or not dest_rel:
            continue
        src = assets_dir / source
        if not src.exists():
            raise FileNotFoundError(f"workspace source file not found: {src}")
        dest = workspace / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())


def _build_task_spec(
    task: PinchTask,
    runtime_id: str,
    workspace: Path,
    worker_timeout_sec: int = 0,
):
    timeout_sec = max(30, int(task.timeout_seconds), max(0, int(worker_timeout_sec)))
    prompt = _build_worker_prompt(task, workspace)
    raw = {
        "meta": {
            "id": f"pinch_{task.task_id}",
            "name": f"PinchBench {task.task_id}",
            "version": "0.1.0",
            "pattern": "pipeline",
            "description": f"PinchBench task {task.task_id}",
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
            {
                "id": "completed",
                "kind": "terminal",
            },
        ],
        "features": [
            {"name": "monitor", "enabled": True, "config": {}},
            {"name": "shared_state", "enabled": True, "config": {}},
        ],
        "policy": {
            "require_json_decision": False,
            "max_steps": 4,
        },
    }
    return compile_spec_obj(raw)


def _build_worker_prompt(task: PinchTask, workspace: Path) -> str:
    expected = task.expected_behavior.strip()
    criteria = _format_criteria(task.grading_criteria)
    return (
        "You are solving a PinchBench task through tools in your runtime environment.\n"
        f"Task ID: {task.task_id}\n"
        f"Task Name: {task.name}\n"
        f"Workspace path: {workspace}\n\n"
        "[User Task]\n"
        f"{task.prompt.strip()}\n\n"
        "[Expected Behavior]\n"
        f"{expected}\n\n"
        "[Grading Criteria]\n"
        f"{criteria}\n\n"
        "Execution requirements:\n"
        "- Use tools when needed and produce concrete outputs in workspace.\n"
        "- Do not stop at planning; finish the requested deliverables.\n"
        "- Final answer must be valid JSON only:\n"
        '{"decision":"next","summary":"what you completed","updates":{"artifacts":[]}}'
    )


def _build_task_input(task: PinchTask, workspace: Path) -> str:
    expected = task.expected_behavior.strip()
    criteria = _format_criteria(task.grading_criteria)
    return (
        f"PinchBench task_id={task.task_id}\n"
        f"task_name={task.name}\n"
        f"workspace={workspace}\n\n"
        "[User Task]\n"
        f"{task.prompt.strip()}\n\n"
        "[Expected Behavior]\n"
        f"{expected}\n\n"
        "[Grading Criteria]\n"
        f"{criteria}\n\n"
        "Execution constraints:\n"
        "- Complete real tool/file operations in workspace.\n"
        "- Do not only describe what you did; actually do it.\n"
    )


def _build_judge_prompt(task: PinchTask, transcript: list[dict[str, Any]], rubric: str) -> str:
    return (
        "You are a strict benchmark grader.\n"
        "Return a single JSON object only, no markdown.\n\n"
        "[Task Prompt]\n"
        f"{task.prompt.strip()}\n\n"
        "[Expected Behavior]\n"
        f"{task.expected_behavior.strip()}\n\n"
        "[Transcript Summary]\n"
        f"{_summarize_transcript(transcript)}\n\n"
        "[Rubric]\n"
        f"{rubric.strip()}\n\n"
        "Output schema:\n"
        '{"scores":{"criterion":0.0},"total":0.0,"notes":"brief justification"}'
    )


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
        elif role == "toolResult":
            rows.append(f"tool_result:{str(content)[:240]}")
        elif role == "user":
            rows.append(f"user:{str(content)[:240]}")
    if not rows:
        return "(no transcript events captured)"
    return "\n".join(rows[:200])


def _load_latest_openclaw_transcript(agent_id: str, started_at: float) -> list[dict[str, Any]]:
    agent_dir = _resolve_agent_dir(agent_id)
    sessions_dir = agent_dir / "sessions"
    if not sessions_dir.exists():
        return []

    files = [p for p in sessions_dir.glob("*.jsonl") if p.is_file()]
    if not files:
        return []

    tolerance = 5.0
    recent = [p for p in files if p.stat().st_mtime >= (started_at - tolerance)]
    target = max((recent or files), key=lambda p: p.stat().st_mtime)

    out: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _extract_pc_agent_loop_transcript(history: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in history:
        summary = str(getattr(event, "summary", "") or "").strip()
        if summary:
            skey = f"summary|{summary}"
            if skey not in seen:
                seen.add(skey)
                rows.append(
                    {
                        "type": "message",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": summary,
                                }
                            ],
                        },
                    }
                )
        meta = getattr(event, "meta", {})
        raw_tail = ""
        if isinstance(meta, dict):
            raw_tail = str(meta.get("raw_tail", "") or "")

        tool_calls = _parse_pc_tool_calls(raw_tail)
        tool_calls.extend(_infer_pc_tool_calls_from_text("\n".join(x for x in [summary, raw_tail] if x)))

        for name, params in tool_calls:
            key = f"{name}|{json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "toolCall",
                                "name": name,
                                "params": params,
                            }
                        ],
                    },
                }
            )
    return rows


def _infer_pc_tool_calls_from_text(text: str) -> list[tuple[str, dict[str, Any]]]:
    src = str(text or "")
    out: list[tuple[str, dict[str, Any]]] = []
    for m in _PC_READ_HINT_RE.finditer(src):
        path = _clean_path_token(m.group(1))
        if path:
            out.append(("read_file", {"files": [path]}))
    for m in _PC_WRITE_HINT_RE.finditer(src):
        path = _clean_path_token(m.group(1))
        if path:
            out.append(("write_file", {"path": path}))
    return out


def _clean_path_token(raw: str | None) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    txt = txt.strip("`'\"")
    txt = txt.rstrip(".,;:!?)]}，。；：！？")
    if not txt or "://" in txt:
        return ""
    return txt


def _parse_pc_tool_calls(raw_output: str) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    text = str(raw_output or "")
    if not text.strip():
        return calls

    for m in _PC_TOOL_MD_RE.finditer(text):
        name = str(m.group(1) or "").strip()
        args_text = str(m.group(2) or "").strip()
        try:
            args = json.loads(args_text)
        except json.JSONDecodeError:
            args = {}
        if not isinstance(args, dict):
            args = {}
        calls.append(_normalize_pc_tool_call(name, args))

    for tm in _PC_TOOL_USE_RE.finditer(text):
        body = str(tm.group(1) or "")
        for obj in _extract_json_objects(body):
            tool_name = str(obj.get("name", obj.get("tool_name", ""))).strip()
            args = obj.get("args", obj.get("arguments", obj.get("params", {})))
            if not isinstance(args, dict):
                args = {}
            if tool_name:
                calls.append(_normalize_pc_tool_call(tool_name, args))
    return calls


def _normalize_pc_tool_call(name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    tool = str(name or "").strip()
    params = dict(args or {})
    if "name" in params and str(params.get("name", "")).strip() == tool:
        params.pop("name", None)

    mapping = {
        "file_read": "read_file",
        "file_write": "write_file",
        "file_patch": "write_file",
        "code_run": "execute_command",
    }
    canonical = mapping.get(tool, tool)
    if canonical == "read_file" and "files" not in params:
        path = params.get("path")
        if isinstance(path, str) and path.strip():
            params["files"] = [path]
        elif isinstance(path, list):
            params["files"] = path
    if canonical == "execute_command" and "command" not in params:
        cmd = params.get("code")
        if isinstance(cmd, str) and cmd.strip():
            params["command"] = cmd
    return canonical, params


def _resolve_agent_dir(agent_id: str) -> Path:
    base = Path.home() / ".openclaw" / "agents"
    direct = base / agent_id
    if direct.exists():
        return direct
    normalized = base / agent_id.replace(":", "-")
    if normalized.exists():
        return normalized
    return direct


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


def _load_single_task(path: Path) -> PinchTask:
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = _TASK_FRONTMATTER_RE.match(raw)
    if not m:
        raise ValueError(f"task file missing frontmatter: {path}")
    front = yaml.safe_load(m.group(1)) or {}
    if not isinstance(front, dict):
        raise ValueError(f"invalid task frontmatter: {path}")
    sections = _parse_sections(m.group(2))
    criteria = _parse_criteria(sections.get("Grading Criteria", ""))

    weights = front.get("grading_weights")
    clean_weights = None
    if isinstance(weights, dict):
        clean_weights = {}
        for k, v in weights.items():
            if isinstance(v, (int, float)):
                clean_weights[str(k)] = float(v)

    return PinchTask(
        task_id=str(front.get("id", "")).strip(),
        name=str(front.get("name", "")).strip(),
        category=str(front.get("category", "")).strip(),
        grading_type=str(front.get("grading_type", "automated")).strip(),
        timeout_seconds=max(30, int(front.get("timeout_seconds", 120))),
        workspace_files=(
            front.get("workspace_files")
            if isinstance(front.get("workspace_files"), list)
            else []
        ),
        prompt=str(sections.get("Prompt", "")).strip(),
        expected_behavior=str(sections.get("Expected Behavior", "")).strip(),
        grading_criteria=criteria,
        automated_checks=str(sections.get("Automated Checks", "")).strip(),
        llm_judge_rubric=str(sections.get("LLM Judge Rubric", "")).strip(),
        grading_weights=clean_weights,
        file_path=str(path.resolve()),
    )


def _parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    buf: list[str] = []
    for line in body.splitlines():
        hm = _SECTION_HEADER_RE.match(line.strip())
        if hm:
            if current:
                sections[current] = "\n".join(buf).strip()
            current = hm.group(1).strip()
            buf = []
            continue
        if current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    return sections


def _parse_criteria(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        m = _CRITERION_RE.match(line.strip())
        if m:
            out.append(m.group(1).strip())
    return out


def _extract_python_code(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
    if not m:
        return ""
    return m.group(1)


def _format_criteria(criteria: list[str]) -> str:
    if not criteria:
        return "- No explicit criteria listed."
    return "\n".join(f"- {x}" for x in criteria)


def _build_agent_id(prefix: str, model: str, suffix: str) -> str:
    mslug = _slugify(model, max_len=24)
    digest = hashlib.sha1(f"{model}|{suffix}".encode("utf-8")).hexdigest()[:6]
    ssrc = f"{digest}-{suffix}"
    sslug = _slugify(ssrc, max_len=18)
    return f"{prefix}-{mslug}-{sslug}".strip("-")


def _slugify(src: str, max_len: int = 32) -> str:
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", str(src or "").strip().lower())
    txt = re.sub(r"-+", "-", txt).strip("-")
    return (txt[:max_len].strip("-") or "x")


def _normalize_scores(raw: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = _clip01(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _clip01(x: float) -> float:
    if x < 0:
        return 0.0
    if x > 1:
        return 1.0
    return x


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        v = str(row.get(key, ""))
        out[v] = out.get(v, 0) + 1
    return out


def _parse_judge_payload(text: str) -> dict[str, Any]:
    objects = _extract_json_objects(text)
    if not objects:
        return {}
    for obj in reversed(objects):
        if isinstance(obj, dict) and (
            "scores" in obj or "criteria_scores" in obj or "total" in obj or "score" in obj
        ):
            return obj
    tail = objects[-1]
    return tail if isinstance(tail, dict) else {}


def _extract_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    out: list[dict[str, Any]] = []
    src = str(text or "")
    i = 0
    while i < len(src):
        if src[i] != "{":
            i += 1
            continue
        try:
            obj, consumed = decoder.raw_decode(src[i:])
        except json.JSONDecodeError:
            i += 1
            continue
        if isinstance(obj, dict):
            out.append(obj)
        i += max(1, consumed)
    return out


def _requires_judge(tasks: list[PinchTask]) -> bool:
    return any(t.grading_type in {"llm_judge", "hybrid"} for t in tasks)


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


def _apply_benchmark_stage_objectives(spec: Any, task: PinchTask, workspace: Path) -> None:
    for stage in getattr(spec, "stages", []):
        if getattr(stage, "kind", "") == "terminal":
            continue
        kind = str(getattr(stage, "kind", "")).strip().lower()
        if kind in {"planner", "initiator", "orchestrator"}:
            stage.description = (
                "You are in planning stage. Produce a concise and concrete execution plan for this "
                "PinchBench task, referencing exact filenames and tools. Do not claim completion."
            )
            continue
        stage.description = (
            "You are in execution stage. Execute the task end-to-end using tools and filesystem actions "
            f"in workspace `{workspace}`. Ensure deliverables required by task `{task.task_id}` are "
            "actually created with correct names and content before responding."
        )


def _normalize_transcript_for_grading(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for event in transcript:
        if not isinstance(event, dict):
            continue
        row = copy.deepcopy(event)
        if row.get("type") != "message":
            normalized.append(row)
            continue
        msg = row.get("message")
        if not isinstance(msg, dict):
            normalized.append(row)
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            normalized.append(row)
            continue
        new_content: list[Any] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "toolCall":
                new_content.append(_normalize_tool_call_item(item))
            else:
                new_content.append(item)
        msg["content"] = new_content
        row["message"] = msg
        normalized.append(row)
    return normalized


def _normalize_tool_call_item(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    raw_name = str(out.get("name", "")).strip()
    name = _canonical_tool_name(raw_name)
    out["name"] = name

    params = out.get("params")
    if not isinstance(params, dict):
        args = out.get("arguments")
        if isinstance(args, dict):
            params = dict(args)
        else:
            params = {}
    else:
        params = dict(params)

    if name in {"read_file", "readFile"}:
        if "files" not in params:
            path = params.get("path")
            if isinstance(path, str) and path.strip():
                params["files"] = [path]
            elif isinstance(path, list):
                params["files"] = path

    if name in {"write_file", "writeFile"}:
        if "path" not in params:
            for k in ("file_path", "filepath", "dest", "destination"):
                v = params.get(k)
                if isinstance(v, str) and v.strip():
                    params["path"] = v
                    break

    if name in {"execute_command", "executeCommand"}:
        if "command" not in params:
            for k in ("cmd", "shell_command"):
                v = params.get(k)
                if isinstance(v, str) and v.strip():
                    params["command"] = v
                    break

    if name in {"generate_image", "generateImage", "image_generation"}:
        if "path" not in params:
            for k in ("file_path", "output_path", "save_path", "output"):
                v = params.get(k)
                if isinstance(v, str) and v.strip():
                    params["path"] = v
                    break

    out["params"] = params
    return out


def _canonical_tool_name(name: str) -> str:
    key = str(name or "").strip()
    mapping = {
        "read": "read_file",
        "write": "write_file",
        "exec": "execute_command",
    }
    return mapping.get(key, key)
