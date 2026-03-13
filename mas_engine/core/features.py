"""Feature plugin hooks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .errors import AdapterError
from .types import AgentResult, FeatureSpec, StageSpec, TaskState


class FeaturePlugin:
    name = "base"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def before_stage(self, task: TaskState, stage: StageSpec, ctx: dict[str, Any]) -> None:
        del task, stage, ctx

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        del task, stage, ctx
        return result


class MonitorPlugin(FeaturePlugin):
    name = "monitor"

    def before_stage(self, task: TaskState, stage: StageSpec, ctx: dict[str, Any]) -> None:
        heartbeat = {
            "type": "heartbeat",
            "stage": stage.id,
            "task": task.task_id,
            "status": "running",
        }
        ctx.setdefault("monitor", []).append(heartbeat)

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        observer_id = str(self.config.get("observer_agent", "")).strip()
        if not observer_id:
            return result

        dispatch = ctx.get("adapter_dispatch")
        agents = ctx.get("agents")
        if not callable(dispatch) or not isinstance(agents, dict):
            return result

        observer = agents.get(observer_id)
        if observer is None:
            ctx.setdefault("monitor", []).append(
                {
                    "type": "observer_error",
                    "stage": stage.id,
                    "task": task.task_id,
                    "observer_agent": observer_id,
                    "error": "observer_agent_not_found",
                }
            )
            return result

        history_tail = [
            {
                "stage": e.stage_id,
                "decision": e.decision,
                "summary": e.summary,
            }
            for e in task.history[-6:]
        ]
        monitor_prompt = (
            "[Monitor Observer]\n"
            "你是旁路监察节点，只做监督与报告，不得阻断主链路。\n"
            f"task_id: {task.task_id}\n"
            f"title: {task.title}\n"
            f"stage: {stage.id} ({stage.kind})\n"
            f"stage_decision: {result.decision}\n"
            f"stage_summary: {result.summary}\n"
            f"recent_history: {json.dumps(history_tail, ensure_ascii=False)}\n"
            "请输出 JSON："
            '{"decision":"ok|alert","summary":"...","updates":{"impeachment_report":"..."}}'
        )

        timeout_default = int(self.config.get("observer_timeout_sec", 120))
        retries_default = int(self.config.get("observer_retries", 1))
        timeout_sec = int(getattr(observer, "timeout_sec", timeout_default) or timeout_default)
        retries = int(getattr(observer, "retries", retries_default) or retries_default)
        runtime_id = str(getattr(observer, "runtime_id", observer_id))

        try:
            obs_result = dispatch(
                runtime_id=runtime_id,
                message=monitor_prompt,
                timeout_sec=timeout_sec,
                retries=retries,
            )
            report = {
                "type": "observer_report",
                "stage": stage.id,
                "task": task.task_id,
                "observer_agent": observer_id,
                "observer_runtime_id": runtime_id,
                "observer_decision": obs_result.decision,
                "observer_summary": obs_result.summary,
                "observer_updates": obs_result.updates,
            }
            ctx.setdefault("monitor", []).append(report)
            task.shared_state.setdefault("_monitor_reports", []).append(report)
            self._append_observer_trace(
                ctx=ctx,
                observer_agent=observer_id,
                runtime_id=runtime_id,
                result=obs_result,
            )
        except AdapterError as exc:
            ctx.setdefault("monitor", []).append(
                {
                    "type": "observer_error",
                    "stage": stage.id,
                    "task": task.task_id,
                    "observer_agent": observer_id,
                    "observer_runtime_id": runtime_id,
                    "error": str(exc),
                }
            )

        return result

    def _append_observer_trace(
        self,
        ctx: dict[str, Any],
        observer_agent: str,
        runtime_id: str,
        result: AgentResult,
    ) -> None:
        next_seq = ctx.get("next_agent_sequence")
        append_trace = ctx.get("append_agent_trace")
        if not callable(next_seq) or not callable(append_trace):
            return

        seq = next_seq()
        append_trace(
            ctx=ctx,
            sequential_id=seq,
            agent_id=observer_agent,
            runtime_id=runtime_id,
            result=result,
        )


class SharedStatePlugin(FeaturePlugin):
    name = "shared_state"

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        del stage, ctx
        if result.updates:
            task.shared_state.update(result.updates)
        return result


class SystemProtocolPlugin(FeaturePlugin):
    name = "system_protocol"

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        del stage
        banned = self.config.get("banned_terms") or task.shared_state.get("banned_terms") or []
        text = f"{result.summary}\n{result.raw_output}".lower()
        for term in banned:
            t = str(term).strip().lower()
            if not t:
                continue
            if t in text:
                ctx["force_decision"] = str(self.config.get("violation_decision", "policy_violation"))
                return AgentResult(
                    decision=ctx["force_decision"],
                    summary=f"System protocol violation: output contains banned term '{term}'",
                    raw_output=result.raw_output,
                    updates=result.updates,
                    meta={**result.meta, "policy_violation": term},
                )
        return result


class EmergencyHandlerPlugin(FeaturePlugin):
    name = "emergency_handler"

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        del stage
        failure_decisions = set(self.config.get("failure_decisions", ["error", "failed"]))
        threshold = int(self.config.get("threshold", 2))
        emergency_decision = str(self.config.get("emergency_decision", "emergency"))

        state = task.shared_state.setdefault("_emergency", {})
        failures = int(state.get("failures", 0))

        if result.decision in failure_decisions:
            failures += 1
            state["failures"] = failures
            if failures >= threshold:
                ctx["force_decision"] = emergency_decision
                return AgentResult(
                    decision=emergency_decision,
                    summary=(
                        f"Emergency handler triggered after {failures} "
                        f"failures at stage '{stage.id}'"
                    ),
                    raw_output=result.raw_output,
                    updates=result.updates,
                    meta={**result.meta, "emergency": True, "failures": failures},
                )
        else:
            state["failures"] = 0

        return result


class HitlConfirmationPlugin(FeaturePlugin):
    name = "human_confirmation"

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        stage_allow = self.config.get("stages", [])
        if stage_allow and stage.id not in stage_allow:
            return result

        callback = ctx.get("human_confirm_callback")
        if callback is None:
            # No callback attached -> no-op in non-interactive mode.
            return result

        approved = bool(
            callback(
                task=task,
                stage=stage,
                result=result,
            )
        )
        if approved:
            return result

        reject_decision = str(self.config.get("reject_decision", "reject"))
        return AgentResult(
            decision=reject_decision,
            summary=f"HITL rejected output at stage '{stage.id}'",
            raw_output=result.raw_output,
            updates=result.updates,
            meta={**result.meta, "hitl_rejected": True},
        )


class LoopGuardPlugin(FeaturePlugin):
    name = "loop_guard"

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        rules = self.config.get("rules", [])
        if not isinstance(rules, list):
            return result

        decision = str(result.decision or "").strip()
        if not decision:
            return result

        for item in rules:
            if not isinstance(item, dict):
                continue
            stage_id = str(item.get("stage", "")).strip()
            guarded_decision = str(item.get("decision", "")).strip()
            force_decision = str(item.get("force_decision", "next")).strip() or "next"
            try:
                max_count = int(item.get("max_count", 0))
            except Exception:
                max_count = 0

            if not stage_id or not guarded_decision or max_count <= 0:
                continue
            if stage.id != stage_id or decision != guarded_decision:
                continue

            previous_count = sum(
                1
                for evt in task.history
                if evt.stage_id == stage_id and str(evt.decision) == guarded_decision
            )
            current_count = previous_count + 1
            if current_count <= max_count:
                continue

            ctx["force_decision"] = force_decision
            return AgentResult(
                decision=force_decision,
                summary=(
                    f"Loop guard forced '{force_decision}' at stage '{stage_id}' "
                    f"after {previous_count} '{guarded_decision}' events "
                    f"(max={max_count})"
                ),
                raw_output=result.raw_output,
                updates=result.updates,
                meta={
                    **result.meta,
                    "loop_guard": {
                        "stage": stage_id,
                        "decision": guarded_decision,
                        "max_count": max_count,
                        "actual_count": current_count,
                        "forced_decision": force_decision,
                    },
                },
            )

        return result


_PLUGIN_REGISTRY = {
    MonitorPlugin.name: MonitorPlugin,
    SharedStatePlugin.name: SharedStatePlugin,
    SystemProtocolPlugin.name: SystemProtocolPlugin,
    EmergencyHandlerPlugin.name: EmergencyHandlerPlugin,
    HitlConfirmationPlugin.name: HitlConfirmationPlugin,
    LoopGuardPlugin.name: LoopGuardPlugin,
}


@dataclass
class FeatureManager:
    plugins: list[FeaturePlugin]

    @classmethod
    def from_specs(cls, specs: list[FeatureSpec]) -> "FeatureManager":
        plugins: list[FeaturePlugin] = []
        for spec in specs:
            if not spec.enabled:
                continue
            plugin_cls = _PLUGIN_REGISTRY.get(spec.name)
            if plugin_cls is None:
                continue
            plugins.append(plugin_cls(spec.config))
        return cls(plugins=plugins)

    def before_stage(self, task: TaskState, stage: StageSpec, ctx: dict[str, Any]) -> None:
        for plugin in self.plugins:
            plugin.before_stage(task, stage, ctx)

    def after_stage(
        self,
        task: TaskState,
        stage: StageSpec,
        result: AgentResult,
        ctx: dict[str, Any],
    ) -> AgentResult:
        cur = result
        for plugin in self.plugins:
            cur = plugin.after_stage(task, stage, cur, ctx)
        return cur
