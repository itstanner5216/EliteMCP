#!/usr/bin/env python3
"""
FastMCP Server for Directory Intelligence Tool
Exposes the get_codebase_structure tool as a FastMCP service.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPServer:
    """Main MCP Server class with robust configuration and error handling."""

    def __init__(self):
        """Initialize the MCP server with default configuration."""
        # Load configuration with validation
        self.config = self._load_config()

        # Initialize FastMCP instance
        self.mcp = None

        # Store registered tools
        self.registered_tools = []

        # Note: The current FastMCP server loads configuration but does not yet forward
        # tool-specific configuration (such as max_file_count and expand_large) into
        # instantiated tools. Documented for future extension.

    def _load_config(self) -> Dict[str, Any]:
        """
        Load and validate configuration from config/config.json.

        Returns:
            Dict containing validated configuration with defaults applied

        Raises:
            RuntimeError: If configuration is invalid or cannot be loaded
        """
        config_path = Path(__file__).parent.parent / "config" / "config.json"

        # Default configuration
        defaults = {
            "server_name": "directory-intelligence-server",
            "host": "127.0.0.1",
            "port": 8000,
            "log_level": "INFO",
            "enable_directory_tool": True,
            "tools": {
                "directory_tool": {
                    "enabled": True,
                    "max_file_count": 50,
                    "expand_large": False
                }
            }
        }

        # Try to load config file
        try:
            if not config_path.exists():
                logger.warning(f"Config:not_found: {config_path}")
                return defaults

            with open(config_path, 'r') as f:
                config = json.load(f)

            # Apply defaults for missing fields
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value

            logger.debug(f"Config:loaded: {config_path}")
            return config

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Config:invalid_json: {str(e)}")
        except PermissionError as e:
            raise RuntimeError(f"Config:permission_denied: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Config:load_error: {str(e)}")

    def _validate_config(self) -> None:
        """
        Validate configuration values.

        Raises:
            RuntimeError: If validation fails
        """
        # Validate server configuration
        if not isinstance(self.config.get("server_name"), str) or not self.config["server_name"].strip():
            raise RuntimeError("Config:invalid: server_name must be a non-empty string")

        # Validate host
        host = self.config.get("host")
        if not isinstance(host, str) or not host.strip():
            raise RuntimeError("Config:invalid: host must be a non-empty string")

        # Validate port
        port = self.config.get("port")
        if not isinstance(port, int):
            raise RuntimeError("Config:invalid: port must be an integer")
        if not (1 <= port <= 65535):
            raise RuntimeError("Config:invalid: port must be between 1 and 65535")

        # Validate log_level
        log_level = self.config.get("log_level", "INFO")
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            raise RuntimeError(f"Config:invalid: log_level must be one of {valid_levels}")

        logger.debug("Config:validated")

    def _initialize_fastmcp(self) -> None:
        """
        Initialize FastMCP instance with configuration.

        Raises:
            RuntimeError: If initialization fails
        """
        try:
            server_name = self.config.get("server_name", "directory-intelligence-server")
            self.mcp = FastMCP(name=server_name)
            logger.debug("FastMCP:initialized")
        except Exception as e:
            raise RuntimeError(f"FastMCP:init_error: {str(e)}")

    def _register_tools(self) -> None:
        """
        Register enabled tools with FastMCP.

        Raises:
            RuntimeError: If tool registration fails
        """
        # Check if directory tool is enabled
        if not self.config.get("enable_directory_tool", True):
            logger.info("Tools:directory_tool:disabled")
            return

        try:
            # Import the tool from directory_tool.py
            from directory_tool import get_codebase_structure

            # Note: MCP-exposed tools receive explicit argument values for each invocation
            # and therefore do not rely on environment or config defaults unless the server
            # is extended to propagate configuration to the tool layer.
            self.mcp.add_tool(get_codebase_structure)
            self.registered_tools.append("get_codebase_structure")

            logger.debug("Tools:registered: get_codebase_structure")

        except ImportError as e:
            raise RuntimeError(f"Tools:import_error: directory_tool - {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Tools:registration_error: {str(e)}")

    def _log_startup_info(self) -> None:
        """Log server startup information."""
        host = self.config["host"]
        port = self.config["port"]
        tools = ", ".join(self.registered_tools) if self.registered_tools else "none"

        logger.info(f"Server:starting: name={self.config['server_name']}")
        logger.info(f"Server:listening: host={host} port={port}")
        logger.info(f"Tools:enabled: {tools}")
        logger.info(f"Environment: python={sys.version.split()[0]} os={os.name}")

    def run(self) -> None:
        """
        Run the MCP server.

        This method handles the complete server lifecycle with proper error handling.
        """
        try:
            # Validate configuration
            self._validate_config()

            # Initialize FastMCP
            self._initialize_fastmcp()

            # Register tools
            self._register_tools()

            # Log startup information
            self._log_startup_info()

            # Get configuration
            host = self.config["host"]
            port = self.config["port"]
            log_level = self.config["log_level"]

            # Run the server
            self.mcp.run(
                host=host,
                port=port,
                log_level=log_level
            )

        except KeyboardInterrupt:
            logger.info("Server:shutdown: interrupted by user")
        except RuntimeError as e:
            logger.error(f"Server:startup_error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Server:unexpected_error: {str(e)}")
            sys.exit(1)


def main():
    """Main entry point for the server."""
    # Ensure server only runs when executed as a script
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
