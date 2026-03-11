"""OpenClaw CLI adapter."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field

from ..core.errors import AdapterError
from ..core.types import AgentResult


_DELIVER_MODES = {"auto", "always", "never"}


@dataclass
class OpenClawAdapter:
    executable: str = "openclaw"
    deliver_mode: str = "auto"
    project_dir: str | None = None
    extra_env: dict[str, str] = field(default_factory=dict)

    def dispatch(
        self,
        runtime_id: str,
        message: str,
        timeout_sec: int = 300,
        retries: int = 1,
    ) -> AgentResult:
        if self.deliver_mode not in _DELIVER_MODES:
            raise AdapterError(
                f"Invalid deliver_mode '{self.deliver_mode}', "
                "must be one of: auto|always|never"
            )

        err = ""
        command_variants = _build_command_variants(
            executable=self.executable,
            runtime_id=runtime_id,
            message=message,
            timeout_sec=timeout_sec,
            deliver_mode=self.deliver_mode,
        )

        env = os.environ.copy()
        env.update(self.extra_env)

        for _ in range(max(1, retries)):
            for idx, cmd in enumerate(command_variants):
                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_sec + 10,
                        check=False,
                        cwd=self.project_dir or None,
                        env=env,
                    )
                except FileNotFoundError as exc:
                    raise AdapterError(
                        "openclaw executable not found. "
                        "Install OpenClaw or use mock adapter."
                    ) from exc
                except subprocess.TimeoutExpired:
                    err = f"timeout after {timeout_sec}s"
                    break

                out = (proc.stdout or "") + "\n" + (proc.stderr or "")
                if proc.returncode == 0:
                    return _parse_agent_output(out)

                err = out[-500:]
                if idx + 1 < len(command_variants) and _should_fallback_to_next(
                    cmd=cmd,
                    output=out,
                    deliver_mode=self.deliver_mode,
                ):
                    continue
                break

        raise AdapterError(f"OpenClaw dispatch failed for {runtime_id}: {err}")


def _build_command_variants(
    executable: str,
    runtime_id: str,
    message: str,
    timeout_sec: int,
    deliver_mode: str,
) -> list[list[str]]:
    base = [
        executable,
        "agent",
        "--agent",
        runtime_id,
        "-m",
        message,
        "--timeout",
        str(timeout_sec),
    ]
    with_deliver = [*base, "--deliver"]

    if deliver_mode == "always":
        return [with_deliver]
    if deliver_mode == "never":
        return [base]
    return [with_deliver, base]


def _should_fallback_to_next(cmd: list[str], output: str, deliver_mode: str) -> bool:
    if deliver_mode != "auto":
        return False
    if "--deliver" not in cmd:
        return False

    low = output.lower()
    return (
        ("unknown flag" in low and "--deliver" in low)
        or ("flag provided but not defined" in low and "deliver" in low)
        or ("unrecognized arguments" in low and "--deliver" in low)
    )


def _extract_json_objects(output: str) -> list[dict]:
    decoder = json.JSONDecoder()
    objects: list[dict] = []
    i = 0
    while i < len(output):
        if output[i] != "{":
            i += 1
            continue

        try:
            obj, consumed = decoder.raw_decode(output[i:])
        except json.JSONDecodeError:
            i += 1
            continue

        if isinstance(obj, dict):
            objects.append(obj)
        i += max(1, consumed)

    return objects


def _parse_agent_output(output: str) -> AgentResult:
    """Parse the latest JSON decision from CLI output."""
    for obj in reversed(_extract_json_objects(output)):
        if "decision" in obj:
            updates = obj.get("updates", {})
            meta = obj.get("meta", {})
            return AgentResult(
                decision=str(obj.get("decision", "next")),
                summary=str(obj.get("summary", "")),
                raw_output=output[-2000:],
                updates=updates if isinstance(updates, dict) else {},
                meta=meta if isinstance(meta, dict) else {},
            )

    # Fallback: treat as plain text success.
    return AgentResult(
        decision="next",
        summary=output.strip().splitlines()[-1][:200] if output.strip() else "",
        raw_output=output[-2000:],
        updates={},
    )
