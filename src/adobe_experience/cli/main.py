"""CLI application for Adobe Experience Cloud."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from adobe_experience.aep.client import AEPClient
from adobe_experience.agent.inference import AIInferenceEngine, SchemaGenerationRequest
from adobe_experience.cli.auth import auth_app
from adobe_experience.cli.ai import ai_app
from adobe_experience.cli.onboarding import onboarding_app
from adobe_experience.core.config import get_config
from adobe_experience.schema.xdm import XDMSchemaAnalyzer, XDMSchemaRegistry

# Create unified Adobe Experience Cloud CLI
app = typer.Typer(
    name="adobe",
    help="Adobe Experience Cloud CLI - Unified interface for AEP, Target, Analytics, and more",
    add_completion=False,
    rich_markup_mode="rich",
)

# Import AEP app
from adobe_experience.aep.cli import aep_app

# Register product subcommands
app.add_typer(
    aep_app,
    name="aep",
    help="Adobe Experience Platform commands"
)

# TODO: Add aliases support when Typer version supports it
# For now, users can use: adobe aep

# Register common commands
app.add_typer(auth_app, name="auth", help="Authentication management")
app.add_typer(ai_app, name="ai", help="AI provider configuration")
app.add_typer(onboarding_app, name="onboarding", help="Interactive onboarding tutorials")

console = Console()


@app.command("init")
def init_command() -> None:
    """Initialize Adobe Experience Cloud CLI with interactive setup wizard.
    
    Examples:
        adobe init
    """
    from adobe_experience.cli.init import setup
    setup()


@app.command()
def version() -> None:
    """Show version information."""
    from adobe_experience import __version__

    console.print(f"[cyan]Adobe Experience Cloud CLI[/cyan] v{__version__}")
    console.print("\n[dim]Supported products:[/dim]")
    console.print("  • [cyan]aep[/cyan] - Adobe Experience Platform")


# Legacy schema commands (moved to aep subcommand)
schema_app = typer.Typer(help="[deprecated] Use 'adobe aep schema' instead")


@schema_app.command("create")
def create_schema(
    name: str = typer.Option(..., "--name", "-n", help="Schema name"),
    from_sample: Optional[Path] = typer.Option(
        None,
        "--from-sample",
        "-f",
        help="Path to sample JSON data file",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Schema description",
    ),
    use_ai: bool = typer.Option(
        False,
        "--use-ai",
        help="Use AI inference for enhanced schema generation",
    ),
    upload: bool = typer.Option(
        False,
        "--upload",
        help="Upload schema to AEP after generation",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save schema to file",
    ),
) -> None:
    """Create XDM schema from sample data.

    Examples:
        adobe-aep schema create --name "Customer Events" --from-sample data.json
        adobe-aep schema create -n "Customer Profile" -f customers.json --use-ai --upload
    """
    if not from_sample:
        console.print("[red]Error: --from-sample is required[/red]")
        raise typer.Exit(1)

    if not from_sample.exists():
        console.print(f"[red]Error: File not found: {from_sample}[/red]")
        raise typer.Exit(1)

    try:
        # Load sample data
        with console.status(f"[bold blue]Loading sample data from {from_sample}..."):
            with from_sample.open("r", encoding="utf-8") as f:
                sample_data = json.load(f)

            if not isinstance(sample_data, list):
                sample_data = [sample_data]

        console.print(f"[green]OK[/green] Loaded {len(sample_data)} sample records")

        # Generate schema
        if use_ai:
            console.print("[bold blue]Using AI inference for schema generation...[/bold blue]")
            schema_result = asyncio.run(_generate_schema_with_ai(name, sample_data, description))

            # Display AI insights
            console.print("\n[bold]AI Analysis:[/bold]")
            console.print(schema_result.reasoning)

            if schema_result.identity_recommendations:
                table = Table(title="Identity Field Recommendations")
                table.add_column("Field", style="cyan")
                table.add_column("Namespace", style="magenta")
                table.add_column("Reasoning", style="green")

                for field, reason in schema_result.identity_recommendations.items():
                    table.add_row(field, "Auto-detected", reason)

                console.print(table)

            if schema_result.data_quality_issues:
                console.print("\n[yellow]WARNING: Data Quality Issues:[/yellow]")
                for issue in schema_result.data_quality_issues:
                    console.print(f"  • {issue}")

            schema = schema_result.xdm_schema
        else:
            with console.status("[bold blue]Generating XDM schema..."):
                config = get_config()
                schema = XDMSchemaAnalyzer.from_sample_data(
                    sample_data, name, description, tenant_id=config.aep_tenant_id
                )

        console.print(f"\n[green]OK[/green] Generated schema: {schema.title}")

        # Display schema
        schema_json = schema.model_dump_json(by_alias=True, exclude_none=True, indent=2)
        syntax = Syntax(schema_json, "json", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"Schema: {name}", border_style="blue"))

        # Save to file
        if output:
            output.write_text(schema_json, encoding="utf-8")
            console.print(f"[green]OK[/green] Schema saved to {output}")

        # Upload to AEP
        if upload:
            console.print("\n[bold blue]Uploading schema to AEP...[/bold blue]")
            result = asyncio.run(_upload_schema(schema))
            console.print(f"[green]OK[/green] Schema created in AEP")
            console.print(f"Schema ID: {result.get('$id')}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@schema_app.command("list")
def list_schemas(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of schemas to display"),
) -> None:
    """List all XDM schemas in AEP."""
    try:
        with console.status("[bold blue]Fetching schemas from AEP..."):
            result = asyncio.run(_list_schemas(limit))

        schemas = result.get("results", [])

        if not schemas:
            console.print("[yellow]No schemas found[/yellow]")
            return

        table = Table(title=f"XDM Schemas ({len(schemas)} total)")
        table.add_column("Title", style="cyan", no_wrap=False)
        table.add_column("Schema ID", style="magenta")
        table.add_column("Version", style="green")

        for schema in schemas:
            table.add_row(
                schema.get("title", "N/A"),
                schema.get("$id", "N/A"),
                schema.get("version", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@schema_app.command("get")
def get_schema(
    schema_id: str = typer.Argument(..., help="Schema ID or name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save schema to file"),
) -> None:
    """Get schema details by ID."""
    try:
        with console.status(f"[bold blue]Fetching schema {schema_id}..."):
            schema = asyncio.run(_get_schema(schema_id))

        schema_json = json.dumps(schema, indent=2)
        syntax = Syntax(schema_json, "json", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=schema.get("title", schema_id), border_style="blue"))

        if output:
            output.write_text(schema_json, encoding="utf-8")
            console.print(f"[green]OK[/green] Schema saved to {output}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Async helper functions


async def _generate_schema_with_ai(
    name: str,
    sample_data: list,
    description: Optional[str],
):
    """Generate schema using AI inference."""
    engine = AIInferenceEngine()
    request = SchemaGenerationRequest(
        sample_data=sample_data,
        schema_name=name,
        schema_description=description,
    )
    return await engine.generate_schema_with_ai(request)


async def _upload_schema(schema):
    """Upload schema to AEP."""
    async with AEPClient() as client:
        registry = XDMSchemaRegistry(client)
        return await registry.create_schema(schema)


async def _list_schemas(limit: int):
    """List schemas from AEP."""
    async with AEPClient() as client:
        registry = XDMSchemaRegistry(client)
        return await registry.list_schemas(limit)


async def _get_schema(schema_id: str):
    """Get schema from AEP."""
    async with AEPClient() as client:
        registry = XDMSchemaRegistry(client)
        return await registry.get_schema(schema_id)


if __name__ == "__main__":
    app()
