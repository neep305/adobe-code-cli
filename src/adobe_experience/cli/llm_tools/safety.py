"""Safety module for LLM tools - defines safe and destructive operations."""

from typing import Set

# Phase 1: Read-only operations only
# These tools are safe to call without confirmation
SAFE_TOOLS: Set[str] = {
    # Schema operations (read-only)
    "aep_schema_list",
    "aep_schema_get",
    "aep_schema_analyze_dataset",
    
    # Dataset operations (read-only)
    "aep_dataset_list",
    "aep_dataset_get",
    
    # Dataflow operations (read-only)
    "aep_dataflow_list",
    "aep_dataflow_get",
    "aep_dataflow_runs",
    "aep_dataflow_failures",
    "aep_dataflow_health",
    "aep_dataflow_connections",
    
    # Segment operations (read-only) - Future
    # "aep_segment_list",
    # "aep_segment_get",
    
    # Destination operations (read-only) - Future
    # "aep_destination_list",
    # "aep_destination_get",
}

# Future Phase 2+: Write operations (require explicit user confirmation)
# These tools modify AEP resources and should be used with caution
DESTRUCTIVE_TOOLS: Set[str] = {
    # Schema operations (write)
    "aep_schema_create",
    "aep_schema_update",
    "aep_schema_delete",
    "aep_schema_validate",
    
    # Dataset operations (write)
    "aep_dataset_create",
    "aep_dataset_update",
    "aep_dataset_delete",
    "aep_dataset_create_batch",
    "aep_dataset_complete_batch",
    "aep_dataset_abort_batch",
    
    # Data ingestion (write)
    "aep_ingest_upload_file",
    "aep_ingest_upload_batch",
    
    # Dataflow operations (write)
    "aep_dataflow_create",
    "aep_dataflow_update",
    "aep_dataflow_delete",
    "aep_dataflow_enable",
    "aep_dataflow_disable",
    
    # Segment operations (write)
    "aep_segment_create",
    "aep_segment_update",
    "aep_segment_delete",
    "aep_segment_activate",
    
    # Destination operations (write)
    "aep_destination_create",
    "aep_destination_update",
    "aep_destination_delete",
    "aep_destination_activate",
}

# All registered tools (safe + destructive)
ALL_TOOLS = SAFE_TOOLS | DESTRUCTIVE_TOOLS


def is_safe_tool(tool_name: str) -> bool:
    """Check if a tool is safe to execute without confirmation.
    
    Args:
        tool_name: Name of the tool to check
        
    Returns:
        True if the tool is in SAFE_TOOLS, False otherwise
        
    Example:
        >>> is_safe_tool("aep_schema_list")
        True
        >>> is_safe_tool("aep_schema_create")
        False
    """
    return tool_name in SAFE_TOOLS


def is_destructive_tool(tool_name: str) -> bool:
    """Check if a tool is destructive (requires confirmation).
    
    Args:
        tool_name: Name of the tool to check
        
    Returns:
        True if the tool is in DESTRUCTIVE_TOOLS, False otherwise
        
    Example:
        >>> is_destructive_tool("aep_schema_create")
        True
        >>> is_destructive_tool("aep_schema_list")
        False
    """
    return tool_name in DESTRUCTIVE_TOOLS


def get_tool_safety_level(tool_name: str) -> str:
    """Get the safety level of a tool.
    
    Args:
        tool_name: Name of the tool to check
        
    Returns:
        "safe", "destructive", or "unknown"
        
    Example:
        >>> get_tool_safety_level("aep_schema_list")
        'safe'
        >>> get_tool_safety_level("aep_schema_create")
        'destructive'
        >>> get_tool_safety_level("unknown_tool")
        'unknown'
    """
    if tool_name in SAFE_TOOLS:
        return "safe"
    elif tool_name in DESTRUCTIVE_TOOLS:
        return "destructive"
    else:
        return "unknown"


def get_safety_warning(tool_name: str) -> str:
    """Get a safety warning message for a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Warning message appropriate for the tool's safety level
    """
    if is_destructive_tool(tool_name):
        return (
            f"⚠️  WARNING: '{tool_name}' is a destructive operation that will modify AEP resources. "
            "This operation cannot be undone. Please confirm before proceeding."
        )
    elif not is_safe_tool(tool_name):
        return (
            f"⚠️  WARNING: '{tool_name}' is not recognized as a safe operation. "
            "This tool may modify AEP resources or have unexpected side effects."
        )
    else:
        return ""
