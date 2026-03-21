#!/usr/bin/env python3
"""Simple HTTP server for catalog UI."""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8002
SCRIPT_DIR = Path(__file__).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

if __name__ == "__main__":
    os.chdir(SCRIPT_DIR)
    # Allow reusing the port immediately after restart
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Serving catalog UI on all interfaces, port {PORT}")
        print(f"Navigate to http://localhost:{PORT} or http://192.168.1.156:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
