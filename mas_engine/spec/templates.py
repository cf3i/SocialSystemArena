"""Built-in starter templates for governance specs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SUPPORTED_PATTERNS = [
    "pipeline",
    "gated_pipeline",
    "autonomous_cluster",
    "consensus",
]


def build_spec_template(spec_id: str, name: str, pattern: str) -> dict[str, Any]:
    if pattern not in SUPPORTED_PATTERNS:
        raise ValueError(f"Unsupported pattern: {pattern}")

    meta = {
        "meta": {
            "id": spec_id,
            "name": name,
            "version": "0.1.0",
            "pattern": pattern,
            "description": f"Starter template for {pattern}",
        },
        "features": [
            {"name": "monitor", "enabled": True, "config": {}},
            {"name": "shared_state", "enabled": True, "config": {}},
        ],
        "policy": {
            "require_json_decision": False,
            "max_steps": 16,
        },
    }

    pattern_spec = _pattern_scaffold(pattern)
    merged = {**meta, **pattern_spec}
    return deepcopy(merged)


def _pattern_scaffold(pattern: str) -> dict[str, Any]:
    if pattern == "pipeline":
        return {
            "entry_stage": "plan",
            "agents": {
                "planner": {"runtime_id": "planner", "role": "planner"},
                "executor": {"runtime_id": "executor", "role": "executor"},
            },
            "stages": [
                {
                    "id": "plan",
                    "kind": "planner",
                    "agent": "planner",
                    "prompt_template": "生成执行计划。任务:{title}",
                    "transitions": [{"decision": "next", "to": "execute"}],
                },
                {
                    "id": "execute",
                    "kind": "executor",
                    "agent": "executor",
                    "prompt_template": "按计划执行并返回结果。任务:{title}",
                    "transitions": [{"decision": "next", "to": "completed"}],
                },
                {"id": "completed", "kind": "terminal"},
            ],
        }

    if pattern == "gated_pipeline":
        return {
            "entry_stage": "draft",
            "agents": {
                "planner": {"runtime_id": "planner", "role": "planner"},
                "gatekeeper": {"runtime_id": "gatekeeper", "role": "gate"},
                "executor": {"runtime_id": "executor", "role": "executor"},
            },
            "stages": [
                {
                    "id": "draft",
                    "kind": "planner",
                    "agent": "planner",
                    "prompt_template": "起草方案并提交审议。任务:{title}",
                    "transitions": [
                        {"decision": "submit", "to": "review"},
                        {"decision": "default", "to": "review"},
                    ],
                },
                {
                    "id": "review",
                    "kind": "gate",
                    "agent": "gatekeeper",
                    "prompt_template": "审议方案，decision=approve|reject。任务:{title}",
                    "transitions": [
                        {"decision": "approve", "to": "execute"},
                        {"decision": "reject", "to": "completed"},
                        {"decision": "default", "to": "completed"},
                    ],
                },
                {
                    "id": "execute",
                    "kind": "executor",
                    "agent": "executor",
                    "prompt_template": "执行已批准方案。任务:{title}",
                    "transitions": [{"decision": "next", "to": "completed"}],
                },
                {"id": "completed", "kind": "terminal"},
            ],
        }

    if pattern == "autonomous_cluster":
        return {
            "entry_stage": "orchestrate",
            "agents": {
                "orchestrator": {"runtime_id": "orchestrator", "role": "orchestrator"},
                "unit_a": {"runtime_id": "unit_a", "role": "subsystem"},
                "unit_b": {"runtime_id": "unit_b", "role": "subsystem"},
                "auditor": {"runtime_id": "auditor", "role": "auditor"},
            },
            "stages": [
                {
                    "id": "orchestrate",
                    "kind": "orchestrator",
                    "agent": "orchestrator",
                    "prompt_template": "拆分任务到多个子系统。任务:{title}",
                    "transitions": [{"decision": "next", "to": "cluster_exec"}],
                },
                {
                    "id": "cluster_exec",
                    "kind": "cluster",
                    "prompt_template": "子系统并行执行并返回 success|failed。任务:{title}",
                    "cluster_members": [
                        {"agent": "unit_a", "role": "worker", "required": True},
                        {"agent": "unit_b", "role": "worker", "required": True},
                    ],
                    "transitions": [
                        {"decision": "success", "to": "audit"},
                        {"decision": "failure", "to": "audit"},
                        {"decision": "default", "to": "audit"},
                    ],
                },
                {
                    "id": "audit",
                    "kind": "auditor",
                    "agent": "auditor",
                    "prompt_template": "汇总并审计执行结果。任务:{title}",
                    "transitions": [{"decision": "next", "to": "completed"}],
                },
                {"id": "completed", "kind": "terminal"},
            ],
        }

    # consensus
    return {
        "entry_stage": "propose",
        "agents": {
            "planner": {"runtime_id": "planner", "role": "planner"},
            "voter_a": {"runtime_id": "voter_a", "role": "voter"},
            "voter_b": {"runtime_id": "voter_b", "role": "voter"},
            "executor": {"runtime_id": "executor", "role": "executor"},
        },
        "stages": [
            {
                "id": "propose",
                "kind": "planner",
                "agent": "planner",
                "prompt_template": "提出方案。任务:{title}",
                "transitions": [{"decision": "next", "to": "vote"}],
            },
            {
                "id": "vote",
                "kind": "consensus",
                "prompt_template": "投票 yes/no。任务:{title}",
                "consensus": {
                    "voters": ["voter_a", "voter_b"],
                    "algorithm": "majority",
                    "threshold": 0.5,
                    "tie_breaker": "reject",
                },
                "transitions": [
                    {"decision": "approve", "to": "execute"},
                    {"decision": "reject", "to": "completed"},
                    {"decision": "default", "to": "completed"},
                ],
            },
            {
                "id": "execute",
                "kind": "executor",
                "agent": "executor",
                "prompt_template": "执行通过方案。任务:{title}",
                "transitions": [{"decision": "next", "to": "completed"}],
            },
            {"id": "completed", "kind": "terminal"},
        ],
    }
