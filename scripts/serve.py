"""Tiny static server with no-cache headers so SPA edits show up without a hard refresh.

Usage: python scripts/serve.py [port]
"""
from __future__ import annotations

import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.log_date_time_string()} {fmt % args}\n")


def main(argv: list[str]) -> int:
    port = int(argv[0]) if argv else 8765
    root = Path(__file__).resolve().parent.parent
    import os
    os.chdir(root)
    addr = ("127.0.0.1", port)
    with ThreadingHTTPServer(addr, NoCacheHandler) as httpd:
        print(f"serving {root} at http://{addr[0]}:{port}/  (no-cache)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nshutting down")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
