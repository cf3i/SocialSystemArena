"""Governance runtime for executing compiled specs."""

from __future__ import annotations

import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..adapters.base import AgentAdapter
from ..storage.jsonl import JsonlStore
from .errors import AdapterError, RuntimeErrorEngine
from .features import FeatureManager
from .types import AgentResult, GovernanceSpec, StageSpec, TaskEvent, TaskState


_POSITIVE_DECISIONS = {"approve", "approved", "yes", "pass", "accepted", "success"}
_FAILURE_DECISIONS = {"error", "failed", "reject", "rejected", "veto", "cancel", "cancelled"}
_ABSTAIN_DECISIONS = {"error", "timeout"}
_SECTION_MAX_CHARS = 3200
_PROMPT_BODY_MAX_CHARS = 10000
_DISPATCH_GUARD_SLACK_SEC = 1
_PATTERN_STAGE_ALIAS: dict[str, dict[str, str]] = {
    "pipeline": {
        "planner": "plan",
        "executor": "execute",
    },
    "gated_pipeline": {
        "planner": "draft",
        "gate": "review",
        "executor": "execute",
    },
    "autonomous_cluster": {
        "orchestrator": "orchestrate",
        "cluster": "cluster_exec",
        "auditor": "audit",
    },
    "consensus": {
        "planner": "propose",
        "consensus": "vote",
        "executor": "execute",
    },
}
_LOG = logging.getLogger("mas_engine.runtime")


@dataclass
class GovernanceRuntime:
    spec: GovernanceSpec
    adapter: AgentAdapter
    store: JsonlStore | None = None
    human_confirm_callback: Callable[..., bool] | None = None

    def __post_init__(self) -> None:
        self._stage_map = {s.id: s for s in self.spec.stages}
        self._features = FeatureManager.from_specs(self.spec.features)
        self._soul_cache: dict[str, tuple[float, str]] = {}
        self._spec_path = (
            Path(self.spec.source_path).expanduser().resolve()
            if self.spec.source_path
            else None
        )
        self._spec_dir = str(self._spec_path.parent) if self._spec_path else str(Path.cwd())
        self._workspace_root = Path.cwd().resolve()
        if self._spec_path:
            for parent in [self._spec_path.parent, *self._spec_path.parents]:
                if parent.name == "systems":
                    self._workspace_root = parent.parent
                    break
        _LOG.info(
            "runtime initialized: spec=%s entry=%s stages=%s source_dir=%s workspace_root=%s",
            self.spec.meta.id,
            self.spec.entry_stage,
            len(self.spec.stages),
            self._spec_dir,
            self._workspace_root,
        )

    def run(
        self,
        task_id: str,
        title: str,
        input_text: str,
        max_steps: int | None = None,
    ) -> TaskState:
        budget = max_steps or self.spec.policy.max_steps
        task = TaskState(
            task_id=task_id,
            title=title,
            input_text=input_text,
            current_stage=self.spec.entry_stage,
            shared_state={"banned_terms": self.spec.policy.banned_terms},
        )

        for idx in range(budget):
            stage = self._stage_map.get(task.current_stage)
            if stage is None:
                raise RuntimeErrorEngine(f"Unknown stage: {task.current_stage}")

            if stage.kind == "terminal":
                task.status = "done"
                _LOG.info("task=%s reached terminal stage=%s", task.task_id, stage.id)
                if self.store:
                    terminal_event = TaskEvent(
                        index=idx,
                        stage_id=stage.id,
                        stage_kind=stage.kind,
                        agent=None,
                        decision="done",
                        summary="",
                        next_stage=None,
                        meta={},
                    )
                    self.store.append_event(task, terminal_event)
                break

            _LOG.info(
                "task=%s step=%s stage=%s kind=%s",
                task.task_id,
                idx,
                stage.id,
                stage.kind,
            )

            ctx: dict[str, object] = {
                "step": idx,
                "human_confirm_callback": self.human_confirm_callback,
                "agent_traces": [],
                "adapter_dispatch": self._dispatch_with_guard,
                "agents": self.spec.agents,
                "next_agent_sequence": task.next_agent_sequence,
                "append_agent_trace": self._append_agent_trace,
            }
            self._features.before_stage(task, stage, ctx)

            result = self._execute_stage(task, stage, ctx)
            result = self._features.after_stage(task, stage, result, ctx)

            decision = str(ctx.get("force_decision", result.decision or stage.default_decision))
            if decision.lower() == "error":
                task.status = "error"
                next_stage = task.current_stage
            else:
                next_stage = self._resolve_next_stage(stage, decision)
                if next_stage is None:
                    task.status = "error"
                    next_stage = task.current_stage

            event = TaskEvent(
                index=idx,
                stage_id=stage.id,
                stage_kind=stage.kind,
                agent=stage.agent,
                decision=decision,
                summary=result.summary,
                next_stage=next_stage,
                meta={
                    **result.meta,
                    "raw_tail": result.raw_output[-500:],
                    "updates": result.updates,
                    "monitor": ctx.get("monitor", []),
                },
            )
            if self.store:
                self.store.append_agent_traces(
                    task=task,
                    stage_index=idx,
                    stage_id=stage.id,
                    stage_kind=stage.kind,
                    traces=list(ctx.get("agent_traces", [])),
                )
            task.append_event(event)
            if self.store:
                self.store.append_event(task, event)

            _LOG.info(
                "task=%s step=%s stage=%s decision=%s next=%s",
                task.task_id,
                idx,
                stage.id,
                decision,
                next_stage,
            )

            if task.status == "error":
                break

        else:
            task.status = "max_steps_exceeded"

        return task

    def _execute_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        ctx: dict[str, object],
    ) -> AgentResult:
        if stage.kind == "consensus":
            return self._run_consensus_stage(task, stage, ctx)
        if stage.kind == "cluster":
            return self._run_cluster_stage(task, stage, ctx)
        return self._run_single_agent_stage(task, stage, ctx)

    def _run_single_agent_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        ctx: dict[str, object],
    ) -> AgentResult:
        if not stage.agent:
            return AgentResult(
                decision=stage.default_decision,
                summary=f"No agent bound for stage {stage.id}, auto-advance",
            )

        agent = self.spec.agents[stage.agent]
        prompt, prompt_meta = self._build_prompt(task, stage)
        prompt_with_profile = self._append_agent_profile(
            prompt=prompt,
            agent_id=stage.agent,
        )
        sop_retry_enabled = bool(stage.sop and stage.sop.on_violation == "retry")
        max_attempts = 2 if sop_retry_enabled else 1
        result: AgentResult | None = None

        for attempt in range(1, max_attempts + 1):
            seq = task.next_agent_sequence()
            message = prompt_with_profile
            if attempt > 1:
                message = (
                    f"{prompt_with_profile}\n\n"
                    "[SYSTEM] Previous output violated SOP rules. "
                    "You must strictly follow SOP and return valid JSON."
                )
            try:
                dispatch_result = self._dispatch_with_guard(
                    runtime_id=agent.runtime_id,
                    message=message,
                    timeout_sec=agent.timeout_sec,
                    retries=agent.retries,
                )
            except AdapterError as exc:
                result = AgentResult(
                    decision="error",
                    summary=str(exc),
                    raw_output=str(exc),
                    meta={**prompt_meta, "attempt": attempt},
                )
                self._append_agent_trace(
                    ctx=ctx,
                    sequential_id=seq,
                    agent_id=stage.agent,
                    runtime_id=agent.runtime_id,
                    result=result,
                )
                _LOG.warning(
                    "stage=%s agent=%s dispatch failed attempt=%s error=%s",
                    stage.id,
                    stage.agent,
                    attempt,
                    exc,
                )
                return result

            result = dispatch_result
            result.meta = {**result.meta, **prompt_meta, "attempt": attempt}
            sop_check = self._evaluate_sop(stage, result)
            if sop_check:
                result.meta["sop_check"] = sop_check

            self._append_agent_trace(
                ctx=ctx,
                sequential_id=seq,
                agent_id=stage.agent,
                runtime_id=agent.runtime_id,
                result=result,
            )

            if not sop_check or sop_check.get("passed", True):
                break

            action = str(sop_check.get("on_violation", "error"))
            _LOG.warning(
                "stage=%s agent=%s sop_violation action=%s missing=%s forbidden=%s attempt=%s",
                stage.id,
                stage.agent,
                action,
                sop_check.get("missing_required", []),
                sop_check.get("matched_forbidden", []),
                attempt,
            )
            if action == "force_decision":
                result.decision = stage.default_decision or result.decision or "next"
                result.summary = (
                    f"[SOP forced decision={result.decision}] " + (result.summary or "")
                ).strip()
                break

            if action == "retry" and attempt < max_attempts:
                continue

            result = AgentResult(
                decision="error",
                summary=(
                    f"SOP violation in stage '{stage.id}': "
                    f"missing={sop_check.get('missing_required', [])}, "
                    f"forbidden={sop_check.get('matched_forbidden', [])}"
                ),
                raw_output=result.raw_output,
                updates=result.updates,
                meta=result.meta,
            )
            break

        if result is None:
            result = AgentResult(
                decision="error",
                summary=f"stage '{stage.id}' execution produced no result",
            )
            _LOG.error("stage=%s produced no result", stage.id)

        if self.spec.policy.require_json_decision and not result.decision:
            return AgentResult(
                decision="error",
                summary=(
                    f"Agent '{agent.runtime_id}' did not return a decision in JSON contract"
                ),
                raw_output=result.raw_output,
            )

        return result

    def _dispatch_with_guard(
        self,
        runtime_id: str,
        message: str,
        timeout_sec: int,
        retries: int,
    ) -> AgentResult:
        timeout = max(1, int(timeout_sec or 0))
        retry_count = max(1, int(retries or 1))
        holder: dict[str, object] = {}
        done = threading.Event()

        def _target() -> None:
            try:
                holder["result"] = self.adapter.dispatch(
                    runtime_id=runtime_id,
                    message=message,
                    timeout_sec=timeout,
                    retries=retry_count,
                )
            except Exception as exc:  # adapter boundary
                holder["error"] = exc
            finally:
                done.set()

        th = threading.Thread(
            target=_target,
            daemon=True,
            name=f"dispatch-{runtime_id}",
        )
        th.start()

        wait_sec = timeout + _DISPATCH_GUARD_SLACK_SEC
        if not done.wait(wait_sec):
            raise AdapterError(
                f"dispatch timeout: runtime_id={runtime_id} "
                f"timeout_sec={timeout} waited={wait_sec}"
            )

        err = holder.get("error")
        if err is not None:
            if isinstance(err, AdapterError):
                raise err
            raise AdapterError(str(err))

        out = holder.get("result")
        if isinstance(out, AgentResult):
            return out
        raise AdapterError(
            f"dispatch returned invalid result type for agent '{runtime_id}': "
            f"{type(out).__name__}"
        )

    def _run_consensus_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        ctx: dict[str, object],
    ) -> AgentResult:
        assert stage.consensus is not None
        prompt, prompt_meta = self._build_prompt(task, stage)

        ballots: dict[str, AgentResult] = {}
        with ThreadPoolExecutor(max_workers=len(stage.consensus.voters) or 1) as ex:
            futures: dict[object, tuple[str, int, str]] = {}
            for voter in stage.consensus.voters:
                agent = self.spec.agents[voter]
                seq = task.next_agent_sequence()
                prompt_with_profile = self._append_agent_profile(
                    prompt=prompt,
                    agent_id=voter,
                )
                msg = (
                    f"{prompt_with_profile}\n\n"
                    "Return JSON only: "
                    '{"decision":"yes|no","summary":"...","updates":{}}'
                )
                fut = ex.submit(
                    self._dispatch_with_guard,
                    runtime_id=agent.runtime_id,
                    message=msg,
                    timeout_sec=agent.timeout_sec,
                    retries=agent.retries,
                )
                futures[fut] = (voter, seq, agent.runtime_id)

            for fut in as_completed(futures):
                voter, seq, runtime_id = futures[fut]
                try:
                    result = fut.result()
                except Exception as exc:  # adapter error path
                    result = AgentResult(
                        decision="error",
                        summary=f"voter {voter} failed: {exc}",
                        raw_output=str(exc),
                    )
                result.meta = {**result.meta, **prompt_meta}
                sop_check = self._evaluate_sop(stage, result)
                if sop_check:
                    result.meta["sop_check"] = sop_check
                    if not sop_check.get("passed", True):
                        result = AgentResult(
                            decision="error",
                            summary=(
                                f"voter {voter} failed SOP: "
                                f"missing={sop_check.get('missing_required', [])}, "
                                f"forbidden={sop_check.get('matched_forbidden', [])}"
                            ),
                            raw_output=result.raw_output,
                            updates=result.updates,
                            meta=result.meta,
                        )
                ballots[voter] = result
                self._append_agent_trace(
                    ctx=ctx,
                    sequential_id=seq,
                    agent_id=voter,
                    runtime_id=runtime_id,
                    result=result,
                )

        decision = self._aggregate_consensus(stage, ballots)
        summary = (
            f"Consensus {decision}: "
            + "; ".join(f"{k}={v.decision}" for k, v in sorted(ballots.items()))
        )
        _LOG.info("stage=%s consensus decision=%s", stage.id, decision)
        return AgentResult(
            decision=decision,
            summary=summary,
            updates={
                "ballots": {k: v.decision for k, v in ballots.items()},
                "consensus_algorithm": stage.consensus.algorithm,
            },
            meta={"ballots": {k: v.summary for k, v in ballots.items()}},
        )

    def _aggregate_consensus(
        self,
        stage: StageSpec,
        ballots: dict[str, AgentResult],
    ) -> str:
        cfg = stage.consensus
        assert cfg is not None

        algo = cfg.algorithm
        error_handling = getattr(cfg, "error_handling", "reject")
        decisions = {k: str(v.decision).lower() for k, v in ballots.items()}
        positives = {k for k, d in decisions.items() if d in _POSITIVE_DECISIONS}
        abstains = (
            {k for k, d in decisions.items() if d in _ABSTAIN_DECISIONS}
            if error_handling == "abstain"
            else set()
        )

        if algo == "unanimity":
            effective_voters = [v for v in cfg.voters if v not in abstains]
            if not effective_voters:
                return cfg.tie_breaker  # all abstained
            ok = len(positives) == len(effective_voters)
            return "approve" if ok else cfg.tie_breaker

        if algo == "weighted":
            weights = cfg.weights or {}
            total = sum(
                float(weights.get(v, 1.0)) for v in cfg.voters if v not in abstains
            )
            good = sum(float(weights.get(v, 1.0)) for v in positives)
            if total <= 0:
                return cfg.tie_breaker  # all abstained
            return "approve" if (good / total) >= cfg.threshold else cfg.tie_breaker

        # majority (default)
        effective_total = len(cfg.voters) - len(abstains)
        if effective_total <= 0:
            return cfg.tie_breaker  # all abstained → tie_breaker (usually reject)
        ratio = len(positives) / effective_total
        return "approve" if ratio >= cfg.threshold else cfg.tie_breaker

    def _run_cluster_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        ctx: dict[str, object],
    ) -> AgentResult:
        prompt, prompt_meta = self._build_prompt(task, stage)

        outputs: dict[str, AgentResult] = {}
        with ThreadPoolExecutor(max_workers=len(stage.cluster_members) or 1) as ex:
            futures: dict[object, tuple[object, int, str]] = {}
            for member in stage.cluster_members:
                agent = self.spec.agents[member.agent]
                seq = task.next_agent_sequence()
                prompt_with_profile = self._append_agent_profile(
                    prompt=prompt,
                    agent_id=member.agent,
                )
                member_prompt = (
                    f"{prompt_with_profile}\n\n"
                    f"Cluster role: {member.role}. "
                    "Return JSON only: "
                    '{"decision":"success|failed","summary":"...","updates":{}}'
                )
                fut = ex.submit(
                    self._dispatch_with_guard,
                    runtime_id=agent.runtime_id,
                    message=member_prompt,
                    timeout_sec=agent.timeout_sec,
                    retries=agent.retries,
                )
                futures[fut] = (member, seq, agent.runtime_id)

            for fut in as_completed(futures):
                member, seq, runtime_id = futures[fut]
                try:
                    result = fut.result()
                except Exception as exc:
                    result = AgentResult(
                        decision="failed",
                        summary=f"member {member.agent} failed: {exc}",
                        raw_output=str(exc),
                    )
                result.meta = {**result.meta, **prompt_meta}
                sop_check = self._evaluate_sop(stage, result)
                if sop_check:
                    result.meta["sop_check"] = sop_check
                    if not sop_check.get("passed", True):
                        result = AgentResult(
                            decision="failed",
                            summary=(
                                f"member {member.agent} failed SOP: "
                                f"missing={sop_check.get('missing_required', [])}, "
                                f"forbidden={sop_check.get('matched_forbidden', [])}"
                            ),
                            raw_output=result.raw_output,
                            updates=result.updates,
                            meta=result.meta,
                        )
                outputs[member.agent] = result
                self._append_agent_trace(
                    ctx=ctx,
                    sequential_id=seq,
                    agent_id=member.agent,
                    runtime_id=runtime_id,
                    result=result,
                )

        required_failures = []
        for member in stage.cluster_members:
            out = outputs.get(member.agent)
            d = str(out.decision).lower() if out else "failed"
            if member.required and d in _FAILURE_DECISIONS:
                required_failures.append(member.agent)

        decision = "failure" if required_failures else "success"
        summary = (
            "Cluster execution "
            + decision
            + ": "
            + "; ".join(f"{k}={v.decision}" for k, v in sorted(outputs.items()))
        )
        _LOG.info("stage=%s cluster decision=%s", stage.id, decision)
        return AgentResult(
            decision=decision,
            summary=summary,
            updates={
                "cluster_outputs": {k: v.decision for k, v in outputs.items()},
                "required_failures": required_failures,
            },
            meta={"cluster": {k: v.summary for k, v in outputs.items()}},
        )

    def _append_agent_trace(
        self,
        ctx: dict[str, object],
        sequential_id: int,
        agent_id: str,
        runtime_id: str,
        result: AgentResult,
    ) -> None:
        traces = ctx.get("agent_traces")
        if not isinstance(traces, list):
            return
        traces.append(
            {
                "sequential_id": sequential_id,
                "agent_id": agent_id,
                "runtime_id": runtime_id,
                "decision": result.decision,
                "summary": result.summary,
                "raw_tail": result.raw_output[-500:],
                "updates": result.updates,
                "meta": result.meta,
            }
        )

    def _resolve_next_stage(self, stage: StageSpec, decision: str) -> str | None:
        for t in stage.transitions:
            if t.decision == decision:
                return t.to

        for t in stage.transitions:
            if t.decision == "default":
                return t.to

        if decision == "next" and len(stage.transitions) == 1:
            return stage.transitions[0].to

        return None

    def _build_prompt(self, task: TaskState, stage: StageSpec) -> tuple[str, dict[str, object]]:
        transition_view = [{"decision": t.decision, "to": t.to} for t in stage.transitions]
        allowed_decisions = [t.decision for t in stage.transitions if t.decision != "default"]
        if not allowed_decisions and stage.default_decision:
            allowed_decisions = [stage.default_decision]
        allowed_decisions = list(dict.fromkeys(allowed_decisions))

        history_tail = [
            {
                "stage": e.stage_id,
                "decision": e.decision,
                "summary": e.summary,
            }
            for e in task.history[-6:]
        ]
        payload = {
            "task_id": task.task_id,
            "title": task.title,
            "input_text": task.input_text,
            "stage_id": stage.id,
            "stage_kind": stage.kind,
            "shared_state": json.dumps(task.shared_state, ensure_ascii=False),
            "history": json.dumps(history_tail, ensure_ascii=False),
            "last_summary": task.history[-1].summary if task.history else "",
            "transitions": json.dumps(transition_view, ensure_ascii=False),
            "allowed_decisions": json.dumps(allowed_decisions, ensure_ascii=False),
        }
        contract = (
            "\n\n[Topology Contract]\n"
            f"- stage: {stage.id} ({stage.kind})\n"
            f"- transitions: {payload['transitions']}\n"
            f"- allowed_decisions: {payload['allowed_decisions']}\n"
            "Return JSON only with this schema: "
            '{"decision":"...","summary":"...","updates":{}}'
        )

        prompt_meta: dict[str, object] = {}
        sections: list[tuple[str, str]] = []
        seen_lines: set[str] = set()
        truncated_sections: list[str] = []

        precedence = (
            "1) [Stage Objective] is mandatory for this turn.\n"
            "2) If [Institution SOP] conflicts with [Pattern Rules], follow [Institution SOP].\n"
            "3) [Pattern Rules] defines default behavior constraints.\n"
            "4) Never violate [Topology Contract] and JSON output schema."
        )
        sections.append(("Prompt Precedence", precedence))

        if stage.description:
            desc_text = self._render_with_payload(stage.description, payload)
            sections.append(("Stage Objective", desc_text))
            prompt_meta["stage_description"] = desc_text

        pattern_soul_path = self._resolve_pattern_soul_path(stage)
        if pattern_soul_path:
            pattern_text = self._read_soul_file(pattern_soul_path)
            sections.append(("Pattern Rules", self._render_with_payload(pattern_text, payload)))
            prompt_meta["pattern_soul_path"] = pattern_soul_path

        if stage.soul_file_path:
            soul_path = self._resolve_soul_path(stage.soul_file_path)
            soul_text = self._read_soul_file(soul_path)
            sections.append(("Institution SOP", self._render_with_payload(soul_text, payload)))
            prompt_meta["soul_path"] = soul_path
            prompt_meta["prompt_mode"] = (
                "pattern_plus_soul" if pattern_soul_path else "soul_file_path"
            )
        elif stage.prompt_template:
            text = self._render_with_payload(stage.prompt_template, payload)
            sections.append(("Legacy Prompt Template", text))
            prompt_meta["prompt_mode"] = (
                "pattern_plus_prompt_template_legacy"
                if pattern_soul_path
                else "prompt_template_legacy"
            )
            _LOG.warning(
                "stage=%s uses legacy prompt_template; consider migrating to soul_file_path",
                stage.id,
            )
        else:
            fallback = (
                "You are a stage worker in a governance engine. "
                f"Stage={stage.id} ({stage.kind})\n"
                f"TaskId={task.task_id}\n"
                f"Title={task.title}\n"
                f"Input={task.input_text}\n"
                f"SharedState={payload['shared_state']}\n"
                f"History={payload['history']}\n"
                f"Transitions={payload['transitions']}\n"
                f"AllowedDecisions={payload['allowed_decisions']}"
            )
            sections.append(("Runtime Fallback", fallback))
            prompt_meta["prompt_mode"] = (
                "pattern_plus_runtime_fallback"
                if pattern_soul_path
                else "runtime_fallback"
            )
            _LOG.warning("stage=%s has no soul_file_path and no prompt_template", stage.id)

        rendered_sections: list[str] = []
        section_names: list[str] = []
        for name, content in sections:
            deduped = self._dedupe_text_lines(content, seen_lines)
            clipped, clipped_flag = self._clip_text(deduped, _SECTION_MAX_CHARS)
            if clipped_flag:
                truncated_sections.append(name)
            clean = clipped.strip()
            if not clean:
                continue
            rendered_sections.append(f"[{name}]\n{clean}")
            section_names.append(name)

        body = "\n\n".join(rendered_sections)
        body, body_clipped = self._clip_text(body, _PROMPT_BODY_MAX_CHARS)
        if body_clipped:
            truncated_sections.append("Prompt Body")
            body = body + "\n\n[System Note]\nPrompt body truncated for length control."

        prompt_meta["prompt_sections"] = section_names
        prompt_meta["prompt_truncated_sections"] = truncated_sections
        return body + contract, prompt_meta

    def _append_agent_profile(self, prompt: str, agent_id: str) -> str:
        agent = self.spec.agents.get(agent_id)
        if agent is None:
            return prompt

        profile_lines: list[str] = []
        role = str(agent.role or "").strip()
        instructions = str(agent.instructions or "").strip()
        if role:
            profile_lines.append(f"- role: {role}")
        if instructions:
            profile_lines.append(f"- instructions: {instructions}")

        if not profile_lines:
            return prompt

        profile = "[Agent Profile]\n" + "\n".join(profile_lines)
        return f"{prompt}\n\n{profile}"

    def _render_with_payload(self, template: str, payload: dict[str, object]) -> str:
        out = str(template)
        for key, val in payload.items():
            out = out.replace(f"{{{key}}}", str(val))
        return out

    def _dedupe_text_lines(self, text: str, seen: set[str]) -> str:
        lines = str(text).splitlines()
        out: list[str] = []
        blank_pending = False
        for raw in lines:
            line = raw.rstrip()
            key = line.strip()
            if not key:
                if out and not blank_pending:
                    out.append("")
                    blank_pending = True
                continue
            blank_pending = False
            if key in seen:
                continue
            seen.add(key)
            out.append(line)
        return "\n".join(out).strip()

    def _clip_text(self, text: str, max_chars: int) -> tuple[str, bool]:
        src = str(text or "")
        if len(src) <= max_chars:
            return src, False
        clipped = src[: max(0, max_chars - 1)] + "…"
        return clipped, True

    def _resolve_pattern_soul_path(self, stage: StageSpec) -> str | None:
        pattern = str(self.spec.meta.pattern or "").strip()
        if not pattern:
            return None

        roots = [self._workspace_root]
        repo_root = Path(__file__).resolve().parents[2]
        if repo_root not in roots:
            roots.append(repo_root)

        candidates: list[Path] = []
        for root in roots:
            base = root / "systems" / "pattern_souls" / pattern
            candidates.append(base / f"{stage.kind}.md")

            alias = _PATTERN_STAGE_ALIAS.get(pattern, {}).get(stage.kind)
            if alias:
                candidates.append(base / f"{alias}.md")

        for c in candidates:
            if c.exists() and c.is_file():
                return str(c.resolve())

        _LOG.debug(
            "pattern soul not found: pattern=%s stage=%s kind=%s checked=%s",
            pattern,
            stage.id,
            stage.kind,
            [str(x) for x in candidates],
        )
        return None

    def _resolve_soul_path(self, soul_file_path: str) -> str:
        p = Path(soul_file_path).expanduser()
        if not p.is_absolute():
            candidates: list[Path] = []
            candidates.append((Path(self._spec_dir) / p).resolve())
            candidates.append((self._workspace_root / p).resolve())
            candidates.append((Path.cwd() / p).resolve())

            # Inline spec without source_path: try discovering unique match under institutions.
            if self._spec_path is None:
                inst_root = self._workspace_root / "systems" / "institutions"
                if inst_root.exists() and inst_root.is_dir():
                    hits = []
                    for d in inst_root.iterdir():
                        if not d.is_dir():
                            continue
                        c = (d / p).resolve()
                        if c.exists() and c.is_file():
                            hits.append(c)
                    if len(hits) == 1:
                        candidates.insert(0, hits[0])

                    guessed_id = self._guess_institution_id_from_meta()
                    if guessed_id:
                        guessed = (inst_root / guessed_id / p).resolve()
                        candidates.insert(0, guessed)

            seen: set[str] = set()
            for c in candidates:
                k = str(c)
                if k in seen:
                    continue
                seen.add(k)
                if c.exists() and c.is_file():
                    return str(c)
            p = candidates[0]
        else:
            p = p.resolve()
        if not p.exists() or not p.is_file():
            raise RuntimeErrorEngine(f"soul file not found: {p}")
        return str(p)

    def _guess_institution_id_from_meta(self) -> str:
        sid = str(self.spec.meta.id or "").strip().lower()
        for suffix in ("_yaml", "_json", "_cue"):
            if sid.endswith(suffix):
                sid = sid[: -len(suffix)]
                break
        return sid

    def _read_soul_file(self, resolved_path: str) -> str:
        p = Path(resolved_path)
        mtime = p.stat().st_mtime
        cached = self._soul_cache.get(resolved_path)
        if cached and cached[0] == mtime:
            return cached[1]
        text = p.read_text(encoding="utf-8")
        self._soul_cache[resolved_path] = (mtime, text)
        _LOG.info("loaded soul file: %s", resolved_path)
        return text

    def _evaluate_sop(self, stage: StageSpec, result: AgentResult) -> dict[str, object] | None:
        if stage.sop is None:
            return None
        text = f"{result.raw_output}\n{result.summary}"
        missing_required: list[str] = []
        matched_forbidden: list[str] = []
        for pat in stage.sop.required_patterns:
            if not re.search(pat, text, flags=re.MULTILINE):
                missing_required.append(pat)
        for pat in stage.sop.forbidden_patterns:
            if re.search(pat, text, flags=re.MULTILINE):
                matched_forbidden.append(pat)
        return {
            "enabled": True,
            "passed": not missing_required and not matched_forbidden,
            "required_patterns": stage.sop.required_patterns,
            "forbidden_patterns": stage.sop.forbidden_patterns,
            "missing_required": missing_required,
            "matched_forbidden": matched_forbidden,
            "on_violation": stage.sop.on_violation,
        }
