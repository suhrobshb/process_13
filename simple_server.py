#!/usr/bin/env python3
"""
Simple Web Server for AI Engine Demo
====================================
Serves the HTML interface files so you can access them in a browser
"""

import http.server
import socketserver
import webbrowser
import os
import threading
import time

PORT = 3001

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def start_server():
    """Start the web server"""
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}")
        print("Available pages:")
        print(f"  • Main Interface: http://localhost:{PORT}/interactive_ui_enhanced.html")
        print(f"  • User Interface: http://localhost:{PORT}/user_interface_preview.html")
        print(f"  • Admin Interface: http://localhost:{PORT}/admin_interface_preview.html")
        print(f"  • Workflow Interface: http://localhost:{PORT}/ai_engine_workflow_interface_preview.html")
        print("\nPress Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

if __name__ == "__main__":
    start_server()