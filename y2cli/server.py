"""
Local HTTP server — lets the VS Code webview and browser extension
communicate with y2cli without spawning subprocesses from JS.

Start: y2cli --serve  (default port 7272)

Endpoints:
  GET  /ping
  POST /info       { "url": "..." }
  POST /download   { "url": "...", "format_id": "...", "output_dir": "..." }
  GET  /progress   ?job_id=...
"""

import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import yt_dlp

from y2cli.downloader import fetch_info, build_formats, download
from y2cli import __version__

DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "y2cli")

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _cors(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def _json_response(handler, status: int, data: dict):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    _cors(handler)
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    raw = handler.rfile.read(length)
    return json.loads(raw) if raw else {}


class Y2Handler(BaseHTTPRequestHandler):

    def log_message(self, *_):
        pass  # silence access log

    def do_OPTIONS(self):
        self.send_response(204)
        _cors(self)
        self.end_headers()

    def do_GET(self):
        if self.path == "/ping":
            _json_response(self, 200, {"ok": True, "version": __version__})

        elif self.path.startswith("/progress"):
            job_id = self.path.split("job_id=")[-1] if "job_id=" in self.path else ""
            with _jobs_lock:
                job = _jobs.get(job_id)
            if job is None:
                _json_response(self, 404, {"error": "job not found"})
            else:
                _json_response(self, 200, job)
        else:
            _json_response(self, 404, {"error": "not found"})

    def do_POST(self):
        try:
            body = _read_body(self)
        except Exception as e:
            _json_response(self, 400, {"error": str(e)})
            return

        if self.path == "/info":
            url = body.get("url", "").strip()
            if not url:
                _json_response(self, 400, {"error": "url required"})
                return
            try:
                info = fetch_info(url)
                choices = build_formats(info)
                _json_response(self, 200, {
                    "title":    info.get("title", ""),
                    "uploader": info.get("uploader", ""),
                    "duration": info.get("duration_string") or str(info.get("duration", "")),
                    "thumbnail": info.get("thumbnail", ""),
                    "formats":  [{"id": c["id"], "label": c["label"], "type": c["type"]}
                                 for c in choices],
                })
            except yt_dlp.utils.DownloadError as e:
                _json_response(self, 422, {"error": str(e)})

        elif self.path == "/download":
            url       = body.get("url", "").strip()
            fmt_id    = body.get("format_id", "").strip()
            out_dir   = body.get("output_dir", DEFAULT_DIR).strip() or DEFAULT_DIR

            if not url or not fmt_id:
                _json_response(self, 400, {"error": "url and format_id required"})
                return

            try:
                info    = fetch_info(url)
                choices = build_formats(info)
            except yt_dlp.utils.DownloadError as e:
                _json_response(self, 422, {"error": str(e)})
                return

            fmt = next((c for c in choices if c["id"] == fmt_id), None)
            if fmt is None:
                _json_response(self, 400, {"error": f"unknown format_id '{fmt_id}'"})
                return

            job_id = str(uuid.uuid4())
            with _jobs_lock:
                _jobs[job_id] = {"status": "queued", "percent": "0%",
                                 "speed": "", "eta": "", "filename": ""}

            def _run():
                def hook(d):
                    with _jobs_lock:
                        if d["status"] == "downloading":
                            _jobs[job_id].update({
                                "status":  "downloading",
                                "percent": d.get("_percent_str", "").strip(),
                                "speed":   d.get("_speed_str",   "").strip(),
                                "eta":     d.get("_eta_str",     "").strip(),
                            })
                        elif d["status"] == "finished":
                            _jobs[job_id].update({
                                "status":   "processing",
                                "filename": os.path.basename(d.get("filename", "")),
                            })
                try:
                    download(url, fmt, out_dir, progress_hook=hook)
                    with _jobs_lock:
                        _jobs[job_id]["status"] = "done"
                except Exception as e:
                    with _jobs_lock:
                        _jobs[job_id].update({"status": "error", "error": str(e)})

            threading.Thread(target=_run, daemon=True).start()
            _json_response(self, 202, {"job_id": job_id})

        else:
            _json_response(self, 404, {"error": "not found"})


def run_server(port: int = 7272):
    server = HTTPServer(("127.0.0.1", port), Y2Handler)
    print(f"y2cli server running on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
