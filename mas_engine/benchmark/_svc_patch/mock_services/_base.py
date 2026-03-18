"""Patch for mock_services._base — adds dispatch-logging middleware on top of
the original ErrorInjectionMiddleware without touching claw-eval source.

Loaded via PYTHONPATH prepend by clawebench._start_mock_services.
The real _base.py is loaded directly by file path to avoid recursive import.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Load the real _base.py by absolute file path (avoids any sys.path games)
# ---------------------------------------------------------------------------

def _find_real_base() -> Path:
    """Walk sys.path entries to find the claw-eval mock_services/_base.py,
    skipping our own patch directory."""
    _our_dir = str(Path(__file__).resolve().parent.parent)  # _svc_patch/
    for entry in sys.path:
        if entry == _our_dir:
            continue
        candidate = Path(entry) / "mock_services" / "_base.py"
        if candidate.exists():
            return candidate.resolve()
    raise ImportError("Could not find the real mock_services/_base.py in sys.path")


def _load_real_base():
    real_path = _find_real_base()
    spec = importlib.util.spec_from_file_location("_mock_services_base_real", real_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_real_base = _load_real_base()

# Re-export original symbols so existing imports stay working
ErrorInjectionMiddleware = _real_base.ErrorInjectionMiddleware

# ---------------------------------------------------------------------------
# Dispatch-logging middleware
# ---------------------------------------------------------------------------

_EXEMPT_SUFFIXES = ("/audit", "/reset", "/health", "/docs", "/openapi.json")

# endpoint path → logical tool_name (matches task.yaml tool names)
_ENDPOINT_TO_TOOL: dict[str, str] = {
    "/gmail/messages/get":     "gmail_get_message",
    "/gmail/messages":         "gmail_list_messages",
    "/gmail/send":             "gmail_send_message",
    "/gmail/drafts/save":      "gmail_save_draft",
    "/calendar/events/create": "calendar_create_event",
    "/calendar/events/update": "calendar_update_event",
    "/calendar/events/delete": "calendar_delete_event",
    "/calendar/events":        "calendar_list_events",
    "/todo/tasks/create":      "todo_create_task",
    "/todo/tasks/update":      "todo_update_task",
    "/todo/tasks/delete":      "todo_delete_task",
    "/todo/tasks":             "todo_list_tasks",
    "/contacts/search":        "contacts_search",
    "/contacts/get":           "contacts_get",
    "/contacts/send_message":  "contacts_send_message",
}

def _path_to_tool_name(path: str) -> str:
    for fragment, name in sorted(_ENDPOINT_TO_TOOL.items(), key=lambda x: -len(x[0])):
        if path == fragment or path.startswith(fragment + "/"):
            return name
    return path.strip("/").replace("/", "_") or "unknown"


try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    from fastapi import Request

    class DispatchLogMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            log_file = os.environ.get("DISPATCH_LOG_FILE", "")
            trace_id = os.environ.get("DISPATCH_TRACE_ID", "unknown")
            path = request.url.path

            if (not log_file
                    or any(path.endswith(s) for s in _EXEMPT_SUFFIXES)
                    or request.headers.get("X-Health-Check") == "1"
                    or request.method != "POST"):
                return await call_next(request)

            body_bytes = await request.body()
            try:
                req_body = json.loads(body_bytes) if body_bytes else {}
            except Exception:
                req_body = {"_raw": body_bytes.decode(errors="replace")}

            t0 = time.monotonic()
            response = await call_next(request)
            latency_ms = round((time.monotonic() - t0) * 1000, 1)

            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk)
            resp_bytes = b"".join(chunks)
            try:
                resp_body = json.loads(resp_bytes) if resp_bytes else {}
            except Exception:
                resp_body = {"_raw": resp_bytes.decode(errors="replace")}

            port = request.url.port or 80
            record = {
                "type": "tool_dispatch",
                "trace_id": trace_id,
                "tool_use_id": str(uuid.uuid4()),
                "tool_name": _path_to_tool_name(path),
                "endpoint_url": f"http://localhost:{port}{path}",
                "request_body": req_body,
                "response_status": response.status_code,
                "response_body": resp_body,
                "latency_ms": latency_ms,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            try:
                with open(log_file, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception:
                pass

            return Response(
                content=resp_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

    def add_error_injection(app):
        """Patched: original error injection + dispatch logging."""
        _real_base.add_error_injection(app)
        app.add_middleware(DispatchLogMiddleware)

except ImportError:
    # FastAPI not available — fall back silently
    add_error_injection = _real_base.add_error_injection
