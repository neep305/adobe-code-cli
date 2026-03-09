"""LLM-powered CLI tools - Convert CLI commands to LLM-callable tools."""

from adobe_experience.cli.llm_tools.executor import CommandExecutor
from adobe_experience.cli.llm_tools.registry import ToolRegistry
from adobe_experience.cli.llm_tools.safety import SAFE_TOOLS, is_safe_tool

__all__ = [
    "ToolRegistry",
    "CommandExecutor",
    "SAFE_TOOLS",
    "is_safe_tool",
    "register_safe_tools",
]


def register_safe_tools(registry: ToolRegistry) -> None:
    """Register Phase 1 safe (read-only) tools.
    
    This function registers only read-only CLI commands as LLM tools.
    Write operations are explicitly excluded for safety.
    
    Args:
        registry: ToolRegistry instance to register tools into
    """
    from adobe_experience.cli import dataflow, dataset, schema
    
    # Schema tools (3 read-only)
    registry.register_from_typer_command(
        command_name="list",
        typer_command=schema.list_schemas,
        category="schema",
        description="List XDM schemas in AEP with names, classes (Profile/ExperienceEvent), and creation dates"
    )
    
    registry.register_from_typer_command(
        command_name="get",
        typer_command=schema.get_schema,
        category="schema",
        description="Get detailed XDM schema definition by ID including all fields, data types, and relationships"
    )
    
    registry.register_from_typer_command(
        command_name="analyze_dataset",
        typer_command=schema.analyze_dataset,
        category="schema",
        description="Analyze multi-entity ERD structure from directory, showing relationships between entities"
    )
    
    # Dataset tools (2 read-only)
    registry.register_from_typer_command(
        command_name="list",
        typer_command=dataset.list_datasets,
        category="dataset",
        description="List datasets in AEP with schema references, state (enabled/disabled), and Profile enablement status"
    )
    
    registry.register_from_typer_command(
        command_name="get",
        typer_command=dataset.get_dataset,
        category="dataset",
        description="Get detailed dataset information by ID including schema, batch history, and configuration"
    )
    
    # Dataflow tools (6 read-only)
    registry.register_from_typer_command(
        command_name="list",
        typer_command=dataflow.list_dataflows,
        category="dataflow",
        description="List all dataflows with state (enabled/disabled), source connections, and flow specifications"
    )
    
    registry.register_from_typer_command(
        command_name="get",
        typer_command=dataflow.get_dataflow,
        category="dataflow",
        description="Get detailed dataflow information including connections, schedules, and inherited attributes"
    )
    
    registry.register_from_typer_command(
        command_name="runs",
        typer_command=dataflow.list_runs,
        category="dataflow",
        description="List execution runs for a dataflow showing status, records processed, duration, and errors"
    )
    
    registry.register_from_typer_command(
        command_name="failures",
        typer_command=dataflow.list_failures,
        category="dataflow",
        description="Show only failed dataflow runs with detailed error messages and activity failures"
    )
    
    registry.register_from_typer_command(
        command_name="health",
        typer_command=dataflow.analyze_health,
        category="dataflow",
        description="Analyze dataflow health metrics: success rate, error frequency, average duration, and common failure patterns"
    )
    
    registry.register_from_typer_command(
        command_name="connections",
        typer_command=dataflow.get_connections,
        category="dataflow",
        description="Show source and target connection details for a dataflow including connection specs and parameters"
    )
