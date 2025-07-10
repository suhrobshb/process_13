#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend UI
"""

import os
import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 3000

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

def start_server():
    """Start the HTTP server for the frontend"""
    
    # Check if user_interface_preview.html exists
    ui_file = Path("user_interface_preview.html")
    if not ui_file.exists():
        print(f"Error: {ui_file} not found")
        return
    
    handler = CustomHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"🌐 Frontend server starting on http://localhost:{PORT}")
        print(f"📁 Serving files from: {Path.cwd()}")
        print(f"🎯 Main UI available at: http://localhost:{PORT}/user_interface_preview.html")
        print(f"📊 Admin interface at: http://localhost:{PORT}/admin_interface_preview.html")
        print(f"🔧 Workflow editor at: http://localhost:{PORT}/ai_engine_workflow_interface_preview.html")
        print("\n💡 Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped")

if __name__ == "__main__":
    start_server()