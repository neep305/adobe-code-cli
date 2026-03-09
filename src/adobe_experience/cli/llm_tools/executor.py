"""Command executor - executes CLI tools and captures results."""

import asyncio
import logging
import sys
import time
from io import StringIO
from typing import Any, Dict, Optional

from click.exceptions import Exit as ClickExit

# Allow nested asyncio.run() calls (needed for Typer commands that use asyncio.run())
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    # nest_asyncio not installed, will fail if nested asyncio.run() is attempted
    pass

from adobe_experience.cli.llm_tools.registry import ToolRegistry
from adobe_experience.cli.llm_tools.safety import get_safety_warning, is_safe_tool
from adobe_experience.cli.llm_tools.schemas import ExecutionResult
from adobe_experience.core.config import AEPConfig

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Executes CLI commands programmatically and captures output.
    
    Takes tool calls from LLM and executes the corresponding CLI commands,
    capturing stdout and handling errors gracefully.
    
    Example:
        >>> executor = CommandExecutor(registry, config)
        >>> result = await executor.execute_tool(
        ...     "aep_schema_list",
        ...     {"limit": 10}
        ... )
        >>> print(result.output)
    """
    
    def __init__(self, registry: ToolRegistry, config: Optional[AEPConfig] = None):
        """Initialize executor.
        
        Args:
            registry: ToolRegistry containing registered tools
            config: Optional AEP configuration (uses default if not provided)
        """
        self.registry = registry
        self.config = config
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        require_confirmation: bool = False
    ) -> ExecutionResult:
        """Execute a tool and return structured result.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Dictionary of parameters to pass to the tool
            require_confirmation: If True, require confirmation before executing
            
        Returns:
            ExecutionResult with success status, output, and any errors
            
        Example:
            >>> result = await executor.execute_tool(
            ...     "aep_schema_list",
            ...     {"limit": 10, "json": False}
            ... )
            >>> if result.success:
            ...     print(result.output)
        """
        start_time = time.time()
        
        try:
            # Get tool definition
            tool_def = self.registry.get_tool(tool_name)
            if not tool_def:
                return ExecutionResult(
                    success=False,
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' not found in registry",
                    error_code="TOOL_NOT_FOUND",
                    suggestion="Use '/tools' command to see available tools",
                    execution_time_seconds=time.time() - start_time
                )
            
            # Safety check - only allow safe tools in Phase 1
            if not is_safe_tool(tool_name):
                warning = get_safety_warning(tool_name)
                return ExecutionResult(
                    success=False,
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' is not available in Phase 1 (read-only mode)",
                    error_code="TOOL_NOT_SAFE",
                    suggestion="Only read-only operations are currently supported",
                    execution_time_seconds=time.time() - start_time
                )
            
            # Validate parameters
            validation_result = self._validate_parameters(tool_def, parameters)
            if not validation_result["valid"]:
                return ExecutionResult(
                    success=False,
                    tool_name=tool_name,
                    error=f"Invalid parameters: {validation_result['error']}",
                    error_code="INVALID_PARAMETERS",
                    suggestion=validation_result.get("suggestion", "Check parameter types and required fields"),
                    execution_time_seconds=time.time() - start_time
                )
            
            # Capture stdout
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = captured_output = StringIO()
            sys.stderr = captured_errors = StringIO()
            
            result_value = None
            
            try:
                # Call the Typer command function directly
                handler = tool_def.handler
                
                if asyncio.iscoroutinefunction(handler):
                    result_value = await handler(**parameters)
                else:
                    result_value = handler(**parameters)
                
                output = captured_output.getvalue()
                errors = captured_errors.getvalue()
                
                # Combine output and errors
                full_output = output
                if errors:
                    full_output += f"\n[Errors: {errors}]"
                
                execution_time = time.time() - start_time
                
                return ExecutionResult(
                    success=True,
                    tool_name=tool_name,
                    output=full_output or "(No output)",
                    result=result_value,
                    execution_time_seconds=execution_time
                )
                
            except (ClickExit, SystemExit) as e:
                # Handle Typer/Click exit codes (e.g., raise typer.Exit(1))
                # ClickExit.exit_code is the attribute for Click exceptions
                # SystemExit.code is the attribute for SystemExit exceptions
                if isinstance(e, ClickExit):
                    exit_code = e.exit_code if hasattr(e, 'exit_code') else 1
                else:  # SystemExit
                    exit_code = e.code if e.code is not None else 1
                    
                output = captured_output.getvalue()
                error_output = captured_errors.getvalue()
                
                # Debug logging
                logger.debug(f"Exit exception caught: type={type(e).__name__}, code={exit_code}, output_len={len(output)}, error_len={len(error_output)}")
                logger.debug(f"Captured output: {repr(output[:200])}")
                logger.debug(f"Captured errors: {repr(error_output[:200])}")
                
                # Combine any captured output and errors
                # Prioritize error_output, then output, then generic message
                if error_output.strip():
                    error_msg = error_output.strip()
                elif output.strip():
                    error_msg = output.strip()
                else:
                    error_msg = f"Command exited with code {exit_code}"
                
                execution_time = time.time() - start_time
                
                logger.error(f"Tool execution failed with exit code {exit_code}: {tool_name} - {error_msg}")
                
                return ExecutionResult(
                    success=False,
                    tool_name=tool_name,
                    error=error_msg,
                    error_code="COMMAND_EXIT",
                    suggestion="Check the error message for details",
                    execution_time_seconds=execution_time
                )
                
            except Exception as e:
                # Capture any errors from command execution
                error_msg = str(e)
                error_output = captured_errors.getvalue()
                
                if error_output:
                    error_msg = f"{error_msg}\n{error_output}"
                
                execution_time = time.time() - start_time
                
                # Categorize error and provide suggestion
                error_code, suggestion = self._categorize_error(e, tool_name)
                
                logger.error(f"Tool execution failed: {tool_name} - {error_msg}")
                
                return ExecutionResult(
                    success=False,
                    tool_name=tool_name,
                    error=error_msg,
                    error_code=error_code,
                    suggestion=suggestion,
                    execution_time_seconds=execution_time
                )
                
            finally:
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        
        except Exception as e:
            # Catch-all for unexpected errors
            execution_time = time.time() - start_time
            logger.exception(f"Unexpected error executing tool: {tool_name}")
            
            return ExecutionResult(
                success=False,
                tool_name=tool_name,
                error=f"Unexpected error: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                suggestion="Check logs for details",
                execution_time_seconds=execution_time
            )
    
    def _validate_parameters(
        self,
        tool_def,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate parameters against tool schema.
        
        Args:
            tool_def: Tool definition
            parameters: Parameters to validate
            
        Returns:
            Dict with 'valid' boolean and optional 'error' message
        """
        schema = tool_def.input_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # Check required parameters
        for req_param in required:
            if req_param not in parameters:
                return {
                    "valid": False,
                    "error": f"Missing required parameter: {req_param}",
                    "suggestion": f"Parameter '{req_param}' is required for this tool"
                }
        
        # Check parameter types (basic validation)
        for param_name, param_value in parameters.items():
            if param_name not in properties:
                # Unknown parameter - log warning but allow
                logger.warning(f"Unknown parameter '{param_name}' for tool {tool_def.name}")
                continue
            
            expected_type = properties[param_name].get("type")
            actual_type = self._get_json_type(param_value)
            
            # Allow type coercion for compatible types
            if expected_type and actual_type != expected_type:
                # Check if it's a compatible conversion
                if not self._is_compatible_type(actual_type, expected_type):
                    return {
                        "valid": False,
                        "error": f"Parameter '{param_name}' has wrong type: expected {expected_type}, got {actual_type}",
                        "suggestion": f"Convert '{param_name}' to {expected_type}"
                    }
        
        return {"valid": True}
    
    def _get_json_type(self, value: Any) -> str:
        """Get JSON type of a Python value.
        
        Args:
            value: Python value
            
        Returns:
            JSON type string
        """
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"
    
    def _is_compatible_type(self, actual: str, expected: str) -> bool:
        """Check if types are compatible for coercion.
        
        Args:
            actual: Actual JSON type
            expected: Expected JSON type
            
        Returns:
            True if compatible, False otherwise
        """
        # Integer can be used as number
        if actual == "integer" and expected == "number":
            return True
        
        # Number can sometimes be used as integer (if it's a whole number)
        if actual == "number" and expected == "integer":
            return True
        
        return False
    
    def _categorize_error(self, exception: Exception, tool_name: str) -> tuple[str, str]:
        """Categorize error and provide helpful suggestion.
        
        Args:
            exception: The exception that occurred
            tool_name: Name of the tool that failed
            
        Returns:
            Tuple of (error_code, suggestion)
        """
        error_msg = str(exception).lower()
        
        # Authentication errors
        if "401" in error_msg or "unauthorized" in error_msg or "authentication" in error_msg:
            return (
                "AUTH_ERROR",
                "Authentication failed. Run 'aep auth status' to check credentials, or 'aep auth test' to refresh token"
            )
        
        # Not found errors
        if "404" in error_msg or "not found" in error_msg:
            return (
                "NOT_FOUND",
                "Resource not found. Verify the ID or name you provided exists"
            )
        
        # Permission errors
        if "403" in error_msg or "forbidden" in error_msg or "permission" in error_msg:
            return (
                "PERMISSION_ERROR",
                "Insufficient permissions. Check your AEP role and sandbox access"
            )
        
        # Rate limit errors
        if "429" in error_msg or "rate limit" in error_msg:
            return (
                "RATE_LIMIT",
                "API rate limit exceeded. Wait a moment and try again"
            )
        
        # Network errors
        if "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
            return (
                "NETWORK_ERROR",
                "Network error. Check your internet connection and try again"
            )
        
        # Validation errors
        if "validation" in error_msg or "invalid" in error_msg:
            return (
                "VALIDATION_ERROR",
                "Data validation failed. Check the format and values of your parameters"
            )
        
        # Generic error
        return (
            "EXECUTION_ERROR",
            f"Tool '{tool_name}' encountered an error. Check the error message for details"
        )
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<CommandExecutor: {self.registry.get_tool_count(safe_only=True)} safe tools available>"
