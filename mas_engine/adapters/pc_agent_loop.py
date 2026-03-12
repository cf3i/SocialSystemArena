"""pc-agent-loop adapter."""

from __future__ import annotations

import importlib.util
import json
import logging
import queue
import re
import sys
import threading
import time
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.errors import AdapterError
from ..core.types import AgentResult

_LOG = logging.getLogger("mas_engine.adapter.pc_agent_loop")


@dataclass
class _AgentContext:
    agent: Any
    thread: threading.Thread


@dataclass
class PcAgentLoopAdapter:
    """Adapter that routes stage prompts into pc-agent-loop runtime."""

    agent_root: str = "third_party/pc-agent-loop"
    shared_instance: bool = False
    llm_no: int | None = None
    mykey_path: str | None = None
    source: str = "mas_engine"

    _contexts: dict[str, _AgentContext] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _agent_class: type | None = field(default=None, init=False, repr=False)

    def dispatch(
        self,
        runtime_id: str,
        message: str,
        timeout_sec: int = 300,
        retries: int = 1,
    ) -> AgentResult:
        _LOG.info(
            "dispatch runtime=%s shared_instance=%s timeout=%s retries=%s",
            runtime_id,
            self.shared_instance,
            timeout_sec,
            retries,
        )
        err = ""
        for _ in range(max(1, retries)):
            try:
                return self._dispatch_once(runtime_id, message, timeout_sec)
            except AdapterError as exc:
                err = str(exc)
                _LOG.warning("dispatch retry runtime=%s error=%s", runtime_id, err)
        raise AdapterError(f"pc-agent-loop dispatch failed for {runtime_id}: {err}")

    def _dispatch_once(self, runtime_id: str, message: str, timeout_sec: int) -> AgentResult:
        key = "__shared__" if self.shared_instance else runtime_id
        context = self._get_context(key)

        try:
            display_queue = context.agent.put_task(message, source=self.source)
        except Exception as exc:
            raise AdapterError(f"failed to submit task: {exc}") from exc

        output = self._wait_done(context.agent, display_queue, timeout_sec)
        return _parse_agent_output(output)

    def _wait_done(self, agent: Any, display_queue: queue.Queue, timeout_sec: int) -> str:
        start = time.monotonic()
        last_chunk = ""
        while True:
            remain = timeout_sec - (time.monotonic() - start)
            if remain <= 0:
                self._abort_agent(agent)
                tail = last_chunk[-160:] if last_chunk else ""
                if tail:
                    raise AdapterError(f"timeout after {timeout_sec}s; last chunk: {tail}")
                raise AdapterError(f"timeout after {timeout_sec}s")

            try:
                item = display_queue.get(timeout=min(1.0, max(0.1, remain)))
            except queue.Empty:
                continue

            if not isinstance(item, dict):
                continue

            if "done" in item:
                return str(item.get("done", ""))

            if "next" in item:
                last_chunk = str(item.get("next", ""))

    def _abort_agent(self, agent: Any) -> None:
        try:
            if hasattr(agent, "abort"):
                agent.abort()
        except Exception:
            return

    def _get_context(self, runtime_key: str) -> _AgentContext:
        with self._lock:
            existing = self._contexts.get(runtime_key)
            if existing is not None:
                return existing

            context = self._create_context(runtime_key)
            self._contexts[runtime_key] = context
            _LOG.info("created runtime context: %s", runtime_key)
            return context

    def _create_context(self, runtime_key: str) -> _AgentContext:
        agent_cls = self._load_generatic_agent_class()

        try:
            agent = agent_cls()
        except Exception as exc:
            raise AdapterError(
                "failed to create pc-agent-loop GeneraticAgent. "
                "Check mykey.py/mykey.json and backend connectivity."
            ) from exc

        llm_client = getattr(agent, "llmclient", None)
        backends = getattr(llm_client, "backends", []) if llm_client is not None else []
        if not backends:
            raise AdapterError(
                "pc-agent-loop has no available LLM backend. "
                "Configure third_party/pc-agent-loop/mykey.py or pass --pc-mykey."
            )

        if self.llm_no is not None:
            try:
                agent.llm_no = int(self.llm_no) % len(backends)
            except Exception as exc:
                raise AdapterError(f"invalid llm_no '{self.llm_no}': {exc}") from exc

        if hasattr(agent, "verbose"):
            agent.verbose = False
        if hasattr(agent, "inc_out"):
            agent.inc_out = False

        thread = threading.Thread(
            target=agent.run,
            daemon=True,
            name=f"pc-agent-loop-{runtime_key}",
        )
        thread.start()
        return _AgentContext(agent=agent, thread=thread)

    def _load_generatic_agent_class(self) -> type:
        if self._agent_class is not None:
            return self._agent_class

        root = Path(self.agent_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise AdapterError(f"pc-agent-loop root not found: {root}")

        agentmain_path = root / "agentmain.py"
        if not agentmain_path.exists():
            raise AdapterError(f"agentmain.py not found under: {root}")

        self._inject_mykey_module(root)

        root_text = str(root)
        if root_text not in sys.path:
            sys.path.insert(0, root_text)

        mod_name = f"pc_agent_loop_agentmain_{abs(hash(root_text))}"
        module = sys.modules.get(mod_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(mod_name, agentmain_path)
            if spec is None or spec.loader is None:
                raise AdapterError(f"cannot load pc-agent-loop from {agentmain_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = module
            try:
                spec.loader.exec_module(module)
            except Exception as exc:
                raise AdapterError(
                    "failed to import pc-agent-loop agentmain. "
                    "Check dependencies and mykey settings."
                ) from exc

        agent_cls = getattr(module, "GeneraticAgent", None)
        if agent_cls is None:
            raise AdapterError("GeneraticAgent class not found in agentmain.py")

        self._agent_class = agent_cls
        return agent_cls

    def _inject_mykey_module(self, root: Path) -> None:
        if not self.mykey_path:
            return

        cfg_path = Path(self.mykey_path).expanduser()
        if not cfg_path.is_absolute():
            cfg_path = (Path.cwd() / cfg_path).resolve()
        else:
            cfg_path = cfg_path.resolve()

        if cfg_path.is_dir():
            py_path = cfg_path / "mykey.py"
            json_path = cfg_path / "mykey.json"
            if py_path.exists():
                cfg_path = py_path
            elif json_path.exists():
                cfg_path = json_path
            else:
                raise AdapterError(f"mykey config not found in directory: {cfg_path}")

        if not cfg_path.exists():
            raise AdapterError(f"mykey config not found: {cfg_path}")

        if cfg_path.suffix.lower() == ".py":
            spec = importlib.util.spec_from_file_location("mykey", cfg_path)
            if spec is None or spec.loader is None:
                raise AdapterError(f"cannot load mykey module from: {cfg_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules["mykey"] = module
            return

        if cfg_path.suffix.lower() == ".json":
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise AdapterError(f"invalid mykey json: {cfg_path}") from exc
            if not isinstance(data, dict):
                raise AdapterError(f"mykey json must be object: {cfg_path}")
            module = types.ModuleType("mykey")
            for k, v in data.items():
                setattr(module, k, v)
            sys.modules["mykey"] = module
            return

        raise AdapterError(
            f"unsupported mykey file type '{cfg_path.suffix}', expected .py/.json"
        )


def _extract_json_objects(output: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
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


def _fallback_summary(output: str) -> str:
    summaries = re.findall(r"<summary>(.*?)</summary>", output, flags=re.DOTALL)
    if summaries:
        text = summaries[-1].strip()
        if text:
            return text[:200]

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[-1][:200]


def _parse_agent_output(output: str) -> AgentResult:
    for obj in reversed(_extract_json_objects(output)):
        if "decision" not in obj:
            continue
        updates = obj.get("updates")
        meta = obj.get("meta")
        return AgentResult(
            decision=str(obj.get("decision", "next")),
            summary=str(obj.get("summary", "")),
            raw_output=output[-2000:],
            updates=updates if isinstance(updates, dict) else {},
            meta=meta if isinstance(meta, dict) else {},
        )

    return AgentResult(
        decision="next",
        summary=_fallback_summary(output),
        raw_output=output[-2000:],
        updates={},
    )
