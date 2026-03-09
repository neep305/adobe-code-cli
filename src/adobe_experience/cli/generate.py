"""CLI commands for test data generation."""

import asyncio
import csv
import json
import logging
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adobe_experience.agent.inference import AIInferenceEngine
from adobe_experience.cli.command_metadata import CommandCategory, command_metadata
from adobe_experience.core.config import get_config
from adobe_experience.generators.domain_analyzer import DomainAnalyzer
from adobe_experience.generators.engine import DataGenerationEngine
from adobe_experience.generators.models import GenerationConfig, OutputFormat
from adobe_experience.generators.schema_generator import ERDToSchemaConverter
from adobe_experience.schema.xdm import XDMSchemaRegistry

# Try to import pandas for CSV, fall back to csv module
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

logger = logging.getLogger(__name__)
console = Console()

generate_app = typer.Typer(
    name="generate",
    help="🤖 Generate test data using AI",
    no_args_is_help=True,
)


@command_metadata(CommandCategory.ENHANCED, "Generate data from domain description")
@generate_app.command("from-domain")
def generate_from_domain(
    domain: str = typer.Argument(..., help="Domain name (e.g., 'ecommerce', 'healthcare')"),
    context: Optional[str] = typer.Option(
        None, "--context", "-c", help="Additional context or requirements"
    ),
    output_dir: Path = typer.Option(
        Path("generated-data"), "--output", "-o", help="Output directory"
    ),
    format: str = typer.Option(
        "json", "--format", "-f", help="Output format: json, csv, jsonl"
    ),
    records: int = typer.Option(10, "--records", "-n", help="Records per entity"),
    locale: str = typer.Option(
        "en_US", "--locale", "-l", help="Faker locale (en_US, ko_KR, ja_JP, etc.)"
    ),
    entity_count: int = typer.Option(5, "--entities", "-e", help="Number of entities (3-7)"),
    upload_schemas: bool = typer.Option(
        False, "--upload-schemas", help="Upload generated schemas to AEP"
    ),
    relationships: bool = typer.Option(
        True, "--relationships/--no-relationships", help="Generate with FK relationships"
    ),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducibility"),
):
    """Generate test data from domain description using AI.

    The AI will analyze the domain and automatically create:
    - Entity definitions (tables)
    - Field definitions with appropriate types
    - Relationships between entities
    - Realistic test data using Faker

    Examples:
        # Basic generation
        aep generate from-domain ecommerce

        # Korean locale with 100 records each
        aep generate from-domain ecommerce --locale ko_KR --records 100

        # With context and schema upload
        aep generate from-domain "healthcare" --context "Hospital patient management" --upload-schemas

        # CSV output
        aep generate from-domain ecommerce --format csv
    """
    start_time = time.time()

    try:
        config = get_config()

        # Validate format
        try:
            output_format = OutputFormat(format.lower())
        except ValueError:
            console.print(
                f"[red]Invalid format: {format}. Use: json, csv, or jsonl[/red]"
            )
            raise typer.Exit(1)

        # 1. Generate ERD from domain using AI
        console.print(f"\n[bold cyan]🧠 Analyzing domain:[/bold cyan] {domain}")
        if context:
            console.print(f"[dim]Context: {context}[/dim]")

        with console.status("[bold blue]Generating data model with AI..."):
            ai_engine = AIInferenceEngine(config)
            analyzer = DomainAnalyzer(ai_engine)
            erd = asyncio.run(
                analyzer.generate_erd_from_domain(domain, context, entity_count)
            )

        # Display ERD summary
        _display_erd_summary(erd)

        # 2. Generate XDM schemas
        console.print("\n[bold cyan]📐 Generating XDM schemas...[/bold cyan]")
        with console.status("[bold blue]Creating XDM schema definitions..."):
            schema_converter = ERDToSchemaConverter(config.aep_tenant_id)
            schemas = asyncio.run(schema_converter.generate_schemas_from_erd(erd))

        console.print(f"[green]✓[/green] Generated {len(schemas)} XDM schemas")

        # 3. Generate test data
        console.print("\n[bold cyan]🎲 Generating test data...[/bold cyan]")
        generation_config = GenerationConfig(
            output_format=output_format,
            record_count=records,
            locale=locale,
            preserve_relationships=relationships,
            seed=seed,
        )

        with console.status("[bold blue]Generating realistic test data..."):
            engine = DataGenerationEngine(config)
            data = asyncio.run(engine.generate_from_erd(erd, generation_config))

        # 4. Save files
        console.print("\n[bold cyan]💾 Saving generated data...[/bold cyan]")
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []

        for entity_name, records_list in data.items():
            if output_format == OutputFormat.JSON:
                file_path = output_dir / f"{entity_name}.json"
                file_path.write_text(
                    json.dumps(records_list, indent=2, default=str), encoding="utf-8"
                )
            elif output_format == OutputFormat.CSV:
                file_path = output_dir / f"{entity_name}.csv"
                if HAS_PANDAS:
                    # Use pandas for better CSV handling
                    df = pd.DataFrame(records_list)
                    df.to_csv(file_path, index=False, encoding="utf-8")
                else:
                    # Fallback to csv module
                    if records_list:
                        with open(file_path, "w", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=records_list[0].keys())
                            writer.writeheader()
                            writer.writerows(records_list)
            elif output_format == OutputFormat.JSONL:
                file_path = output_dir / f"{entity_name}.jsonl"
                with open(file_path, "w", encoding="utf-8") as f:
                    for record in records_list:
                        f.write(json.dumps(record, default=str) + "\n")

            saved_files.append(str(file_path))
            console.print(f"[green]✓[/green] {file_path}")

        # 5. Upload schemas (optional)
        if upload_schemas:
            console.print("\n[bold cyan]☁️ Uploading schemas to AEP...[/bold cyan]")
            with console.status("[bold blue]Uploading to Schema Registry..."):
                async def upload_all():
                    async with XDMSchemaRegistry(config) as registry:
                        uploaded = 0
                        for entity_name, schema in schemas.items():
                            try:
                                await registry.create_schema(schema)
                                uploaded += 1
                                console.print(
                                    f"[green]✓[/green] Uploaded schema: {entity_name}"
                                )
                            except Exception as e:
                                console.print(
                                    f"[yellow]⚠[/yellow] Failed to upload {entity_name}: {e}"
                                )
                        return uploaded

                uploaded_count = asyncio.run(upload_all())

            console.print(
                f"[green]✓[/green] Uploaded {uploaded_count}/{len(schemas)} schemas"
            )

        # 6. Display summary
        generation_time = time.time() - start_time
        _display_generation_summary(data, output_dir, generation_time)

        # Save metadata
        metadata_file = output_dir / "_metadata.json"
        metadata = {
            "domain": domain,
            "context": context,
            "generation_time": generation_time,
            "record_counts": {name: len(records) for name, records in data.items()},
            "output_format": format,
            "locale": locale,
            "relationships_preserved": relationships,
            "seed": seed,
            "entities": [e.name for e in erd.entities],
            "schemas_uploaded": upload_schemas,
        }
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        console.print(
            f"\n[bold green]✨ Generation complete![/bold green] ({generation_time:.2f}s)"
        )
        console.print(f"[dim]Output directory: {output_dir.absolute()}[/dim]")

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("Generation failed")
        raise typer.Exit(1)


def _display_erd_summary(erd):
    """Display ERD summary in a table."""
    table = Table(title=f"📊 {erd.domain.title()} Domain ERD", show_header=True)
    table.add_column("Entity", style="cyan", no_wrap=True)
    table.add_column("Fields", style="green", justify="right")
    table.add_column("Relationships", style="yellow", justify="right")
    table.add_column("Est. Records", style="magenta", justify="right")

    for entity in erd.entities:
        table.add_row(
            entity.name,
            str(len(entity.fields)),
            str(len(entity.relationships)),
            str(entity.estimated_record_count),
        )

    console.print("\n")
    console.print(table)
    console.print(
        f"\n[dim]Generation order: {' → '.join(erd.generation_order)}[/dim]"
    )


def _display_generation_summary(data, output_dir, generation_time):
    """Display generation results summary."""
    total_records = sum(len(records) for records in data.values())

    # Create summary panel
    summary_lines = [
        f"[bold]Total Records:[/bold] {total_records:,}",
        f"[bold]Entities:[/bold] {len(data)}",
        f"[bold]Output:[/bold] {output_dir}",
        f"[bold]Time:[/bold] {generation_time:.2f}s",
        "",
        "[bold]Records per entity:[/bold]",
    ]

    for entity_name, records in data.items():
        summary_lines.append(f"  • {entity_name}: {len(records):,}")

    panel = Panel(
        "\n".join(summary_lines),
        title="📈 Generation Summary",
        border_style="green",
    )
    console.print("\n")
    console.print(panel)
