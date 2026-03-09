"""Tool registry - converts CLI commands to LLM tool definitions."""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, get_args, get_origin

from adobe_experience.cli.llm_tools.safety import is_safe_tool
from adobe_experience.cli.llm_tools.schemas import ToolCategory, ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for CLI commands as LLM tools.
    
    Converts Typer CLI commands into Anthropic tool definitions that can be
    called by LLM models using function calling.
    
    Example:
        >>> registry = ToolRegistry()
        >>> registry.register_from_typer_command(
        ...     "list", schema.list_schemas, "schema",
        ...     "List XDM schemas"
        ... )
        >>> tools = registry.get_anthropic_tools()
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._tools_by_category: Dict[str, List[str]] = {}
    
    def register_from_typer_command(
        self,
        command_name: str,
        typer_command: Callable,
        category: str,
        description: Optional[str] = None
    ) -> ToolDefinition:
        """Convert Typer command to LLM tool definition.
        
        Analyzes the command's function signature, extracts parameter types and
        defaults from Typer annotations, and creates a tool definition that LLMs
        can use.
        
        Args:
            command_name: Name of the command (e.g., "list", "get")
            typer_command: The actual Typer command function
            category: Tool category (schema, dataset, dataflow, etc.)
            description: Optional custom description (uses docstring if not provided)
            
        Returns:
            ToolDefinition object registered in the registry
            
        Example:
            >>> registry.register_from_typer_command(
            ...     "list",
            ...     schema.list_schemas,
            ...     "schema",
            ...     "List all XDM schemas"
            ... )
        """
        # Generate tool name: aep_{category}_{command}
        tool_name = f"aep_{category}_{command_name}"
        
        # Extract function signature
        sig = inspect.signature(typer_command)
        
        # Build JSON schema for parameters
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            # Skip 'self' and internal parameters
            if param_name in ('self', 'ctx'):
                continue
            
            # Infer JSON type from Python type annotation
            param_type = self._infer_json_type(param.annotation)
            param_description = self._extract_param_description(param, param_name)
            
            # Build property schema
            prop_schema = {
                "type": param_type,
                "description": param_description
            }
            
            # Add default value if available
            if param.default is not inspect.Parameter.empty:
                # Check if it's a Typer Option/Argument
                if hasattr(param.default, 'default'):
                    default_value = param.default.default
                    # Typer uses ... (Ellipsis) for required parameters
                    if default_value is not ... and default_value is not None:
                        prop_schema["default"] = default_value
                    elif default_value is ...:
                        required.append(param_name)
                else:
                    # Plain default value
                    prop_schema["default"] = param.default
            
            # Add enum values if available (from Typer)
            if hasattr(param.default, 'click_type'):
                click_type = param.default.click_type
                if hasattr(click_type, 'choices'):
                    prop_schema["enum"] = click_type.choices
            
            properties[param_name] = prop_schema
        
        # Use provided description or extract from docstring
        if description is None:
            description = self._extract_description(typer_command)
        
        # Create tool definition
        tool_def = ToolDefinition(
            name=tool_name,
            command_name=command_name,
            category=ToolCategory(category),
            description=description,
            input_schema={
                "type": "object",
                "properties": properties,
                "required": required
            },
            handler=typer_command
        )
        
        # Register tool
        self._tools[tool_name] = tool_def
        
        # Add to category index
        if category not in self._tools_by_category:
            self._tools_by_category[category] = []
        self._tools_by_category[category].append(tool_name)
        
        logger.debug(f"Registered tool: {tool_name} (category: {category})")
        
        return tool_def
    
    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            ToolDefinition if found, None otherwise
        """
        return self._tools.get(tool_name)
    
    def list_tools(self, category: Optional[str] = None, safe_only: bool = False) -> List[str]:
        """List all registered tool names.
        
        Args:
            category: Optional category filter
            safe_only: If True, only include safe (read-only) tools
            
        Returns:
            List of tool names
        """
        if category:
            tool_names = self._tools_by_category.get(category, [])
        else:
            tool_names = list(self._tools.keys())
        
        if safe_only:
            tool_names = [name for name in tool_names if is_safe_tool(name)]
        
        return tool_names
    
    def get_anthropic_tools(
        self,
        categories: Optional[List[str]] = None,
        safe_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get tool definitions in Anthropic API format.
        
        Converts registered tools into the format expected by Anthropic's
        Messages API for function calling.
        
        Args:
            categories: Optional list of categories to include
            safe_only: If True, only include safe (read-only) tools (default: True)
            
        Returns:
            List of tool definitions in Anthropic format
            
        Example format:
            [
                {
                    "name": "aep_schema_list",
                    "description": "List XDM schemas...",
                    "input_schema": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            ]
        """
        tools = list(self._tools.values())
        
        # Filter by category
        if categories:
            tools = [t for t in tools if t.category.value in categories]
        
        # Filter by safety
        if safe_only:
            tools = [t for t in tools if is_safe_tool(t.name)]
        
        # Convert to Anthropic format
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in tools
        ]
    
    def get_tool_count(self, safe_only: bool = False) -> int:
        """Get total number of registered tools.
        
        Args:
            safe_only: If True, only count safe tools
            
        Returns:
            Number of tools
        """
        if safe_only:
            return len([name for name in self._tools.keys() if is_safe_tool(name)])
        return len(self._tools)
    
    def get_categories(self) -> List[str]:
        """Get list of all registered categories.
        
        Returns:
            List of category names
        """
        return list(self._tools_by_category.keys())
    
    def _infer_json_type(self, python_type: Any) -> str:
        """Infer JSON schema type from Python type annotation.
        
        Args:
            python_type: Python type annotation
            
        Returns:
            JSON schema type string
        """
        # Handle None and empty annotations
        if python_type is inspect.Parameter.empty or python_type is None:
            return "string"
        
        # Get origin type for generics (Optional, List, etc.)
        origin = get_origin(python_type)
        
        # Handle Optional[T]
        if origin is type(None) or python_type is type(None):
            # Check if it's Optional[X]
            args = get_args(python_type)
            if args:
                # Get the non-None type
                inner_type = next((arg for arg in args if arg is not type(None)), None)
                if inner_type:
                    return self._infer_json_type(inner_type)
            return "string"
        
        # Handle basic types
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        
        # Check if it's a basic type
        actual_type = origin if origin is not None else python_type
        
        for py_type, json_type in type_map.items():
            if actual_type is py_type or python_type is py_type:
                return json_type
        
        # Default to string for unknown types
        return "string"
    
    def _extract_param_description(self, param: inspect.Parameter, param_name: str) -> str:
        """Extract parameter description from Typer annotations.
        
        Args:
            param: Function parameter
            param_name: Name of the parameter
            
        Returns:
            Description string
        """
        # Check if it has Typer help text
        if hasattr(param.default, 'help') and param.default.help:
            return param.default.help
        
        # Generate generic description
        return f"Parameter: {param_name}"
    
    def _extract_description(self, func: Callable) -> str:
        """Extract description from function docstring.
        
        Args:
            func: Function to extract description from
            
        Returns:
            Description string (first line of docstring or generic)
        """
        if func.__doc__:
            # Get first line of docstring
            lines = func.__doc__.strip().split('\n')
            first_line = lines[0].strip()
            if first_line:
                return first_line
        
        # Fallback to function name
        return f"Execute {func.__name__}"
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<ToolRegistry: {self.get_tool_count()} tools ({self.get_tool_count(safe_only=True)} safe)>"
