"""Semantic validation for governance specs."""

from __future__ import annotations

import re
from collections import Counter

from ..core.errors import SpecError
from ..core.types import GovernanceSpec, PATTERN_VALUES, STAGE_KIND_VALUES


def validate_spec(spec: GovernanceSpec) -> None:
    if spec.meta.pattern not in PATTERN_VALUES:
        raise SpecError(f"Unsupported pattern: {spec.meta.pattern}")

    stage_ids = [s.id for s in spec.stages]
    dup = [k for k, v in Counter(stage_ids).items() if v > 1]
    if dup:
        raise SpecError(f"Duplicate stage ids: {dup}")

    if spec.entry_stage not in set(stage_ids):
        raise SpecError(f"entry_stage not found: {spec.entry_stage}")

    stage_map = {s.id: s for s in spec.stages}
    runtime_ids = [a.runtime_id for a in spec.agents.values()]
    runtime_dup = [k for k, v in Counter(runtime_ids).items() if v > 1]
    if runtime_dup:
        raise SpecError(
            "Duplicate runtime_id across agents is not allowed for identity isolation: "
            + ", ".join(sorted(runtime_dup))
        )

    for s in spec.stages:
        if s.kind not in STAGE_KIND_VALUES:
            raise SpecError(f"Invalid stage kind '{s.kind}' in stage '{s.id}'")

        if s.kind != "terminal" and not s.transitions:
            raise SpecError(f"Stage '{s.id}' must declare transitions")

        if s.kind != "terminal" and not s.soul_file_path and not s.prompt_template:
            raise SpecError(
                f"Stage '{s.id}' must set soul_file_path "
                "or prompt_template (legacy fallback)"
            )

        if s.agent is not None and s.agent not in spec.agents:
            raise SpecError(f"Stage '{s.id}' references unknown agent '{s.agent}'")

        for t in s.transitions:
            if t.to not in stage_map:
                raise SpecError(
                    f"Stage '{s.id}' transition points to unknown stage '{t.to}'"
                )

        if s.sop:
            if s.sop.on_violation not in {"error", "retry", "force_decision"}:
                raise SpecError(
                    f"Stage '{s.id}' sop.on_violation must be one of "
                    "error|retry|force_decision"
                )
            for pat in s.sop.required_patterns:
                _validate_regex(stage_id=s.id, pattern=pat, field="required_patterns")
            for pat in s.sop.forbidden_patterns:
                _validate_regex(stage_id=s.id, pattern=pat, field="forbidden_patterns")

        if s.kind == "consensus":
            if not s.consensus:
                raise SpecError(f"Consensus stage '{s.id}' requires consensus config")
            if not s.consensus.voters:
                raise SpecError(f"Consensus stage '{s.id}' requires voter agents")
            missing_voters = [v for v in s.consensus.voters if v not in spec.agents]
            if missing_voters:
                raise SpecError(
                    f"Consensus stage '{s.id}' has unknown voters: {missing_voters}"
                )
            if s.consensus.algorithm not in {"majority", "weighted", "unanimity"}:
                raise SpecError(
                    f"Consensus stage '{s.id}' unsupported algorithm: "
                    f"{s.consensus.algorithm}"
                )

        if s.kind == "cluster":
            if not s.cluster_members:
                raise SpecError(f"Cluster stage '{s.id}' requires cluster_members")
            for m in s.cluster_members:
                if m.agent not in spec.agents:
                    raise SpecError(
                        f"Cluster stage '{s.id}' references unknown member '{m.agent}'"
                    )

    _validate_pattern_constraints(spec)


def _validate_pattern_constraints(spec: GovernanceSpec) -> None:
    pattern = spec.meta.pattern
    kinds = [s.kind for s in spec.stages]

    if pattern == "pipeline":
        banned = {"gate", "consensus", "cluster"}
        found = banned.intersection(kinds)
        if found:
            raise SpecError(
                "pipeline pattern cannot contain stages: "
                + ", ".join(sorted(found))
            )

    if pattern == "gated_pipeline":
        if "gate" not in kinds:
            raise SpecError("gated_pipeline pattern requires at least one gate stage")

    if pattern == "autonomous_cluster":
        if "orchestrator" not in kinds:
            raise SpecError(
                "autonomous_cluster pattern requires an orchestrator stage"
            )
        if "cluster" not in kinds:
            raise SpecError("autonomous_cluster pattern requires a cluster stage")

    if pattern == "consensus":
        if "consensus" not in kinds:
            raise SpecError("consensus pattern requires a consensus stage")


def _validate_regex(stage_id: str, pattern: str, field: str) -> None:
    try:
        re.compile(pattern)
    except re.error as exc:
        raise SpecError(
            f"Stage '{stage_id}' sop.{field} has invalid regex '{pattern}': {exc}"
        ) from exc
