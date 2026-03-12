"""Dashboard HTTP server (API + SSE + static page)."""

from __future__ import annotations

import json
import queue
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .observability.task_manager import TaskRunManager
from .spec.compiler import dump_spec_yaml


def serve_dashboard(
    manager: TaskRunManager,
    host: str = "127.0.0.1",
    port: int = 8787,
) -> None:
    handler_cls = _build_handler(manager)
    httpd = ThreadingHTTPServer((host, int(port)), handler_cls)
    print(f"dashboard serving at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def _build_handler(manager: TaskRunManager) -> type[BaseHTTPRequestHandler]:
    dashboard_html = _load_dashboard_html()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path in {"/", "/index.html"}:
                return self._send_html(dashboard_html)
            if path == "/api/health":
                return self._send_json({"ok": True})
            if path == "/api/tasks":
                return self._send_json({"items": manager.list_tasks()})
            if path == "/api/institutions":
                return self._send_json({"items": manager.list_institutions()})
            if path.startswith("/api/institutions/"):
                return self._handle_institution_get(path)
            if path.startswith("/api/specs/"):
                return self._handle_spec_get(path)
            if path == "/api/spec-topology":
                return self._handle_spec_topology(parsed.query)
            if path.startswith("/api/tasks/") and path.endswith("/events"):
                return self._handle_task_events(path, parsed.query)
            if path.startswith("/api/tasks/") and path.endswith("/stream"):
                return self._handle_task_stream(path, parsed.query)
            if path.startswith("/api/tasks/") and path.endswith("/topology"):
                return self._handle_task_topology(path)
            if path.startswith("/api/tasks/"):
                return self._handle_task_get(path)

            return self._send_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/runs":
                return self._handle_run_create()
            if parsed.path == "/api/specs/validate":
                return self._handle_spec_validate()
            if parsed.path == "/api/specs/to-yaml":
                return self._handle_spec_to_yaml()
            if parsed.path == "/api/institutions/save":
                return self._handle_institution_save()
            return self._send_json({"error": "not found"}, status=404)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            del format, args

        def _send_html(self, text: str, status: int = 200) -> None:
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, obj: Any, status: int = 200) -> None:
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            raw_len = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_len)
            except ValueError:
                length = 0
            payload = self.rfile.read(max(0, length))
            if not payload:
                return {}
            obj = json.loads(payload.decode("utf-8"))
            if not isinstance(obj, dict):
                raise ValueError("json body must be object")
            return obj

        def _task_id_from_path(self, path: str) -> str:
            parts = [p for p in path.split("/") if p]
            # /api/tasks/{task_id}(/...)
            if len(parts) < 3:
                raise KeyError("invalid task path")
            return unquote(parts[2])

        def _institution_id_from_path(self, path: str) -> str:
            parts = [p for p in path.split("/") if p]
            # /api/institutions/{institution_id}
            if len(parts) < 3:
                raise KeyError("invalid institution path")
            return unquote(parts[2])

        def _spec_id_from_path(self, path: str) -> str:
            parts = [p for p in path.split("/") if p]
            # /api/specs/{spec_id}
            if len(parts) < 3:
                raise KeyError("invalid spec path")
            return unquote(parts[2])

        def _handle_run_create(self) -> None:
            try:
                payload = self._read_json()
                task = manager.start_run(payload)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"ok": True, "task": task}, status=HTTPStatus.CREATED)

        def _handle_spec_topology(self, query: str) -> None:
            q = parse_qs(query)
            spec = (q.get("spec") or [""])[0].strip()
            try:
                spec_inline = (q.get("spec_inline") or [""])[0]
                spec_format = (q.get("spec_format") or [""])[0].strip() or "yaml"
                spec_id = (q.get("spec_id") or [""])[0].strip()
                institution_id = (q.get("institution_id") or [""])[0].strip()
                if spec_inline:
                    data = manager.preview_topology_inline(spec_inline, spec_format)
                elif spec or spec_id or institution_id:
                    resolved = manager.validate_spec_payload(
                        {
                            "spec": spec,
                            "spec_id": spec_id,
                            "institution_id": institution_id,
                        }
                    )
                    data = resolved["topology"]
                else:
                    return self._send_json(
                        {
                            "error": "provide one of spec/spec_id/institution_id/spec_inline"
                        },
                        status=400,
                    )
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"topology": data})

        def _handle_institution_get(self, path: str) -> None:
            try:
                institution_id = self._institution_id_from_path(path)
                data = manager.get_institution(institution_id)
            except KeyError:
                return self._send_json({"error": "institution not found"}, status=404)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"institution": data})

        def _handle_spec_get(self, path: str) -> None:
            try:
                spec_id = self._spec_id_from_path(path)
                data = manager.get_spec_text(spec_id)
            except KeyError:
                return self._send_json({"error": "spec not found"}, status=404)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"spec": data})

        def _handle_spec_validate(self) -> None:
            try:
                payload = self._read_json()
                data = manager.validate_spec_payload(payload)
            except Exception as exc:
                return self._send_json({"ok": False, "error": str(exc)}, status=400)
            return self._send_json(data)

        def _handle_spec_to_yaml(self) -> None:
            try:
                payload = self._read_json()
                spec_obj = payload.get("spec_obj")
                if not isinstance(spec_obj, dict):
                    raise ValueError("spec_obj must be an object")
                text = dump_spec_yaml(spec_obj)
            except Exception as exc:
                return self._send_json({"ok": False, "error": str(exc)}, status=400)
            return self._send_json({"ok": True, "spec_text": text})

        def _handle_institution_save(self) -> None:
            try:
                payload = self._read_json()
                data = manager.save_institution_spec(payload)
            except Exception as exc:
                return self._send_json({"ok": False, "error": str(exc)}, status=400)
            return self._send_json(data, status=HTTPStatus.CREATED)

        def _handle_task_get(self, path: str) -> None:
            try:
                task_id = self._task_id_from_path(path)
                row = manager.get_task(task_id)
            except KeyError:
                return self._send_json({"error": "task not found"}, status=404)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"task": row})

        def _handle_task_topology(self, path: str) -> None:
            try:
                task_id = self._task_id_from_path(path)
                topology = manager.get_task_topology(task_id)
            except KeyError:
                return self._send_json({"error": "task not found"}, status=404)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"topology": topology})

        def _handle_task_events(self, path: str, query: str) -> None:
            q = parse_qs(query)
            try:
                task_id = self._task_id_from_path(path)
                since = int((q.get("since") or ["0"])[0])
                limit = int((q.get("limit") or ["200"])[0])
                rows = manager.get_events(task_id, since_seq=since, limit=limit)
            except ValueError:
                return self._send_json({"error": "invalid since/limit"}, status=400)
            except KeyError:
                return self._send_json({"error": "task not found"}, status=404)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"items": rows})

        def _handle_task_stream(self, path: str, query: str) -> None:
            q = parse_qs(query)
            try:
                task_id = self._task_id_from_path(path)
                since = int((q.get("since") or ["0"])[0])
                sub, close_sub = manager.event_stream.subscribe(task_id, since_seq=since)
            except ValueError:
                return self._send_json({"error": "invalid since"}, status=400)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=400)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                # Initial ping.
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        row = sub.get(timeout=15.0)
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        continue

                    payload = json.dumps(row, ensure_ascii=False)
                    msg = (
                        f"id: {row.get('stream_seq', 0)}\n"
                        f"event: {row.get('record_type', 'event')}\n"
                        f"data: {payload}\n\n"
                    )
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                close_sub()

    return Handler


def _load_dashboard_html() -> str:
    src = Path(__file__).resolve().parent / "web" / "dashboard.html"
    if src.exists():
        return src.read_text(encoding="utf-8")

    return """
<!doctype html>
<html><body><h1>Dashboard HTML missing</h1></body></html>
"""
