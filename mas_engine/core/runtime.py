"""Governance runtime for executing compiled specs."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from ..adapters.base import AgentAdapter
from ..storage.jsonl import JsonlStore
from .errors import AdapterError, RuntimeErrorEngine
from .features import FeatureManager
from .types import AgentResult, GovernanceSpec, StageSpec, TaskEvent, TaskState


_POSITIVE_DECISIONS = {"approve", "approved", "yes", "pass", "accepted", "success"}
_FAILURE_DECISIONS = {"error", "failed", "reject", "rejected", "veto", "cancel", "cancelled"}


@dataclass
class GovernanceRuntime:
    spec: GovernanceSpec
    adapter: AgentAdapter
    store: JsonlStore | None = None
    human_confirm_callback: Callable[..., bool] | None = None

    def __post_init__(self) -> None:
        self._stage_map = {s.id: s for s in self.spec.stages}
        self._features = FeatureManager.from_specs(self.spec.features)

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
                break

            ctx: dict[str, object] = {
                "step": idx,
                "human_confirm_callback": self.human_confirm_callback,
                "agent_traces": [],
            }
            self._features.before_stage(task, stage, ctx)

            result = self._execute_stage(task, stage, ctx)
            result = self._features.after_stage(task, stage, result, ctx)

            decision = str(ctx.get("force_decision", result.decision or stage.default_decision))
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
        prompt = self._build_prompt(task, stage)
        seq = task.next_agent_sequence()
        try:
            result = self.adapter.dispatch(
                runtime_id=agent.runtime_id,
                message=prompt,
                timeout_sec=agent.timeout_sec,
                retries=agent.retries,
            )
        except AdapterError as exc:
            result = AgentResult(decision="error", summary=str(exc), raw_output=str(exc))
            self._append_agent_trace(
                ctx=ctx,
                sequential_id=seq,
                agent_id=stage.agent,
                runtime_id=agent.runtime_id,
                result=result,
            )
            return result

        self._append_agent_trace(
            ctx=ctx,
            sequential_id=seq,
            agent_id=stage.agent,
            runtime_id=agent.runtime_id,
            result=result,
        )

        if self.spec.policy.require_json_decision and not result.decision:
            return AgentResult(
                decision="error",
                summary=(
                    f"Agent '{agent.runtime_id}' did not return a decision in JSON contract"
                ),
                raw_output=result.raw_output,
            )

        return result

    def _run_consensus_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        ctx: dict[str, object],
    ) -> AgentResult:
        assert stage.consensus is not None
        prompt = self._build_prompt(task, stage)

        ballots: dict[str, AgentResult] = {}
        with ThreadPoolExecutor(max_workers=len(stage.consensus.voters) or 1) as ex:
            futures: dict[object, tuple[str, int, str]] = {}
            for voter in stage.consensus.voters:
                agent = self.spec.agents[voter]
                seq = task.next_agent_sequence()
                msg = (
                    f"{prompt}\n\n"
                    "Return JSON only: "
                    '{"decision":"yes|no","summary":"...","updates":{}}'
                )
                fut = ex.submit(
                    self.adapter.dispatch,
                    agent.runtime_id,
                    msg,
                    agent.timeout_sec,
                    agent.retries,
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
        decisions = {k: str(v.decision).lower() for k, v in ballots.items()}
        positives = {k for k, d in decisions.items() if d in _POSITIVE_DECISIONS}

        if algo == "unanimity":
            ok = len(positives) == len(cfg.voters) and len(cfg.voters) > 0
            return "approve" if ok else cfg.tie_breaker

        if algo == "weighted":
            weights = cfg.weights or {}
            total = sum(float(weights.get(v, 1.0)) for v in cfg.voters)
            good = sum(float(weights.get(v, 1.0)) for v in positives)
            if total <= 0:
                return cfg.tie_breaker
            return "approve" if (good / total) >= cfg.threshold else cfg.tie_breaker

        # majority (default)
        if not cfg.voters:
            return cfg.tie_breaker
        ratio = len(positives) / len(cfg.voters)
        return "approve" if ratio >= cfg.threshold else cfg.tie_breaker

    def _run_cluster_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        ctx: dict[str, object],
    ) -> AgentResult:
        prompt = self._build_prompt(task, stage)

        outputs: dict[str, AgentResult] = {}
        with ThreadPoolExecutor(max_workers=len(stage.cluster_members) or 1) as ex:
            futures: dict[object, tuple[object, int, str]] = {}
            for member in stage.cluster_members:
                agent = self.spec.agents[member.agent]
                seq = task.next_agent_sequence()
                member_prompt = (
                    f"{prompt}\n\n"
                    f"Cluster role: {member.role}. "
                    "Return JSON only: "
                    '{"decision":"success|failed","summary":"...","updates":{}}'
                )
                fut = ex.submit(
                    self.adapter.dispatch,
                    agent.runtime_id,
                    member_prompt,
                    agent.timeout_sec,
                    agent.retries,
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

    def _build_prompt(self, task: TaskState, stage: StageSpec) -> str:
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
            "\n\nTopology context:\n"
            f"- stage: {stage.id} ({stage.kind})\n"
            f"- transitions: {payload['transitions']}\n"
            f"- allowed_decisions: {payload['allowed_decisions']}\n"
            "Return JSON only with this schema: "
            '{"decision":"...","summary":"...","updates":{}}'
        )

        if stage.prompt_template:
            try:
                text = stage.prompt_template.format(**payload)
            except KeyError as exc:
                raise RuntimeErrorEngine(
                    f"Stage '{stage.id}' prompt template missing key: {exc}"
                )
            return text + contract

        return (
            "You are a stage worker in a governance engine. "
            f"Stage={stage.id} ({stage.kind})\n"
            f"TaskId={task.task_id}\n"
            f"Title={task.title}\n"
            f"Input={task.input_text}\n"
            f"SharedState={payload['shared_state']}\n"
            f"History={payload['history']}\n"
            f"Transitions={payload['transitions']}\n"
            f"AllowedDecisions={payload['allowed_decisions']}"
            + contract
        )
