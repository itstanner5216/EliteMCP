#!/usr/bin/env python3
"""
Sandbox Execution Engine for Programmatic Tool Calling (PTC)
Supports Daytona as primary backend with Docker fallback.
"""
# Production code module - must not contain runtime testing blocks.

import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution."""
    exit_code: int
    stdout: str
    stderr: str


class SandboxExecutionEngine:
    """Sandbox execution engine with Daytona primary and Docker fallback."""
    
    def __init__(self):
        """Initialize the sandbox execution engine."""
        self._lock = threading.Lock()
        self._workspace = None
        self._backend = None
        self._backend_type = None
        self._workspace_created = False
        
        # Try to initialize Daytona first
        if self._init_daytona():
            logger.info("Daytona backend initialized successfully")
        else:
            # Fallback to Docker
            if self._init_docker():
                logger.info("Docker backend initialized successfully")
            else:
                raise RuntimeError("Failed to initialize any sandbox backend (Daytona or Docker)")
    
    def _init_daytona(self) -> bool:
        """Initialize Daytona backend."""
        try:
            from daytona_sdk import DaytonaClient
            
            self._client = DaytonaClient()
            logger.info("Daytona client created successfully")
            self._backend_type = "daytona"
            return True
            
        except ImportError:
            logger.warning("Daytona SDK not available, will use Docker fallback")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Daytona: {e}")
            return False
    
    def _init_docker(self) -> bool:
        """Initialize Docker backend."""
        try:
            import docker
            
            self._docker_client = docker.from_env()
            # Test Docker connection
            self._docker_client.ping()
            logger.info("Docker client created successfully")
            self._backend_type = "docker"
            return True
            
        except ImportError:
            logger.error("Docker SDK not available")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Docker: {e}")
            return False
    
    def _get_or_create_workspace(self) -> Any:
        """Get existing workspace or create a new one."""
        if self._workspace is not None:
            return self._workspace

        if self._backend_type == "daytona":
            workspace = self._create_daytona_workspace()
        elif self._backend_type == "docker":
            workspace = self._create_docker_workspace()
        else:
            raise RuntimeError(f"Unknown backend type: {self._backend_type}")

        logger.debug(f"Using backend: {self._backend_type}")
        return workspace
    
    def _create_daytona_workspace(self) -> Any:
        """Create a Daytona workspace."""
        try:
            self._workspace = self._client.create_workspace(image="python:3.11-slim")
            self._workspace_created = True
            logger.info("Daytona workspace created successfully")

            # Verify workspace has required capabilities
            self._check_daytona_capabilities(self._workspace)

            return self._workspace
        except Exception as e:
            raise RuntimeError(f"Failed to create Daytona workspace: {e}")

    def _check_daytona_capabilities(self, workspace: Any) -> None:
        """Check that Daytona workspace has required API capabilities."""
        missing = []

        if not hasattr(workspace, 'fs'):
            missing.append('workspace.fs')
        else:
            if not hasattr(workspace.fs, 'write_file'):
                missing.append('workspace.fs.write_file')

        if not hasattr(workspace, 'exec'):
            missing.append('workspace.exec')

        if not hasattr(workspace, 'remove'):
            missing.append('workspace.remove')

        if missing:
            raise RuntimeError(
                f"Daytona workspace object is missing required capabilities: {', '.join(missing)}. "
                "This indicates an unsupported or incomplete Daytona workspace implementation."
            )
    
    def _create_docker_workspace(self) -> Any:
        """Create a Docker workspace."""
        try:
            # Create a temporary directory for the workspace
            self._temp_dir = tempfile.mkdtemp(prefix="sandbox_workspace_")
            
            # Create a container with volume mount
            self._workspace = self._docker_client.containers.run(
                image="python:3.11-slim",
                command="sleep infinity",  # Keep container running
                volumes={self._temp_dir: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                detach=True,
                remove=True
            )
            self._workspace_created = True
            logger.info("Docker workspace created successfully")
            return self._workspace
        except Exception as e:
            raise RuntimeError(f"Failed to create Docker workspace: {e}")
    
    def _install_requirements(self, requirements: List[str]) -> None:
        """Install Python requirements in the sandbox.

        Daytona and Docker now enforce identical pip-install failure semantics.
        Daytona uses stderr/stdout decode fallback same as Docker,
        ensuring deterministic behavior regardless of backend.
        """
        if not requirements:
            return
            
        logger.info(f"Installing requirements: {requirements}")
        
        # Create requirements.txt
        req_content = "\n".join(requirements)
        
        if self._backend_type == "daytona":
            try:
                self._workspace.fs.write_file("/workspace/requirements.txt", req_content)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to write requirements file in Daytona workspace: {e}"
                )

            try:
                result = self._workspace.exec("pip install -r /workspace/requirements.txt")

                if result.exit_code != 0:
                    decoded = (result.stderr or result.stdout or "").encode().decode("utf-8", errors="replace")
                    raise RuntimeError(f"Failed to install requirements: {decoded}")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to install requirements via Daytona exec: {e}"
                )
        else:  # Docker
            req_path = Path(self._temp_dir) / "requirements.txt"
            req_path.write_text(req_content)
            result = self._workspace.exec_run("pip install -r /workspace/requirements.txt")

        if result.exit_code != 0:
            decoded = (result.output or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"Failed to install requirements: {decoded}")
        
        logger.info("Requirements installed successfully")
    
    def _write_script(self, script: str) -> None:
        """Write Python script to task.py in workspace."""
        if self._backend_type == "daytona":
            try:
                self._workspace.fs.write_file("/workspace/task.py", script)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to write script file in Daytona workspace: {e}"
                )
        else:  # Docker
            script_path = Path(self._temp_dir) / "task.py"
            script_path.write_text(script)
    
    def _execute_script(self) -> ExecutionResult:
        """Execute the Python script in the sandbox."""
        logger.info("Executing Python script in sandbox")
        
        if self._backend_type == "daytona":
            try:
                result = self._workspace.exec("python /workspace/task.py")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to execute script via Daytona exec: {e}"
                )

            if result is None:
                raise RuntimeError("Daytona exec returned None result")

            return ExecutionResult(
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr
            )
        else:  # Docker
            result = self._workspace.exec_run("python /workspace/task.py")
            if result is None:
                raise RuntimeError("Docker exec_run returned None result")
            decoded = (result.output or b"").decode("utf-8", errors="replace")

            # Docker merges stdout+stderr into a single stream (result.output).
            # The engine guarantees stderr="" for Docker containers.
            return ExecutionResult(
                exit_code=result.exit_code,
                stdout=decoded,
                stderr=""
            )
    
    def execute_python(self, script: str, requirements: List[str] = None) -> Dict[str, Any]:
        """
        Execute Python code in a sandboxed environment.
        
        Args:
            script: Python code to execute
            requirements: List of Python packages to install
            
        Returns:
            Dict with exit_code, stdout, stderr
        """
        with self._lock:  # Ensure sequential execution
            try:
                # Get or create workspace
                workspace = self._get_or_create_workspace()
                
                # Install requirements if provided
                if requirements:
                    self._install_requirements(requirements)
                
                # Write script to workspace
                self._write_script(script)
                
                # Execute the script
                result = self._execute_script()
                
                return {
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                
            except Exception as e:
                logger.error(f"Execution failed: {e}")
                return {
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"Execution failed: {str(e)}"
                }
    
    def cleanup(self):
        """Clean up resources."""
        if self._workspace is None:
            return
            
        try:
            if self._backend_type == "daytona":
                if hasattr(self._workspace, 'remove'):
                    try:
                        self._workspace.remove()
                    except Exception as e:
                        logger.error(f"Failed to remove Daytona workspace: {e}")
            else:  # Docker
                if hasattr(self._workspace, 'stop'):
                    self._workspace.stop()
                if hasattr(self._workspace, 'remove'):
                    self._workspace.remove()
            
            # Clean up temporary directory for Docker
            if hasattr(self, '_temp_dir') and os.path.exists(self._temp_dir):
                import shutil
                shutil.rmtree(self._temp_dir)
                
            logger.info("Workspace cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Failed to clean up workspace: {e}")


# Global instance for easy access
_execution_engine = None


def execute_python(script: str, requirements: List[str] = None) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed environment.
    
    Args:
        script: Python code to execute
        requirements: List of Python packages to install
        
    Returns:
        Dict with exit_code, stdout, stderr
    """
    global _execution_engine
    
    if _execution_engine is None:
        try:
            _execution_engine = SandboxExecutionEngine()
        except Exception as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Failed to initialize sandbox engine: {str(e)}"
            }
    
    return _execution_engine.execute_python(script, requirements)


def cleanup_sandbox():
    """Clean up the sandbox resources."""
    global _execution_engine
    
    if _execution_engine is not None:
        _execution_engine.cleanup()
        _execution_engine = None
