#!/usr/bin/env python3
"""
Dojo Server - HTTP API for Ninja Operations

Exposes the Hokage and ninjas over HTTP so any client
(BeeBill, TypeScript, Go, etc.) can use them.

Endpoints:
    GET  /status              - Hokage status
    GET  /ninjas              - List available ninjas
    GET  /jutsu               - List available jutsu
    POST /dispatch            - Dispatch a ninja to perform jutsu
    POST /shadow-clone-army   - Parallel execution
    POST /combination         - Chain multiple jutsu

This is the bridge between Dojo and the world.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from typing import Dict, Any

from scroll import Scroll
from jutsu import Hokage, JUTSU_LIBRARY, SUMMONING_CONTRACTS


# Global Hokage instance
hokage: Hokage = None


class DojoHandler(BaseHTTPRequestHandler):
    """HTTP handler for Dojo operations."""

    def _send_json(self, data: Any, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _read_json(self) -> Dict:
        """Read JSON from request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        return json.loads(body) if body else {}

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self._send_json({})

    def do_GET(self):
        """Handle GET requests."""
        path = urllib.parse.urlparse(self.path).path

        if path == "/status":
            self._send_json({
                "status": "operational",
                "hokage": str(hokage),
                "ninjas": list(hokage.ninjas.keys()),
                "missions_completed": hokage.mission_count,
            })

        elif path == "/ninjas":
            ninjas_info = {}
            for name, ninja in hokage.ninjas.items():
                ninjas_info[name] = {
                    "name": ninja.name,
                    "model": ninja.model,
                    "chakra_affinity": ninja.chakra_affinity,
                    "jutsu": list(ninja.jutsu.keys()),
                    "jutsu_count": ninja.jutsu_count,
                }
            self._send_json(ninjas_info)

        elif path == "/jutsu":
            jutsu_info = {}
            for name, jutsu in JUTSU_LIBRARY.items():
                jutsu_info[name] = {
                    "name": jutsu.name,
                    "description": jutsu.description,
                    "chakra_type": jutsu.chakra_type,
                }
            self._send_json(jutsu_info)

        elif path == "/contracts":
            self._send_json(list(SUMMONING_CONTRACTS.keys()))

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        path = urllib.parse.urlparse(self.path).path
        data = self._read_json()

        if path == "/dispatch":
            # Dispatch a ninja to perform a jutsu
            ninja_name = data.get("ninja")
            jutsu_name = data.get("jutsu")
            kwargs = data.get("kwargs", {})

            if not ninja_name or not jutsu_name:
                self._send_json({"error": "Missing ninja or jutsu"}, 400)
                return

            result = hokage.dispatch(ninja_name, jutsu_name, **kwargs)
            self._send_json(result.to_dict())

        elif path == "/shadow-clone-army":
            # Parallel execution with shadow clones
            ninja_name = data.get("ninja")
            jutsu_name = data.get("jutsu")
            tasks = data.get("tasks", [])

            if not ninja_name or not jutsu_name or not tasks:
                self._send_json({"error": "Missing ninja, jutsu, or tasks"}, 400)
                return

            results = hokage.shadow_clone_army(ninja_name, tasks, jutsu_name)
            self._send_json([r.to_dict() for r in results])

        elif path == "/combination":
            # Combination jutsu - chain multiple steps
            steps = data.get("steps", [])

            if not steps:
                self._send_json({"error": "Missing steps"}, 400)
                return

            result = hokage.combination_jutsu(steps)
            self._send_json(result.to_dict())

        elif path == "/summon":
            # Summon a new ninja
            contract_name = data.get("contract")

            if not contract_name:
                self._send_json({"error": "Missing contract name"}, 400)
                return

            ninja = hokage.summon(contract_name)
            if ninja:
                self._send_json({
                    "summoned": ninja.name,
                    "jutsu": list(ninja.jutsu.keys()),
                })
            else:
                self._send_json({"error": f"Unknown contract: {contract_name}"}, 400)

        elif path == "/raw":
            # Raw prompt execution (for custom jutsu)
            ninja_name = data.get("ninja")
            prompt = data.get("prompt")

            if not ninja_name or not prompt:
                self._send_json({"error": "Missing ninja or prompt"}, 400)
                return

            ninja = hokage.ninjas.get(ninja_name.lower())
            if not ninja:
                self._send_json({"error": f"Unknown ninja: {ninja_name}"}, 400)
                return

            result = ninja._execute(prompt, "raw")
            self._send_json(result.to_dict())

        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[Dojo] {args[0]}")


def run_server(host: str = "0.0.0.0", port: int = 9565, ollama_url: str = "http://localhost:11434/api/generate"):
    """Start the Dojo server."""
    global hokage

    print("=" * 60)
    print("DOJO SERVER - Ninja Operations API")
    print("=" * 60)

    # Initialize Hokage
    hokage = Hokage(ollama_url)
    print(f"Hokage initialized: {hokage}")
    print(f"Ollama URL: {ollama_url}")

    # Start server
    server = HTTPServer((host, port), DojoHandler)
    print(f"\nServer running at http://{host}:{port}")
    print("\nEndpoints:")
    print("  GET  /status              - Hokage status")
    print("  GET  /ninjas              - List ninjas")
    print("  GET  /jutsu               - List jutsu")
    print("  POST /dispatch            - Perform jutsu")
    print("  POST /shadow-clone-army   - Parallel execution")
    print("  POST /combination         - Chain jutsu")
    print("  POST /summon              - Summon new ninja")
    print("  POST /raw                 - Raw prompt")
    print("\n" + "=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    import sys

    # Parse args
    port = 9565
    ollama_url = "http://localhost:11434/api/generate"

    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])
        elif arg.startswith("--ollama="):
            ollama_url = arg.split("=")[1]

    run_server(port=port, ollama_url=ollama_url)
