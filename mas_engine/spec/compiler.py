"""Compiler for governance specs (CUE/JSON -> in-memory IR)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ..core.errors import SpecError
from ..core.types import (
    AgentSpec,
    ClusterMember,
    ConsensusConfig,
    FeatureSpec,
    GovernanceSpec,
    MetaSpec,
    PolicySpec,
    StageSpec,
    TransitionSpec,
)
from .validators import validate_spec


def compile_spec(path: str | Path) -> GovernanceSpec:
    src = Path(path).expanduser()
    if not src.exists():
        raise SpecError(f"Spec not found: {src}")
    src = src.resolve()

    raw = _load_raw(src)
    spec = _parse_raw(raw)
    validate_spec(spec)
    return spec


def export_ir_json(spec: GovernanceSpec) -> dict[str, Any]:
    return {
        "meta": {
            "id": spec.meta.id,
            "name": spec.meta.name,
            "version": spec.meta.version,
            "pattern": spec.meta.pattern,
            "description": spec.meta.description,
        },
        "entry_stage": spec.entry_stage,
        "agents": {
            k: {
                "id": v.id,
                "runtime_id": v.runtime_id,
                "role": v.role,
                "instructions": v.instructions,
                "timeout_sec": v.timeout_sec,
                "retries": v.retries,
            }
            for k, v in spec.agents.items()
        },
        "stages": [
            {
                "id": s.id,
                "kind": s.kind,
                "agent": s.agent,
                "description": s.description,
                "prompt_template": s.prompt_template,
                "default_decision": s.default_decision,
                "transitions": [
                    {"decision": t.decision, "to": t.to} for t in s.transitions
                ],
                "consensus": (
                    {
                        "voters": s.consensus.voters,
                        "algorithm": s.consensus.algorithm,
                        "threshold": s.consensus.threshold,
                        "tie_breaker": s.consensus.tie_breaker,
                        "weights": s.consensus.weights,
                    }
                    if s.consensus
                    else None
                ),
                "cluster_members": [
                    {
                        "agent": m.agent,
                        "role": m.role,
                        "required": m.required,
                    }
                    for m in s.cluster_members
                ],
            }
            for s in spec.stages
        ],
        "features": [
            {"name": f.name, "enabled": f.enabled, "config": f.config}
            for f in spec.features
        ],
        "policy": {
            "banned_terms": spec.policy.banned_terms,
            "require_json_decision": spec.policy.require_json_decision,
            "max_steps": spec.policy.max_steps,
        },
    }


def _load_raw(src: Path) -> dict[str, Any]:
    suffix = src.suffix.lower()
    if suffix == ".json":
        return json.loads(src.read_text())
    if suffix in {".yaml", ".yml"}:
        return _load_yaml(src)
    if suffix == ".cue":
        return _load_cue(src)
    raise SpecError(f"Unsupported spec format: {src.suffix}. Use .cue/.json/.yaml")


def _load_yaml(src: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SpecError(
            "YAML spec requires PyYAML. Install with `pip install pyyaml`."
        ) from exc

    try:
        raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SpecError(f"YAML parse failed: {exc}") from exc

    if not isinstance(raw, dict):
        raise SpecError("YAML root must be an object")
    return raw


def _load_cue(src: Path) -> dict[str, Any]:
    cmd = ["cue", "export", src.name, "--out", "json"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(src.parent),
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise SpecError(
            "`cue` is not installed. Install CUE and retry, "
            "or compile to JSON first."
        ) from exc

    if proc.returncode != 0:
        raise SpecError(f"CUE export failed:\n{proc.stderr.strip()}")

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SpecError("CUE export produced invalid JSON") from exc


def _parse_raw(raw: dict[str, Any]) -> GovernanceSpec:
    meta_raw = _require_obj(raw, "meta")
    meta = MetaSpec(
        id=_require_str(meta_raw, "id"),
        name=_require_str(meta_raw, "name"),
        version=str(meta_raw.get("version", "0.1.0")),
        pattern=_require_str(meta_raw, "pattern"),
        description=str(meta_raw.get("description", "")),
    )

    agents_raw = _require_obj(raw, "agents")
    agents: dict[str, AgentSpec] = {}
    for key, val in agents_raw.items():
        val_obj = _as_obj(val, f"agents.{key}")
        agents[key] = AgentSpec(
            id=key,
            runtime_id=str(val_obj.get("runtime_id", key)),
            role=str(val_obj.get("role", "")),
            instructions=str(val_obj.get("instructions", "")),
            timeout_sec=int(val_obj.get("timeout_sec", 300)),
            retries=int(val_obj.get("retries", 1)),
        )

    stages_list = _require_list(raw, "stages")
    stages: list[StageSpec] = []
    for idx, item in enumerate(stages_list):
        item_obj = _as_obj(item, f"stages[{idx}]")
        transitions_raw = item_obj.get("transitions", [])
        transitions = [
            TransitionSpec(
                decision=_require_str(t, "decision"),
                to=_require_str(t, "to"),
            )
            for t in (_as_obj(x, f"stages[{idx}].transitions") for x in transitions_raw)
        ]

        consensus_obj = item_obj.get("consensus")
        consensus = None
        if consensus_obj is not None:
            c = _as_obj(consensus_obj, f"stages[{idx}].consensus")
            voters = c.get("voters", [])
            if not isinstance(voters, list):
                raise SpecError(f"stages[{idx}].consensus.voters must be list")
            consensus = ConsensusConfig(
                voters=[str(v) for v in voters],
                algorithm=str(c.get("algorithm", "majority")),
                threshold=float(c.get("threshold", 0.5)),
                tie_breaker=str(c.get("tie_breaker", "reject")),
                weights={
                    str(k): float(v)
                    for k, v in _as_obj(
                        c.get("weights", {}),
                        f"stages[{idx}].consensus.weights",
                    ).items()
                },
            )

        members = []
        members_raw = item_obj.get("cluster_members", [])
        if members_raw:
            if not isinstance(members_raw, list):
                raise SpecError(f"stages[{idx}].cluster_members must be list")
            for m in members_raw:
                mobj = _as_obj(m, f"stages[{idx}].cluster_members[]")
                members.append(
                    ClusterMember(
                        agent=_require_str(mobj, "agent"),
                        role=str(mobj.get("role", "executor")),
                        required=bool(mobj.get("required", True)),
                    )
                )

        stages.append(
            StageSpec(
                id=_require_str(item_obj, "id"),
                kind=_require_str(item_obj, "kind"),
                agent=(str(item_obj["agent"]) if "agent" in item_obj else None),
                description=str(item_obj.get("description", "")),
                prompt_template=str(item_obj.get("prompt_template", "")),
                transitions=transitions,
                consensus=consensus,
                cluster_members=members,
                default_decision=str(item_obj.get("default_decision", "next")),
            )
        )

    features_raw = raw.get("features", [])
    if not isinstance(features_raw, list):
        raise SpecError("features must be a list")
    features = []
    for idx, f in enumerate(features_raw):
        fobj = _as_obj(f, f"features[{idx}]")
        features.append(
            FeatureSpec(
                name=_require_str(fobj, "name"),
                enabled=bool(fobj.get("enabled", True)),
                config=_as_obj(fobj.get("config", {}), f"features[{idx}].config"),
            )
        )

    policy_raw = _as_obj(raw.get("policy", {}), "policy")
    banned = policy_raw.get("banned_terms", [])
    if not isinstance(banned, list):
        raise SpecError("policy.banned_terms must be list")
    policy = PolicySpec(
        banned_terms=[str(x) for x in banned],
        require_json_decision=bool(policy_raw.get("require_json_decision", True)),
        max_steps=int(policy_raw.get("max_steps", 64)),
    )

    return GovernanceSpec(
        meta=meta,
        agents=agents,
        entry_stage=_require_str(raw, "entry_stage"),
        stages=stages,
        features=features,
        policy=policy,
    )


def _as_obj(val: Any, name: str) -> dict[str, Any]:
    if not isinstance(val, dict):
        raise SpecError(f"{name} must be an object")
    return val


def _require_obj(raw: dict[str, Any], key: str) -> dict[str, Any]:
    if key not in raw:
        raise SpecError(f"Missing required key: {key}")
    return _as_obj(raw[key], key)


def _require_list(raw: dict[str, Any], key: str) -> list[Any]:
    if key not in raw:
        raise SpecError(f"Missing required key: {key}")
    val = raw[key]
    if not isinstance(val, list):
        raise SpecError(f"{key} must be a list")
    return val


def _require_str(raw: dict[str, Any], key: str) -> str:
    if key not in raw:
        raise SpecError(f"Missing required key: {key}")
    val = raw[key]
    if not isinstance(val, str) or not val.strip():
        raise SpecError(f"{key} must be a non-empty string")
    return val
