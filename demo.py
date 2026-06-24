#!/usr/bin/env python3
import os
import sys
import webbrowser

try:
    import reportlab.graphics.barcode.code128
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["FLASK_ENV"] = "demo"

from app import create_app

app = create_app("demo")

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000
    webbrowser.open(f"http://{host}:{port}")
    print("=" * 60)
    print("  ISO 27001 · NIS2 · GDPR Manager — DEMO")
    print(f"  Running at http://{host}:{port}")
    print("  Close this window to stop the server.")
    print("=" * 60)
    from waitress import serve
    serve(app, host=host, port=port)
