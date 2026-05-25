#!/usr/bin/env python3
"""abox-labs-mcp-server MCP server with dynamic tool loading.

This server automatically discovers and loads tools from the src/tools/ directory.
Each tool file should contain a function decorated with @mcp.tool().

Usage Examples:
  # Stdio mode (default MCP transport)
  python src/main.py
  
  # HTTP mode with MCP protocol over HTTP
  python src/main.py --transport http
  
  # Custom host/port
  python src/main.py --transport http --host localhost --port 8080
  
  # Environment variable mode
  MCP_TRANSPORT_MODE=http python src/main.py
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.server import DynamicMCPServer  # noqa: E402


def _setup_tracing() -> None:
    """Initialise Phoenix / OpenTelemetry tracing if a collector endpoint is configured.

    Reads:
      PHOENIX_COLLECTOR_ENDPOINT – OTLP gRPC/HTTP endpoint of the Phoenix collector
                                    (e.g. http://localhost:6006 for a local instance,
                                     or https://app.phoenix.arize.com for Arize Cloud).
      PHOENIX_PROJECT_NAME       – logical project name shown in the Phoenix UI
                                    (default: "abox-labs-mcp-server").
      PHOENIX_API_KEY            – required only for Arize Cloud; omit for local Phoenix.

    If PHOENIX_COLLECTOR_ENDPOINT is not set the function returns silently so that
    the server still works without any tracing infrastructure.
    """
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        logging.getLogger(__name__).info(
            "PHOENIX_COLLECTOR_ENDPOINT not set – tracing disabled"
        )
        return

    project_name = os.getenv("PHOENIX_PROJECT_NAME", "abox-labs-mcp-server")

    try:
        from phoenix.otel import register  # type: ignore[import-untyped]

        register(
            project_name=project_name,
            auto_instrument=True,
        )
        logging.getLogger(__name__).info(
            "Phoenix tracing enabled → endpoint=%s project=%s",
            endpoint,
            project_name,
        )
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).warning(
            "Failed to initialise Phoenix tracing: %s", exc
        )


def main() -> None:
    """Main entry point for the MCP server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="abox-labs-mcp-server MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode: stdio, or http"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "localhost"),
        help="Host to bind to in HTTP mode (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "3000")),
        help="Port to bind to in HTTP mode (default: 3000)"
    )

    args = parser.parse_args()

    # Check environment variable for transport mode
    transport_mode = os.getenv("MCP_TRANSPORT_MODE", args.transport)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )

    # Initialise Phoenix tracing before the server starts so that every MCP
    # call is captured from the very first request.
    _setup_tracing()

    try:
        # Create server with dynamic tool loading
        server = DynamicMCPServer(
            name="abox-labs-mcp-server",
            tools_dir="src/tools"
        )

        # Load tools and start server
        server.load_tools()

        if transport_mode not in ["http", "stdio"]:
            raise ValueError(f"Invalid transport mode: {transport_mode}. Must be one of: http, or stdio")
        
        server.run(transport_mode=transport_mode, host=args.host, port=args.port)

    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


def dev() -> None:
    """Entry point for the 'dev' script."""
    sys.argv = ["dev", "--transport", "http"]
    main()


def start() -> None:
    """Entry point for the 'start' script."""
    sys.argv = ["start", "--transport", "stdio"]
    main()


if __name__ == "__main__":
    main()
