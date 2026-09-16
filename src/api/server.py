# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Local REST API Server implementation for El Secretario."""

import os
import sys
import json
import secrets
import logging
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PyQt6.QtCore import QThread, pyqtSignal, QObject

from src.database import DBManager
from src.rag_engine import RAGEngine

logger = logging.getLogger("ElSecretario.LocalAPI")


class APISignals(QObject):
    """Safe thread-boundary PyQt signals coordinator."""

    sig_start_recording = pyqtSignal()
    sig_stop_recording = pyqtSignal()
    sig_create_task = pyqtSignal(dict)  # Dictionary of task parameters


class LocalAPIRequestHandler(BaseHTTPRequestHandler):
    """Handles incoming local loopback REST requests for El Secretario."""

    # Protocol version to support keep-alive if necessary
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        # Override to log through Python logging module instead of printing to stderr
        logger.debug(f"{self.client_address[0]} - {format % args}")

    def _send_json(self, status_code: int, data: any):
        """Helper to serialize and return JSON responses."""
        try:
            response_bytes = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            # CORS headers to support local browser integrations
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            logger.error(f"Error sending JSON response: {e}")

    def _check_auth(self) -> bool:
        """Enforces security checks by verifying the localhost Bearer token."""
        # Fast path: reject any request not originating from loopback interface
        if self.client_address[0] != "127.0.0.1":
            self.send_error(403, "Forbidden: Connection allowed only from localhost.")
            return False

        auth_header = self.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            self._send_json(401, {"success": False, "error": "Unauthorized: Missing Bearer token."})
            return False

        token = auth_header.split(" ")[1].strip()
        if token != self.server.token:
            self._send_json(401, {"success": False, "error": "Unauthorized: Invalid Bearer token."})
            return False

        return True

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if not self._check_auth():
            return

        # 1. GET /api/v1/status
        if path == "/api/v1/status":
            self._send_json(200, self.server.thread.get_live_status())
            return

        # 2. GET /api/v1/recordings
        elif path == "/api/v1/recordings":
            try:
                query_params = urllib.parse.parse_qs(parsed_url.query)
                limit = int(query_params.get("limit", [50])[0])
                offset = int(query_params.get("offset", [0])[0])

                # Fetch all recordings
                all_recs = self.server.db.fetch_all()
                paginated_recs = []
                for rec in all_recs[offset : offset + limit]:
                    paginated_recs.append({
                        "id": rec.get("id"),
                        "title": rec.get("title") or "Untitled",
                        "date": rec.get("created_at"),
                        "duration_seconds": rec.get("duration"),
                        "summary_generated": bool(rec.get("summary")),
                        "tags": [t.strip() for t in (rec.get("tags") or "").split(",") if t.strip()]
                    })
                self._send_json(200, paginated_recs)
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        # 3. GET /api/v1/recordings/{id}
        elif path.startswith("/api/v1/recordings/"):
            try:
                record_id_str = path.split("/")[-1]
                record_id = int(record_id_str)
                rec = self.server.db.fetch_record(record_id)
                if not rec:
                    self._send_json(404, {"success": False, "error": f"Recording {record_id} not found."})
                    return

                self._send_json(200, {
                    "id": rec.get("id"),
                    "title": rec.get("title") or "Untitled",
                    "date": rec.get("created_at"),
                    "duration_seconds": rec.get("duration"),
                    "transcript": rec.get("transcription") or "",
                    "notes": rec.get("recording_notes") or "",
                    "summary": rec.get("summary") or "",
                    "tags": [t.strip() for t in (rec.get("tags") or "").split(",") if t.strip()]
                })
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        # 4. GET /api/v1/tasks
        elif path == "/api/v1/tasks":
            try:
                tasks = self.server.db.get_tasks_for_board(include_completed=True)
                formatted_tasks = []
                for t in tasks:
                    formatted_tasks.append({
                        "id": t.get("id"),
                        "title": t.get("content"),
                        "description": t.get("notes") or "",
                        "due_date": t.get("day_date") or "",
                        "completed": bool(t.get("completed"))
                    })
                self._send_json(200, formatted_tasks)
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        # 5. GET /api/v1/search
        elif path == "/api/v1/search":
            try:
                query_params = urllib.parse.parse_qs(parsed_url.query)
                query_str = query_params.get("query", [""])[0].strip()
                if not query_str:
                    self._send_json(400, {"success": False, "error": "Query parameter is required."})
                    return

                # Query RAG Engine
                results = self.server.rag.search(query_str, n_results=10)
                formatted_results = []
                for res in results:
                    score = 1.0 - res.get("distance", 0.0) if "distance" in res else 1.0
                    formatted_results.append({
                        "source": "recording",
                        "source_id": int(res.get("id")) if res.get("id") else None,
                        "title": res.get("metadata", {}).get("title", "Untitled"),
                        "text": res.get("text") or "",
                        "relevance_score": round(score, 2)
                    })
                self._send_json(200, {
                    "query": query_str,
                    "results": formatted_results
                })
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        else:
            self._send_json(404, {"success": False, "error": f"Endpoint GET {path} not found."})

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if not self._check_auth():
            return

        # Read POST body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
            body = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._send_json(400, {"success": False, "error": f"Invalid JSON payload: {e}"})
            return

        # 1. POST /api/v1/record/start
        if path == "/api/v1/record/start":
            status = self.server.thread.get_live_status().get("status")
            if status == "recording":
                self._send_json(409, {"success": False, "error": "Application is already recording."})
                return

            # Emit safely to Main Thread!
            self.server.signals.sig_start_recording.emit()
            self._send_json(200, {"success": True, "message": "Recording session initiated successfully."})
            return

        # 2. POST /api/v1/record/stop
        elif path == "/api/v1/record/stop":
            status = self.server.thread.get_live_status().get("status")
            if status != "recording":
                self._send_json(409, {"success": False, "error": "Application is not currently recording."})
                return

            # Emit safely to Main Thread!
            self.server.signals.sig_stop_recording.emit()
            self._send_json(200, {"success": True, "message": "Recording stopped. Sent to transcription queue."})
            return

        # 3. POST /api/v1/tasks
        elif path == "/api/v1/tasks":
            title = body.get("title", "").strip()
            if not title:
                self._send_json(400, {"success": False, "error": "Task title is required."})
                return

            description = body.get("description", "").strip()
            due_date = body.get("due_date", "").strip()

            try:
                task_id = self.server.db.save_task(
                    record_id=None,
                    content=title,
                    notes=description if description else None,
                    day_date=due_date if due_date else None,
                    task_origin="local_api"
                )

                # Emit signal with parameters
                self.server.signals.sig_create_task.emit({
                    "id": task_id,
                    "title": title,
                    "description": description,
                    "due_date": due_date
                })

                self._send_json(201, {
                    "success": True,
                    "task_id": task_id,
                    "message": "Task created successfully on the board."
                })
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        else:
            self._send_json(404, {"success": False, "error": f"Endpoint POST {path} not found."})


class LocalAPIServerThread(QThread):
    """Isolated background QThread running the loopback ThreadingHTTPServer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = APISignals()
        self.db = DBManager()
        self.rag = RAGEngine()
        self.server = None
        self.port = 0
        self.token = ""

        # Live application state updated atomically
        self._live_state = {
            "status": "idle",
            "active_mic": "Default",
            "elapsed_seconds": 0,
            "backlog": 0
        }

    def set_recording_status(self, is_recording: bool, mic_name: str = "Default", elapsed: int = 0):
        """Slot to atomically update live state parameters."""
        self._live_state["status"] = "recording" if is_recording else "idle"
        self._live_state["active_mic"] = mic_name
        self._live_state["elapsed_seconds"] = elapsed

    def set_queue_backlog(self, count: int):
        """Slot to atomically update backlog."""
        self._live_state["backlog"] = count

    def get_live_status(self) -> dict:
        """Returns safe snapshot of current status."""
        return {
            "app_name": "El Secretario",
            "version": "1.0.0",
            "status": self._live_state["status"],
            "active_recording": {
                "elapsed_seconds": self._live_state["elapsed_seconds"],
                "audio_device": self._live_state["active_mic"]
            } if self._live_state["status"] == "recording" else None,
            "processing_queue_backlog": self._live_state["backlog"]
        }

    def run(self):
        # Select dynamic available port starting at 12800
        import socket
        port = 12800
        while port < 13000:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(("127.0.0.1", port))
                s.close()
                break
            except socket.error:
                port += 1

        self.port = port
        self.token = secrets.token_hex(16)

        # Write the app.port discovery file safely in the root workspace folder!
        try:
            port_filepath = os.path.abspath("app.port")
            with open(port_filepath, "w", encoding="utf-8") as f:
                f.write(f"port={self.port}\ntoken={self.token}\n")
            logger.info(f"Port discovery written to {port_filepath} (Port: {self.port})")
        except Exception as e:
            logger.error(f"Failed to write app.port discovery file: {e}")

        # Start the ThreadingHTTPServer
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", self.port), LocalAPIRequestHandler)
            # Inject references into server object
            self.server.token = self.token
            self.server.signals = self.signals
            self.server.db = self.db
            self.server.rag = self.rag
            self.server.thread = self

            logger.info(f"Local REST API server listening strictly on 127.0.0.1:{self.port}...")
            self.server.serve_forever()

        except Exception as e:
            logger.error(f"Error inside local REST API server thread: {e}")
        finally:
            self.cleanup()

    def stop(self):
        """Signals the server to stop listening and close sockets."""
        if self.server:
            try:
                self.server.shutdown()  # Breaks serve_forever instantly and safely!
                self.server.server_close()
            except Exception:
                pass
        self.wait()

    def cleanup(self):
        """Cleans up the app.port discovery file on exit."""
        try:
            port_filepath = os.path.abspath("app.port")
            if os.path.exists(port_filepath):
                os.remove(port_filepath)
                logger.info("Cleaned up app.port discovery file successfully.")
        except Exception as e:
            logger.error(f"Failed to remove app.port file on exit: {e}")
