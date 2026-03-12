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
                    "soul_file_path": "systems/pattern_souls/pipeline/planner.md",
                    "transitions": [{"decision": "next", "to": "execute"}],
                },
                {
                    "id": "execute",
                    "kind": "executor",
                    "agent": "executor",
                    "soul_file_path": "systems/pattern_souls/pipeline/executor.md",
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
                    "soul_file_path": "systems/pattern_souls/gated_pipeline/planner.md",
                    "transitions": [
                        {"decision": "submit", "to": "review"},
                        {"decision": "default", "to": "review"},
                    ],
                },
                {
                    "id": "review",
                    "kind": "gate",
                    "agent": "gatekeeper",
                    "soul_file_path": "systems/pattern_souls/gated_pipeline/gate.md",
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
                    "soul_file_path": "systems/pattern_souls/gated_pipeline/executor.md",
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
                    "soul_file_path": "systems/pattern_souls/autonomous_cluster/orchestrator.md",
                    "transitions": [{"decision": "next", "to": "cluster_exec"}],
                },
                {
                    "id": "cluster_exec",
                    "kind": "cluster",
                    "soul_file_path": "systems/pattern_souls/autonomous_cluster/cluster.md",
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
                    "soul_file_path": "systems/pattern_souls/autonomous_cluster/auditor.md",
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
                "soul_file_path": "systems/pattern_souls/consensus/planner.md",
                "transitions": [{"decision": "next", "to": "vote"}],
            },
            {
                "id": "vote",
                "kind": "consensus",
                "soul_file_path": "systems/pattern_souls/consensus/consensus.md",
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
                "soul_file_path": "systems/pattern_souls/consensus/executor.md",
                "transitions": [{"decision": "next", "to": "completed"}],
            },
            {"id": "completed", "kind": "terminal"},
        ],
    }
