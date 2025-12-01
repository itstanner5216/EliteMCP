#!/usr/bin/env python3
"""
FastMCP Server for Directory Intelligence Tool
Exposes the get_codebase_structure tool as a FastMCP service.
"""

import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Import FastMCP
    from fastmcp import FastMCP
    
    # Import the tool from directory_tool.py (assumed to be in same src folder)
    try:
        from directory_tool import get_codebase_structure
    except ImportError as e:
        logger.error(f"Failed to import get_codebase_structure from directory_tool.py: {e}")
        logger.error("Ensure directory_tool.py is in the same directory as mcp_server.py")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"directory_tool.py not found: {e}")
        logger.error("Ensure directory_tool.py exists in the same directory as mcp_server.py")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error importing directory_tool: {e}")
        sys.exit(1)

    # Load configuration
    def load_config():
        """Load configuration from config.json."""
        config_path = Path(__file__).parent.parent / "config" / "config.json"
        try:
            import json
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return {
                "server_name": "directory-intelligence-server",
                "host": "127.0.0.1",
                "port": 8000,
                "log_level": "INFO"
            }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            sys.exit(1)

    # Load configuration
    config = load_config()

    # Create FastMCP instance
    try:
        mcp = FastMCP(
            name=config.get("server_name", "directory-intelligence-server")
        )
        
        # Register the get_codebase_structure tool
        mcp.add_tool(get_codebase_structure)
        
        logger.info("Successfully registered get_codebase_structure tool")
        
    except Exception as e:
        logger.error(f"Failed to create FastMCP server or register tool: {e}")
        sys.exit(1)

    def main():
        """Main function to run the server."""
        try:
            host = config.get("host", "127.0.0.1")
            port = config.get("port", 8000)
            
            print(f"FastMCP server running on {host}:{port}")
            logger.info(f"Starting FastMCP server on {host}:{port}")
            
            # Run the server
            mcp.run(
                host=host,
                port=port,
                log_level=config.get("log_level", "INFO")
            )
            
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            print("\nServer stopped.")
        except Exception as e:
            logger.error(f"Server error: {e}")
            print(f"Server error: {e}")
            sys.exit(1)

    if __name__ == "__main__":
        main()

except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Ensure FastMCP is installed: pip install fastmcp")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    sys.exit(1)