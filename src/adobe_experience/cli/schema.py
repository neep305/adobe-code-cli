"""Schema management commands for Adobe Experience Platform."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()
schema_app = typer.Typer(help="XDM schema management commands")


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
    class_id: Optional[str] = typer.Option(
        None,
        "--class-id",
        help="XDM class ID (e.g., https://ns.adobe.com/xdm/context/profile)",
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
        adobe aep schema create --name "Customer Events" --from-sample data.json
        adobe aep schema create -n "Customer Profile" -f customers.json --use-ai --upload
    """
    if not from_sample:
        console.print("[red]Error: --from-sample is required[/red]")
        raise typer.Exit(1)

    if not from_sample.exists():
        console.print(f"[red]Error: File not found: {from_sample}[/red]")
        raise typer.Exit(1)

    try:
        # Import here to avoid circular imports
        from adobe_experience.agent.inference import AIInferenceEngine, SchemaGenerationRequest
        from adobe_experience.aep.client import AEPClient
        from adobe_experience.core.config import get_config
        from adobe_experience.schema.xdm import XDMSchemaAnalyzer, XDMSchemaRegistry

        # Load sample data
        with console.status(f"[bold blue]Loading sample data from {from_sample}..."):
            with open(from_sample, "r", encoding="utf-8") as f:
                sample_data = json.load(f)

            if not isinstance(sample_data, list):
                sample_data = [sample_data]

        console.print(f"[green]✓[/green] Loaded {len(sample_data)} sample records")

        # Generate schema
        if use_ai:
            console.print("\n[bold cyan]Using AI to generate optimized schema...[/bold cyan]")

            engine = AIInferenceEngine()
            request = SchemaGenerationRequest(
                sample_data=sample_data,
                schema_name=name,
                schema_description=description,
            )

            response = asyncio.run(engine.generate_schema_with_ai(request))
            schema = response.xdm_schema

            # Display AI insights
            console.print("\n[bold]AI Analysis:[/bold]")
            console.print(Panel(response.reasoning, title="Reasoning", border_style="cyan"))

            if response.identity_recommendations:
                console.print("\n[bold]Identity Recommendations:[/bold]")
                for field, reason in response.identity_recommendations.items():
                    console.print(f"  • {field}: {reason}")

            if response.data_quality_issues:
                console.print("\n[yellow]Data Quality Issues:[/yellow]")
                for issue in response.data_quality_issues:
                    console.print(f"  • {issue}")

        else:
            with console.status("[bold blue]Analyzing schema structure..."):
                schema = XDMSchemaAnalyzer.from_sample_data(
                    sample_data,
                    name,
                    description,
                )

        console.print(f"\n[green]✓[/green] Schema '{name}' generated successfully")

        # Display schema
        schema_json = schema.model_dump(exclude_none=True, by_alias=True)
        syntax = Syntax(
            json.dumps(schema_json, indent=2),
            "json",
            theme="monokai",
            line_numbers=True,
        )
        console.print("\n[bold]Generated Schema:[/bold]")
        console.print(syntax)

        # Save to file
        if output:
            output.write_text(json.dumps(schema_json, indent=2), encoding="utf-8")
            console.print(f"\n[green]✓[/green] Schema saved to {output}")

        # Upload to AEP
        if upload:
            config = get_config()
            client = AEPClient(config)
            registry = XDMSchemaRegistry(client)

            console.print("\n[bold cyan]Uploading schema to AEP...[/bold cyan]")

            try:
                uploaded_schema = asyncio.run(
                    registry.create_schema(
                        schema,
                        class_id=class_id or "https://ns.adobe.com/xdm/context/experienceevent"
                    )
                )

                console.print(f"[green]✓[/green] Schema uploaded successfully!")
                console.print(f"  Schema ID: [cyan]{uploaded_schema.get('$id', 'N/A')}[/cyan]")

            except Exception as e:
                console.print(f"\n[red]✗ Upload failed: {e}[/red]")
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


@schema_app.command("list")
def list_schemas(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of schemas to display"),
) -> None:
    """List XDM schemas from Adobe Experience Platform.

    Examples:
        adobe aep schema list
        adobe aep schema list --limit 20
    """
    try:
        from adobe_experience.aep.client import AEPClient
        from adobe_experience.core.config import get_config
        from adobe_experience.schema.xdm import XDMSchemaRegistry

        config = get_config()
        client = AEPClient(config)
        registry = XDMSchemaRegistry(client)

        with console.status("[bold blue]Fetching schemas from AEP..."):
            schemas = asyncio.run(registry.list_schemas())

        if not schemas:
            console.print("[yellow]No schemas found[/yellow]")
            return

        # Create table
        table = Table(title=f"XDM Schemas (showing {min(limit, len(schemas))} of {len(schemas)})")
        table.add_column("Title", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Version", justify="center")

        for schema in schemas[:limit]:
            table.add_row(
                schema.get("title", "N/A"),
                schema.get("$id", "N/A")[:60] + "...",
                schema.get("version", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@schema_app.command("get")
def get_schema(
    schema_id: str = typer.Argument(..., help="Schema ID or name"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save schema to file",
    ),
) -> None:
    """Get details of a specific XDM schema.

    Examples:
        adobe aep schema get <schema-id>
        adobe aep schema get <schema-id> --output schema.json
    """
    try:
        from adobe_experience.aep.client import AEPClient
        from adobe_experience.core.config import get_config
        from adobe_experience.schema.xdm import XDMSchemaRegistry

        config = get_config()
        client = AEPClient(config)
        registry = XDMSchemaRegistry(client)

        with console.status(f"[bold blue]Fetching schema {schema_id}..."):
            schema = asyncio.run(registry.get_schema(schema_id))

        console.print(f"\n[green]✓[/green] Schema retrieved successfully")

        # Display schema
        syntax = Syntax(
            json.dumps(schema, indent=2),
            "json",
            theme="monokai",
            line_numbers=True,
        )
        console.print(syntax)

        # Save to file
        if output:
            output.write_text(json.dumps(schema, indent=2), encoding="utf-8")
            console.print(f"\n[green]✓[/green] Schema saved to {output}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


__all__ = ["schema_app"]
