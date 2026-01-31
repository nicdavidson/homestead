#!/usr/bin/env python3
"""
Hearth Unified Service

Runs all Hearth components in a single process:
- Nightshift daemon (background thread)
- REST API (on /api)
- Web UI (on /)

Usage:
    python service.py
    # or
    hearth serve
"""

import logging
import threading
import signal
import sys
from typing import Optional
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core import Config, get_config
from core.api import create_api
from web.app import create_app as create_web_app
from agents.nightshift import Nightshift

logger = logging.getLogger("hearth.service")


class HearthService:
    """
    Unified Hearth service.

    Runs everything:
    - Nightshift daemon in background thread
    - REST API + Web UI in FastAPI
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.nightshift = None
        self.nightshift_thread = None
        self.app = None

    def create_unified_app(self) -> FastAPI:
        """
        Create unified FastAPI app combining REST API and Web UI.

        Structure:
        - /api/* -> REST API endpoints
        - /* -> Web UI pages
        """
        # Create main app
        app = FastAPI(
            title="Hearth",
            description="Unified AI Entity Infrastructure",
            version="1.0.0"
        )

        # Add CORS middleware for API
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount REST API under /api
        api_app = create_api(self.config)
        app.mount("/api", api_app)

        # Mount Web UI at root
        web_app = create_web_app(self.config)

        # Mount web app's routes directly into main app
        # This includes the web UI routes and static files
        for route in web_app.routes:
            app.routes.append(route)

        return app

    def start_nightshift(self):
        """Start nightshift daemon in background thread."""
        logger.info("Starting Nightshift daemon in background...")

        self.nightshift = Nightshift(self.config)
        self.nightshift_thread = threading.Thread(
            target=self.nightshift.run,
            daemon=True,
            name="nightshift"
        )
        self.nightshift_thread.start()

        logger.info("Nightshift daemon started")

    def stop_nightshift(self):
        """Stop nightshift daemon gracefully."""
        if self.nightshift:
            logger.info("Stopping Nightshift daemon...")
            self.nightshift.running = False

            if self.nightshift_thread:
                self.nightshift_thread.join(timeout=5)

            logger.info("Nightshift daemon stopped")

    def run(self, host: str = "0.0.0.0", port: int = 8420):
        """
        Run the unified service.

        Args:
            host: Host to bind to (default: 0.0.0.0 for all interfaces)
            port: Port to bind to (default: 8420)
        """
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        # Start nightshift in background
        self.start_nightshift()

        # Create unified app
        self.app = self.create_unified_app()

        # Print startup info
        print("=" * 70)
        print("🔥 Hearth Unified Service")
        print("=" * 70)
        print(f"\n📡 Web UI:     http://{host}:{port}/")
        print(f"🔌 REST API:  http://{host}:{port}/api/")
        print(f"📚 API Docs:  http://{host}:{port}/api/docs")
        print(f"🌙 Nightshift: Running in background")
        print("\n" + "=" * 70)
        print()

        # Run FastAPI server (blocking)
        try:
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level="info"
            )
        finally:
            self.stop_nightshift()

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_nightshift()
        sys.exit(0)


def run_service(
    host: str = "0.0.0.0",
    port: int = 8420,
    config: Optional[Config] = None
):
    """
    Run the unified Hearth service.

    Args:
        host: Host to bind to
        port: Port to bind to
        config: Hearth configuration
    """
    service = HearthService(config)
    service.run(host=host, port=port)


if __name__ == "__main__":
    import sys

    # Parse command line args
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8420

    run_service(host=host, port=port)
