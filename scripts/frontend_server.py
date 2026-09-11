"""Serve the local results frontend, or run its Vite development server.

npm --prefix frontend run dev       (development, port 5173)
python3 scripts/frontend_server.py  (built frontend, port 8765)
"""

import argparse
import json
import mimetypes
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from frontend_data import LocalArchive, ROOT, is_local_file


def make_handler(archive):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.do_GET(head=True)

        def do_GET(self, head=False):
            if self.headers.get("Host", "").split(":")[0] not in {"localhost", "127.0.0.1"}:
                self.send_error(403)
                return
            path = urlsplit(self.path).path
            if path == "/api/experiments":
                try:
                    with lock:
                        data = archive.catalogue()
                    body = json.dumps(data, allow_nan=False).encode()
                except (OSError, ValueError):
                    self.send_error(500, "Could not read local results")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if not head:
                    self.wfile.write(body)
                return
            if path.startswith("/api/images/"):
                with lock:
                    file = archive.image_path(path.removeprefix("/api/images/"))
            else:
                base = archive.root / "frontend/dist"
                file = base / ("index.html" if path == "/" else unquote(path).lstrip("/"))
                if not is_local_file(file, base):
                    file = None
            if file is None:
                self.send_error(404)
                return
            try:
                source = file.open("rb")
            except OSError:
                self.send_error(404)
                return
            with source:
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(os.fstat(source.fileno()).st_size))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                if not head:
                    try:
                        shutil.copyfileobj(source, self.wfile)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

        def log_message(self, format, *args):
            if len(args) > 1 and str(args[1]).startswith(("4", "5")):
                super().log_message(format, *args)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    port = args.port or (8766 if args.dev else 8765)
    archive = LocalArchive()
    archive.catalogue()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(archive))
    if args.dev:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        child = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], cwd=ROOT / "frontend", env={**os.environ, "BENCH_API_PORT": str(port)})
        try:
            child.wait()
        except KeyboardInterrupt:
            child.terminate()
            child.wait(timeout=10)
        finally:
            server.shutdown()
            server.server_close()
        if child.returncode not in (0, -15, -2):
            raise SystemExit(child.returncode)
    else:
        print(f"Blender Bench: http://127.0.0.1:{port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
