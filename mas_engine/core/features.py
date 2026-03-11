"""Feature plugin hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
            "stage": stage.id,
            "task": task.task_id,
            "status": "running",
        }
        ctx.setdefault("monitor", []).append(heartbeat)


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


_PLUGIN_REGISTRY = {
    MonitorPlugin.name: MonitorPlugin,
    SharedStatePlugin.name: SharedStatePlugin,
    SystemProtocolPlugin.name: SystemProtocolPlugin,
    EmergencyHandlerPlugin.name: EmergencyHandlerPlugin,
    HitlConfirmationPlugin.name: HitlConfirmationPlugin,
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
