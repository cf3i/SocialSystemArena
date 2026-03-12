"""Dataclasses for governance spec and runtime events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PATTERN_VALUES = {
    "pipeline",
    "gated_pipeline",
    "autonomous_cluster",
    "consensus",
}

STAGE_KIND_VALUES = {
    "initiator",
    "planner",
    "gate",
    "executor",
    "auditor",
    "orchestrator",
    "consensus",
    "cluster",
    "terminal",
}


@dataclass
class TransitionSpec:
    decision: str
    to: str


@dataclass
class ConsensusConfig:
    voters: list[str] = field(default_factory=list)
    algorithm: str = "majority"
    threshold: float = 0.5
    tie_breaker: str = "reject"
    weights: dict[str, float] = field(default_factory=dict)


@dataclass
class ClusterMember:
    agent: str
    role: str = "executor"
    required: bool = True


@dataclass
class StageSopSpec:
    required_patterns: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)
    on_violation: str = "error"  # error | retry | force_decision


@dataclass
class StageSpec:
    id: str
    kind: str
    agent: str | None = None
    description: str = ""
    soul_file_path: str = ""
    prompt_template: str = ""
    transitions: list[TransitionSpec] = field(default_factory=list)
    consensus: ConsensusConfig | None = None
    cluster_members: list[ClusterMember] = field(default_factory=list)
    sop: StageSopSpec | None = None
    default_decision: str = "next"


@dataclass
class FeatureSpec:
    name: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSpec:
    id: str
    runtime_id: str
    role: str = ""
    instructions: str = ""
    timeout_sec: int = 300
    retries: int = 1


@dataclass
class PolicySpec:
    banned_terms: list[str] = field(default_factory=list)
    require_json_decision: bool = True
    max_steps: int = 64


@dataclass
class MetaSpec:
    id: str
    name: str
    version: str
    pattern: str
    description: str = ""


@dataclass
class GovernanceSpec:
    meta: MetaSpec
    agents: dict[str, AgentSpec]
    entry_stage: str
    stages: list[StageSpec]
    features: list[FeatureSpec] = field(default_factory=list)
    policy: PolicySpec = field(default_factory=PolicySpec)
    source_path: str = ""


@dataclass
class AgentResult:
    decision: str
    summary: str
    raw_output: str = ""
    updates: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskEvent:
    index: int
    stage_id: str
    stage_kind: str
    agent: str | None
    decision: str
    summary: str
    next_stage: str | None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskState:
    task_id: str
    title: str
    input_text: str
    current_stage: str
    status: str = "running"
    shared_state: dict[str, Any] = field(default_factory=dict)
    history: list[TaskEvent] = field(default_factory=list)
    agent_sequence: int = 0

    def append_event(self, event: TaskEvent) -> None:
        self.history.append(event)
        self.current_stage = event.next_stage or self.current_stage

    def next_agent_sequence(self) -> int:
        self.agent_sequence += 1
        return self.agent_sequence
