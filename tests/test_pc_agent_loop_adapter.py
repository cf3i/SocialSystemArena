from __future__ import annotations

import queue
import threading
from unittest import TestCase
from unittest.mock import patch

from mas_engine.adapters.pc_agent_loop import (
    PcAgentLoopAdapter,
    _AgentContext,
    _parse_agent_output,
)
from mas_engine.core.errors import AdapterError


class _FakeAgent:
    def __init__(self, outputs: list[dict] | None = None) -> None:
        self._outputs = outputs or []
        self.aborted = False

    def put_task(self, query: str, source: str = "mas_engine") -> queue.Queue:
        del query, source
        q: queue.Queue = queue.Queue()
        for item in self._outputs:
            q.put(item)
        return q

    def abort(self) -> None:
        self.aborted = True


class PcAgentLoopAdapterTests(TestCase):
    def test_parse_agent_output_uses_last_decision_object(self) -> None:
        out = (
            "x\n"
            '{"decision":"reject","summary":"first"}\n'
            '{"decision":"approve","summary":"final","updates":{"k":1},"meta":{"m":"v"}}\n'
        )
        result = _parse_agent_output(out)
        self.assertEqual(result.decision, "approve")
        self.assertEqual(result.summary, "final")
        self.assertEqual(result.updates, {"k": 1})
        self.assertEqual(result.meta, {"m": "v"})

    def test_parse_agent_output_fallback_uses_summary_tag(self) -> None:
        out = "abc\n<summary>执行完成</summary>\n"
        result = _parse_agent_output(out)
        self.assertEqual(result.decision, "next")
        self.assertEqual(result.summary, "执行完成")

    def test_dispatch_reads_done_and_returns_result(self) -> None:
        agent = _FakeAgent(
            outputs=[
                {"next": "thinking..."},
                {
                    "done": (
                        "log\n"
                        '{"decision":"approve","summary":"ok","updates":{"x":1}}'
                    )
                },
            ]
        )
        adapter = PcAgentLoopAdapter(agent_root=".")

        with patch.object(
            adapter,
            "_get_context",
            return_value=_AgentContext(agent=agent, thread=threading.Thread()),
        ):
            result = adapter.dispatch(runtime_id="planner", message="test", timeout_sec=2)

        self.assertEqual(result.decision, "approve")
        self.assertEqual(result.summary, "ok")
        self.assertEqual(result.updates, {"x": 1})

    def test_dispatch_timeout_aborts_agent(self) -> None:
        agent = _FakeAgent(outputs=[])
        adapter = PcAgentLoopAdapter(agent_root=".")

        with patch.object(
            adapter,
            "_get_context",
            return_value=_AgentContext(agent=agent, thread=threading.Thread()),
        ):
            with self.assertRaises(AdapterError):
                adapter.dispatch(runtime_id="planner", message="test", timeout_sec=1, retries=1)

        self.assertTrue(agent.aborted)

