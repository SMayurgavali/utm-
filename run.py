"""
AI-Powered UTM Cloud Hub — Unified System Launcher
Starts the Asynchronous FastAPI Backend and serves the Three-Panel Operator Workspace.
"""

import sys
import os
import socket
import argparse
import getpass
from pathlib import Path
import uvicorn

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def find_available_port(start_port: int, host: str = "127.0.0.1") -> int:
    """Return a free port, starting from the requested port."""
    port = max(1, start_port)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                port += 1


def main():
    parser = argparse.ArgumentParser(description="AI-Powered UTM Cloud Hub Launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--edge", action="store_true", help="Launch standalone edge_agent process alongside")
    parser.add_argument("--bootstrap-admin", action="store_true", help="Prompt securely for the first admin account before starting")
    args = parser.parse_args()

    if args.bootstrap_admin:
        email = os.getenv("UTM_BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
        if not email:
            email = input("Admin email: ").strip().lower()
        password = getpass.getpass("New admin password (input hidden): ")
        if not email or not password:
            parser.error("Admin email and password are required for bootstrap")
        os.environ["UTM_BOOTSTRAP_ADMIN_EMAIL"] = email
        os.environ["UTM_BOOTSTRAP_ADMIN_PASSWORD"] = password

    requested_port = args.port if args.port and args.port > 0 else 8000
    actual_port = find_available_port(requested_port, host=args.host)
    args.port = actual_port

    print("=" * 75)
    print("  AI-POWERED UTM CLOUD HUB: HARDWARE-TO-SOFTWARE RETROFITTING PLATFORM")
    print("=" * 75)
    print(f"  • Requested Host        : {args.host}:{requested_port}")
    print(f"  • Active Host           : {args.host}:{actual_port}")
    print(f"  • Serial Protocol Target: 9600 8-N-1 (connection unverified)")
    print(f"  • Telemetry Ingestion   : UTF-8, Comma Delimited [Time, Force, Disp]")
    print(f"  • Review Standards      : IS 1608, IS 1786, ASTM E8 (prototype)")
    print(f"  • Operator Workspace    : http://{args.host}:{actual_port}/")
    print("=" * 75)

    if requested_port != actual_port:
        print(f"  • Port {requested_port} was busy; automatically moved to free port {actual_port}.")

    if args.edge:
        import subprocess
        print("  • Launching Edge Agent background worker...")
        subprocess.Popen([sys.executable, "edge/edge_agent.py"])

    try:
        uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=False)
    finally:
        os.environ.pop("UTM_BOOTSTRAP_ADMIN_PASSWORD", None)

if __name__ == "__main__":
    main()
