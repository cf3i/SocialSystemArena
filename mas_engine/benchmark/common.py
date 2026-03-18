"""Shared helpers for benchmark integrations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..adapters import AgentAdapter, OpenClawAdapter, PcAgentLoopAdapter

_PC_TOOL_MD_RE = re.compile(
    r"\*\*正在调用工具:\*\*\s*`([^`]+)`.*?(?:📥\s*)?\*\*参数:\*\*\s*`{3,4}text\s*(\{.*?\})\s*`{3,4}",
    re.DOTALL,
)
_PC_TOOL_USE_RE = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL | re.IGNORECASE)
_PC_READ_HINT_RE = re.compile(
    r"(?:读取|read(?:ing)?(?:\s+file)?)\s*[`\"']?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)",
    re.IGNORECASE,
)
_PC_WRITE_HINT_RE = re.compile(
    r"(?:写入|保存(?:到)?|write(?:\s+to)?|create(?:d)?)\s*[`\"']?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)",
    re.IGNORECASE,
)


def make_run_dir(base_output: Path) -> Path:
    base = base_output.expanduser().resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / stamp
    nonce = 1
    while run_dir.exists():
        run_dir = base / f"{stamp}-{nonce:02d}"
        nonce += 1
    (run_dir / "traces").mkdir(parents=True, exist_ok=True)
    (run_dir / "workspaces").mkdir(parents=True, exist_ok=True)
    (run_dir / "results").mkdir(parents=True, exist_ok=True)
    return run_dir


def write_result_files(rows: list[dict[str, Any]], summary: dict[str, Any], run_dir: Path) -> None:
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    details = results_dir / "details.jsonl"
    with details.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (results_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_runtime_adapter(
    *,
    adapter: str,
    openclaw_bin: str,
    openclaw_deliver_mode: str,
    openclaw_project_dir: str | None,
    pc_agent_root: str,
    pc_mykey: str | None,
    pc_llm_no: int | None,
    pc_shared_instance: bool,
    source: str = "mas_engine",
) -> tuple[AgentAdapter, bool]:
    mode = str(adapter or "openclaw").strip().lower()
    if mode == "openclaw":
        return (
            OpenClawAdapter(
                executable=openclaw_bin,
                deliver_mode=openclaw_deliver_mode,
                project_dir=openclaw_project_dir,
            ),
            True,
        )
    if mode == "pc-agent-loop":
        return (
            PcAgentLoopAdapter(
                agent_root=pc_agent_root,
                shared_instance=bool(pc_shared_instance),
                llm_no=pc_llm_no,
                mykey_path=pc_mykey,
                source=source,
            ),
            False,
        )
    raise ValueError(
        f"unsupported adapter '{adapter}', expected openclaw or pc-agent-loop"
    )


def make_agent_id(prefix: str, model: str, suffix: str) -> str:
    mslug = _slugify(model, max_len=24)
    digest = hashlib.sha1(f"{model}|{suffix}".encode("utf-8")).hexdigest()[:6]
    ssrc = f"{digest}-{suffix}"
    sslug = _slugify(ssrc, max_len=18)
    return f"{prefix}-{mslug}-{sslug}".strip("-")


def _slugify(src: str, max_len: int = 32) -> str:
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", str(src or "").strip().lower())
    txt = re.sub(r"-+", "-", txt).strip("-")
    return (txt[:max_len].strip("-") or "x")


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def clip01(x: float) -> float:
    if x < 0:
        return 0.0
    if x > 1:
        return 1.0
    return x


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        v = str(row.get(key, ""))
        out[v] = out.get(v, 0) + 1
    return out


def resolve_openclaw_agent_dir(agent_id: str) -> Path:
    base = Path.home() / ".openclaw" / "agents"
    direct = base / agent_id
    if direct.exists():
        return direct
    normalized = base / agent_id.replace(":", "-")
    if normalized.exists():
        return normalized
    return direct


def load_latest_openclaw_transcript(agent_id: str, started_at: float) -> list[dict[str, Any]]:
    agent_dir = resolve_openclaw_agent_dir(agent_id)
    sessions_dir = agent_dir / "sessions"
    if not sessions_dir.exists():
        return []

    files = [p for p in sessions_dir.glob("*.jsonl") if p.is_file()]
    if not files:
        return []

    tolerance = 5.0
    recent = [p for p in files if p.stat().st_mtime >= (started_at - tolerance)]
    target = max((recent or files), key=lambda p: p.stat().st_mtime)

    out: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def extract_pc_agent_loop_transcript(history: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in history:
        summary = str(getattr(event, "summary", "") or "").strip()
        meta = getattr(event, "meta", {})
        raw_tail = ""
        if isinstance(meta, dict):
            raw_tail = str(meta.get("raw_tail", "") or "")

        # Prefer raw_tail (full agent output) over summary (short JSON field).
        # raw_tail contains the agent's natural-language reasoning and answer,
        # which is what LLM judges need to evaluate communication quality.
        text_for_message = raw_tail.strip() or summary
        if text_for_message:
            skey = f"text|{text_for_message}"
            if skey not in seen:
                seen.add(skey)
                rows.append(
                    {
                        "type": "message",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": text_for_message,
                                }
                            ],
                        },
                    }
                )

        tool_calls = _parse_pc_tool_calls(raw_tail)
        tool_calls.extend(
            _infer_pc_tool_calls_from_text("\n".join(x for x in [summary, raw_tail] if x))
        )

        for name, params in tool_calls:
            key = f"{name}|{json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "toolCall",
                                "name": name,
                                "params": params,
                            }
                        ],
                    },
                }
            )
    return rows


def extract_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    out: list[dict[str, Any]] = []
    src = str(text or "")
    i = 0
    while i < len(src):
        if src[i] != "{":
            i += 1
            continue
        try:
            obj, consumed = decoder.raw_decode(src[i:])
        except json.JSONDecodeError:
            i += 1
            continue
        if isinstance(obj, dict):
            out.append(obj)
        i += max(1, consumed)
    return out


def parse_judge_payload(text: str) -> dict[str, Any]:
    objects = extract_json_objects(text)
    if not objects:
        return {}
    for obj in reversed(objects):
        if isinstance(obj, dict) and (
            "scores" in obj or "criteria_scores" in obj or "total" in obj or "score" in obj
        ):
            return obj
    tail = objects[-1]
    return tail if isinstance(tail, dict) else {}


def _infer_pc_tool_calls_from_text(text: str) -> list[tuple[str, dict[str, Any]]]:
    src = str(text or "")
    out: list[tuple[str, dict[str, Any]]] = []
    for m in _PC_READ_HINT_RE.finditer(src):
        path = _clean_path_token(m.group(1))
        if path:
            out.append(("read_file", {"files": [path]}))
    for m in _PC_WRITE_HINT_RE.finditer(src):
        path = _clean_path_token(m.group(1))
        if path:
            out.append(("write_file", {"path": path}))
    return out


def _clean_path_token(raw: str | None) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    txt = txt.strip("`'\"")
    txt = txt.rstrip(".,;:!?)]}，。；：！？")
    if not txt or "://" in txt:
        return ""
    return txt


def _parse_pc_tool_calls(raw_output: str) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    text = str(raw_output or "")
    if not text.strip():
        return calls

    for m in _PC_TOOL_MD_RE.finditer(text):
        name = str(m.group(1) or "").strip()
        args_text = str(m.group(2) or "").strip()
        try:
            args = json.loads(args_text)
        except json.JSONDecodeError:
            args = {}
        if not isinstance(args, dict):
            args = {}
        calls.append(_normalize_pc_tool_call(name, args))

    for tm in _PC_TOOL_USE_RE.finditer(text):
        body = str(tm.group(1) or "")
        for obj in extract_json_objects(body):
            tool_name = str(obj.get("name", obj.get("tool_name", ""))).strip()
            args = obj.get("args", obj.get("arguments", obj.get("params", {})))
            if not isinstance(args, dict):
                args = {}
            if tool_name:
                calls.append(_normalize_pc_tool_call(tool_name, args))
    return calls


def _normalize_pc_tool_call(name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    tool = str(name or "").strip()
    params = dict(args or {})
    if "name" in params and str(params.get("name", "")).strip() == tool:
        params.pop("name", None)

    mapping = {
        "file_read": "read_file",
        "file_write": "write_file",
        "file_patch": "write_file",
        "code_run": "execute_command",
    }
    canonical = mapping.get(tool, tool)
    if canonical == "read_file" and "files" not in params:
        path = params.get("path")
        if isinstance(path, str) and path.strip():
            params["files"] = [path]
        elif isinstance(path, list):
            params["files"] = path
    if canonical == "execute_command" and "command" not in params:
        cmd = params.get("code")
        if isinstance(cmd, str) and cmd.strip():
            params["command"] = cmd
    return canonical, params
