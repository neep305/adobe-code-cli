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
            # Load config for tenant_id even without AI
            config = get_config()
            with console.status("[bold blue]Analyzing schema structure..."):
                schema = XDMSchemaAnalyzer.from_sample_data(
                    sample_data,
                    name,
                    description,
                    tenant_id=config.aep_tenant_id,
                    class_id=class_id,
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

            console.print("\n[bold cyan]Uploading schema to AEP...[/bold cyan]")

            try:
                async def upload_schema():
                    async with AEPClient(config) as client:
                        registry = XDMSchemaRegistry(client)
                        return await registry.create_schema(schema)
                
                uploaded_schema = asyncio.run(upload_schema())

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
        
        async def fetch_schemas():
            async with AEPClient(config) as client:
                registry = XDMSchemaRegistry(client)
                return await registry.list_schemas()

        with console.status("[bold blue]Fetching schemas from AEP..."):
            response = asyncio.run(fetch_schemas())
        
        # Extract schemas from response
        schemas = response.get("results", [])

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
        
        async def fetch_schema():
            async with AEPClient(config) as client:
                registry = XDMSchemaRegistry(client)
                return await registry.get_schema(schema_id)

        with console.status(f"[bold blue]Fetching schema {schema_id}..."):
            schema = asyncio.run(fetch_schema())

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


@schema_app.command("list-fieldgroups")
def list_field_groups(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of field groups to display"),
    container: str = typer.Option("tenant", "--container", "-c", help="Container ID (tenant or global)"),
) -> None:
    """List field groups from Adobe Experience Platform.

    Examples:
        adobe aep schema list-fieldgroups
        adobe aep schema list-fieldgroups --limit 20 --container global
    """
    try:
        from adobe_experience.aep.client import AEPClient
        from adobe_experience.core.config import get_config
        from adobe_experience.schema.xdm import XDMSchemaRegistry

        config = get_config()
        
        async def fetch_field_groups():
            async with AEPClient(config) as client:
                registry = XDMSchemaRegistry(client)
                return await registry.list_field_groups(container_id=container, limit=limit)

        with console.status("[bold blue]Fetching field groups from AEP..."):
            response = asyncio.run(fetch_field_groups())
        
        # Extract field groups from response
        field_groups = response.get("results", [])

        if not field_groups:
            console.print("[yellow]No field groups found[/yellow]")
            return

        # Display table
        table = Table(title=f"Field Groups (showing {min(limit, len(field_groups))} of {len(field_groups)})")
        table.add_column("Title", style="cyan", no_wrap=False)
        table.add_column("ID", style="green")
        table.add_column("Version", style="yellow")

        for fg in field_groups[:limit]:
            table.add_row(
                fg.get("title", "N/A"),
                fg.get("$id", "N/A"),
                fg.get("version", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@schema_app.command("get-fieldgroup")
def get_field_group(
    field_group_id: str = typer.Argument(..., help="Field group ID"),
    container: str = typer.Option("tenant", "--container", "-c", help="Container ID (tenant or global)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save to file"),
) -> None:
    """Get a specific field group by ID.

    Examples:
        adobe aep schema get-fieldgroup <FIELD_GROUP_ID>
        adobe aep schema get-fieldgroup <ID> --output fieldgroup.json
    """
    try:
        from adobe_experience.aep.client import AEPClient
        from adobe_experience.core.config import get_config
        from adobe_experience.schema.xdm import XDMSchemaRegistry

        config = get_config()
        
        async def fetch_field_group():
            async with AEPClient(config) as client:
                registry = XDMSchemaRegistry(client)
                return await registry.get_field_group(field_group_id, container_id=container)

        with console.status(f"[bold blue]Fetching field group {field_group_id}..."):
            field_group = asyncio.run(fetch_field_group())

        console.print(f"\n[green]✓[/green] Field group retrieved successfully")

        # Display field group
        syntax = Syntax(
            json.dumps(field_group, indent=2),
            "json",
            theme="monokai",
            line_numbers=True,
        )
        console.print(syntax)

        # Save to file
        if output:
            output.write_text(json.dumps(field_group, indent=2), encoding="utf-8")
            console.print(f"\n[green]✓[/green] Field group saved to {output}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@schema_app.command("upload-and-validate")
def upload_and_validate(
    name: str = typer.Option(..., "--name", "-n", help="Schema name"),
    from_sample: Path = typer.Option(..., "--from-sample", "-f", help="Sample JSON data for schema generation"),
    validate_data: Path = typer.Option(..., "--validate-data", "-v", help="Actual data to validate against schema"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Schema description"),
    class_id: Optional[str] = typer.Option(
        "https://ns.adobe.com/xdm/context/profile",
        "--class-id",
        help="XDM class ID",
    ),
    use_ai: bool = typer.Option(True, "--use-ai/--no-ai", help="Use AI for schema generation and validation"),
) -> None:
    """Create schema, upload to AEP, and validate with actual data.
    
    This is an end-to-end workflow that:
    1. Generates XDM schema from sample data
    2. Uploads schema to Adobe Experience Platform
    3. Validates actual data against the uploaded schema
    4. Shows detailed validation report with AI insights

    Examples:
        adobe aep schema upload-and-validate \\
            --name "Customer Profile" \\
            --from-sample sample.json \\
            --validate-data actual_customers.json \\
            --use-ai
    """
    try:
        from adobe_experience.agent.inference import AIInferenceEngine, SchemaGenerationRequest
        from adobe_experience.aep.client import AEPClient
        from adobe_experience.core.config import get_config
        from adobe_experience.schema.models import XDMSchemaRef
        from adobe_experience.schema.xdm import XDMSchemaAnalyzer, XDMSchemaRegistry

        # Validate input files
        if not from_sample.exists():
            console.print(f"[red]Error: Sample data file not found: {from_sample}[/red]")
            raise typer.Exit(1)
        
        if not validate_data.exists():
            console.print(f"[red]Error: Validation data file not found: {validate_data}[/red]")
            raise typer.Exit(1)

        console.print(Panel.fit(
            "[bold cyan]Schema Upload & Validation Workflow[/bold cyan]\n"
            "Step 1: Generate Schema\n"
            "Step 2: Upload to AEP\n"
            "Step 3: Validate Data\n"
            "Step 4: Show Report",
            border_style="cyan"
        ))

        # Step 1: Load sample data and generate schema
        console.print("\n[bold]Step 1: Generating Schema[/bold]")
        with console.status("[bold blue]Loading sample data..."):
            with open(from_sample, "r", encoding="utf-8") as f:
                sample_data = json.load(f)
            if not isinstance(sample_data, list):
                sample_data = [sample_data]
        
        console.print(f"[green]✓[/green] Loaded {len(sample_data)} sample records")

        # Load config early to check authentication
        config = get_config()

        if use_ai:
            console.print("[cyan]Using AI to generate optimized schema...[/cyan]")
            engine = AIInferenceEngine(config)
            request = SchemaGenerationRequest(
                sample_data=sample_data,
                schema_name=name,
                schema_description=description,
                tenant_id=config.aep_tenant_id,
                class_id=class_id,
            )
            response = asyncio.run(engine.generate_schema_with_ai(request))
            schema = response.xdm_schema
        else:
            console.print("[cyan]Analyzing schema structure...[/cyan]")
            schema = XDMSchemaAnalyzer.from_sample_data(
                sample_data,
                name,
                description,
                tenant_id=config.aep_tenant_id,
                class_id=class_id,
            )

        console.print(f"[green]✓[/green] Schema '{name}' generated successfully")

        # Debug: Show schema structure
        if config.aep_tenant_id:
            console.print(f"[dim]  Tenant namespace: _{config.aep_tenant_id}[/dim]")
            if schema.properties and f"_{config.aep_tenant_id}" in schema.properties:
                tenant_fields = schema.properties[f"_{config.aep_tenant_id}"].properties
                if tenant_fields:
                    console.print(f"[dim]  Custom fields: {', '.join(tenant_fields.keys())}[/dim]")

        # Step 2: Upload schema to AEP
        console.print("\n[bold]Step 2: Uploading to AEP[/bold]")
        
        field_group_id = None
        
        async def upload_schema_with_fieldgroup():
            async with AEPClient(config) as client:
                registry = XDMSchemaRegistry(client)
                
                # If schema has custom tenant fields, create a field group first
                if config.aep_tenant_id and schema.properties and f"_{config.aep_tenant_id}" in schema.properties:
                    console.print("[cyan]Creating custom field group...[/cyan]")
                    tenant_field = schema.properties[f"_{config.aep_tenant_id}"]
                    
                    # Create field group with custom fields
                    field_group_name = f"{name} Custom Fields"
                    field_group_data = {
                        "$schema": "http://json-schema.org/draft-06/schema#",
                        "$id": f"https://ns.adobe.com/{config.aep_tenant_id}/mixins/{name.lower().replace(' ', '_')}_custom",
                        "title": field_group_name,
                        "description": f"Custom fields for {name}",
                        "type": "object",
                        "meta:intendedToExtend": [schema.meta_class],
                        "definitions": {
                            "customFields": {
                                "properties": {
                                    f"_{config.aep_tenant_id}": tenant_field.model_dump(by_alias=True, exclude_none=True)
                                }
                            }
                        },
                        "allOf": [
                            {
                                "$ref": "#/definitions/customFields"
                            }
                        ]
                    }
                    
                    field_group_response = await registry.create_field_group(field_group_data)
                    created_fg_id = field_group_response.get("$id")
                    console.print(f"[green]✓[/green] Field group created: {field_group_name}")
                    
                    # Update schema to reference the field group instead of inline properties
                    schema.properties = None  # Remove inline properties
                    schema.all_of.append(XDMSchemaRef(ref=created_fg_id))
                    
                    return await registry.create_schema(schema), created_fg_id
                else:
                    return await registry.create_schema(schema), None
        
        with console.status("[bold blue]Uploading schema to Adobe Experience Platform..."):
            uploaded_schema, field_group_id = asyncio.run(upload_schema_with_fieldgroup())
        
        schema_id = uploaded_schema.get("$id", "unknown")
        console.print(f"[green]✓[/green] Schema uploaded successfully!")
        console.print(f"  Schema ID: [cyan]{schema_id}[/cyan]")

        # Step 3: Load validation data and validate
        console.print("\n[bold]Step 3: Validating Data[/bold]")
        with console.status("[bold blue]Loading validation data..."):
            with open(validate_data, "r", encoding="utf-8") as f:
                validation_data = json.load(f)
            if not isinstance(validation_data, list):
                validation_data = [validation_data]
        
        console.print(f"[green]✓[/green] Loaded {len(validation_data)} validation records")

        # Validate data against schema
        with console.status("[bold blue]Running validation..."):
            # Reuse engine if already created, or create new one
            if not use_ai or 'engine' not in locals():
                engine = AIInferenceEngine(config)
            
            schema_dict = schema.model_dump(exclude_none=True, by_alias=True)
            validation_report = asyncio.run(engine.validate_schema_against_data(schema_dict, validation_data))

        # Step 4: Display validation report
        console.print("\n[bold]Step 4: Validation Report[/bold]\n")
        _display_validation_report(validation_report)

    except Exception as e:
        error_msg = str(e)
        console.print(f"\n[red]Error: {error_msg}[/red]")
        
        # Provide specific guidance for common errors
        if "401" in error_msg or "Unauthorized" in error_msg or "authentication" in error_msg.lower():
            console.print("\n[yellow]Authentication failed. Please check:[/yellow]")
            console.print("  1. Run 'adobe auth test' to verify credentials")
            console.print("  2. Check your .env file has valid AEP credentials")
            console.print("  3. Ensure your Adobe Developer Console project has Schema Registry permissions")
        elif "403" in error_msg or "Forbidden" in error_msg:
            console.print("\n[yellow]Permission denied. Please check:[/yellow]")
            console.print("  1. Your Adobe Developer Console project has 'Manage Schemas' permission")
            console.print("  2. You're using the correct sandbox (current: prod)")
        elif "404" in error_msg:
            console.print("\n[yellow]Resource not found. Please check:[/yellow]")
            console.print("  1. The sandbox name is correct")
            console.print("  2. The API endpoint is accessible")
        elif "AI" in error_msg or "Anthropic" in error_msg or "OpenAI" in error_msg:
            console.print("\n[yellow]AI service error. Please check:[/yellow]")
            console.print("  1. Run 'adobe ai list-keys' to verify API keys")
            console.print("  2. Try running without --use-ai flag")
        
        if "--verbose" not in error_msg:
            console.print("\n[dim]For detailed error trace, check the logs above[/dim]")
        
        raise typer.Exit(1)


def _display_validation_report(report) -> None:
    """Display validation report with Rich formatting."""
    from adobe_experience.agent.inference import ValidationSeverity
    
    # Overall status
    status_color = {
        "passed": "green",
        "passed_with_warnings": "yellow",
        "failed": "red",
    }.get(report.overall_status, "white")
    
    status_icon = {
        "passed": "✓",
        "passed_with_warnings": "⚠",
        "failed": "✗",
    }.get(report.overall_status, "?")
    
    console.print(Panel(
        f"[bold {status_color}]{status_icon} Overall Status: {report.overall_status.upper().replace('_', ' ')}[/bold {status_color}]\n\n"
        f"Schema: [cyan]{report.schema_title}[/cyan]\n"
        f"Records Validated: {report.total_records_validated}\n"
        f"Total Issues: {report.total_issues}\n"
        f"  • Critical: [red]{report.critical_issues}[/red]\n"
        f"  • Warnings: [yellow]{report.warning_issues}[/yellow]\n"
        f"  • Info: [blue]{report.info_issues}[/blue]",
        title="Validation Summary",
        border_style=status_color,
    ))

    # AI Summary
    if report.ai_summary:
        console.print("\n")
        console.print(Panel(
            report.ai_summary,
            title="[bold cyan]AI Analysis[/bold cyan]",
            border_style="cyan",
        ))

    # Issues table
    if report.issues:
        console.print("\n[bold]Detailed Issues:[/bold]\n")
        
        # Group by severity
        for severity in [ValidationSeverity.CRITICAL, ValidationSeverity.WARNING, ValidationSeverity.INFO]:
            severity_issues = [issue for issue in report.issues if issue.severity == severity]
            
            if not severity_issues:
                continue
            
            severity_color = {
                ValidationSeverity.CRITICAL: "red",
                ValidationSeverity.WARNING: "yellow",
                ValidationSeverity.INFO: "blue",
            }[severity]
            
            table = Table(
                title=f"{severity.value.upper()} Issues ({len(severity_issues)})",
                border_style=severity_color,
                show_lines=True,
            )
            table.add_column("Field", style="cyan", no_wrap=False)
            table.add_column("Issue Type", style="magenta")
            table.add_column("Message", style="white", no_wrap=False)
            table.add_column("Suggestion", style="green", no_wrap=False)
            
            for issue in severity_issues[:10]:  # Limit to 10 per severity
                table.add_row(
                    issue.field_path,
                    issue.issue_type,
                    issue.message,
                    issue.suggestion or "-",
                )
            
            console.print(table)
            console.print()
        
        if len(report.issues) > 30:
            console.print(f"[dim]... and {len(report.issues) - 30} more issues[/dim]\n")


@schema_app.command("analyze-dataset")
def analyze_dataset(
    dataset_dir: Path = typer.Option(
        ...,
        "--dir",
        "-d",
        help="Directory containing JSON data files",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    sample_size: int = typer.Option(
        10,
        "--sample-size",
        "-s",
        help="Number of records to sample per file",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save analysis result to JSON file",
    ),
    format_type: str = typer.Option(
        "rich",
        "--format",
        help="Output format: rich (default), json, mermaid",
    ),
) -> None:
    """Analyze multi-file dataset and infer ERD relationships using AI.
    
    This command scans all JSON files in a directory, analyzes their structure,
    and uses AI to infer entity relationships, recommend XDM classes, and suggest
    identity strategies for Adobe Experience Platform schema design.
    
    Example:
        adobe aep schema analyze-dataset --dir test-data/ecommerce/
    """
    from adobe_experience.agent.inference import AIInferenceEngine
    from adobe_experience.core.config import get_config
    from adobe_experience.schema.dataset_scanner import DatasetScanner
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.tree import Tree
    
    console.print(Panel.fit(
        "[bold cyan]Dataset ERD Analysis[/bold cyan]\n"
        "AI-powered relationship inference and schema design recommendations",
        border_style="cyan"
    ))
    
    # Step 1: Scan directory
    console.print("\n[bold]Step 1: Scanning Dataset Files[/bold]")
    
    scanner = DatasetScanner(sample_size=sample_size)
    
    with console.status("[bold blue]Scanning JSON files..."):
        try:
            scan_result = scanner.scan_directory(dataset_dir)
        except Exception as e:
            console.print(f"[red]Error scanning directory: {e}[/red]")
            raise typer.Exit(1)
    
    console.print(f"[green]✓[/green] Found {scan_result.total_files} entities with {scan_result.total_records} total records")
    
    # Show discovered entities
    entities_table = Table(title="Discovered Entities", show_header=True, header_style="bold magenta")
    entities_table.add_column("Entity", style="cyan", no_wrap=True)
    entities_table.add_column("Records", justify="right", style="green")
    entities_table.add_column("Fields", justify="right", style="yellow")
    entities_table.add_column("Primary Key", style="blue")
    entities_table.add_column("Foreign Keys", style="magenta")
    
    for entity in scan_result.entities:
        entities_table.add_row(
            entity.entity_name,
            str(entity.record_count),
            str(len(entity.fields)),
            entity.potential_primary_key or "-",
            ", ".join(entity.potential_foreign_keys[:3]) or "-",
        )
    
    console.print(entities_table)
    console.print()
    
    # Step 2: AI Analysis
    console.print("[bold]Step 2: AI ERD Analysis[/bold]")
    console.print("[cyan]Analyzing relationships and recommending XDM structure...[/cyan]")
    
    config = get_config()
    engine = AIInferenceEngine(config)
    
    with console.status("[bold blue]Running AI inference (this may take 30-60 seconds)..."):
        try:
            analysis = asyncio.run(engine.analyze_dataset_relationships(scan_result))
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected error during AI analysis: {e}[/red]")
            raise typer.Exit(1)
    
    console.print(f"[green]✓[/green] Analysis complete\n")
    
    # Step 3: Display Results
    if format_type == "json":
        # JSON output
        output_data = analysis.model_dump()
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            console.print(f"[green]Analysis saved to {output}[/green]")
        else:
            console.print(json.dumps(output_data, indent=2))
    
    elif format_type == "mermaid":
        # Mermaid ERD output
        mermaid_code = _generate_mermaid_erd(analysis)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(mermaid_code)
            console.print(f"[green]Mermaid ERD saved to {output}[/green]")
        else:
            console.print("\n[bold]Mermaid ERD Diagram:[/bold]")
            console.print(Syntax(mermaid_code, "mermaid", theme="monokai"))
    
    else:
        # Rich visual output (default)
        _display_analysis_rich(analysis, scan_result)
        
        # Save JSON if output specified
        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(analysis.model_dump(), f, indent=2)
            console.print(f"\n[green]Analysis also saved to {output}[/green]")


def _display_analysis_rich(analysis, scan_result) -> None:
    """Display analysis results with Rich formatting."""
    from rich.tree import Tree
    
    console.print("[bold]Step 3: Analysis Results[/bold]\n")
    
    # Relationships
    if analysis.relationships:
        console.print(Panel(
            "[bold cyan]Detected Relationships[/bold cyan]",
            border_style="cyan"
        ))
        
        rel_table = Table(show_header=True, header_style="bold magenta")
        rel_table.add_column("Source", style="cyan")
        rel_table.add_column("Field", style="blue")
        rel_table.add_column("→", style="yellow")
        rel_table.add_column("Target", style="cyan")
        rel_table.add_column("Field", style="blue")
        rel_table.add_column("Type", style="green")
        rel_table.add_column("Confidence", justify="right", style="yellow")
        
        for rel in analysis.relationships:
            rel_table.add_row(
                rel.source_entity,
                rel.source_field,
                "→",
                rel.target_entity,
                rel.target_field,
                rel.relationship_type.value,
                f"{rel.confidence:.0%}",
            )
        
        console.print(rel_table)
        console.print()
    
    # XDM Class Recommendations
    if analysis.xdm_class_recommendations:
        console.print(Panel(
            "[bold cyan]XDM Class Recommendations[/bold cyan]",
            border_style="cyan"
        ))
        
        for rec in analysis.xdm_class_recommendations:
            console.print(f"[bold]{rec.entity_name}[/bold]")
            console.print(f"  → [green]{rec.recommended_class}[/green] ({rec.confidence:.0%} confidence)")
            console.print(f"  [dim]{rec.reasoning}[/dim]")
            if rec.alternative_classes:
                console.print(f"  [dim]Alternatives: {', '.join(rec.alternative_classes)}[/dim]")
            console.print()
    
    # Identity Strategies
    if analysis.identity_strategies:
        console.print(Panel(
            "[bold cyan]Identity Configuration Strategy[/bold cyan]",
            border_style="cyan"
        ))
        
        for strat in analysis.identity_strategies:
            console.print(f"[bold]{strat.entity_name}[/bold]")
            console.print(f"  Primary: [green]{strat.primary_identity_field}[/green] ({strat.identity_namespace})")
            if strat.additional_identity_fields:
                console.print(f"  Additional: [cyan]{', '.join(strat.additional_identity_fields)}[/cyan]")
            console.print(f"  [dim]{strat.reasoning}[/dim]")
            console.print()
    
    # Field Group Suggestions
    if analysis.field_group_suggestions:
        console.print(Panel(
            "[bold cyan]Recommended Field Groups[/bold cyan]",
            border_style="cyan"
        ))
        
        for entity, groups in analysis.field_group_suggestions.items():
            console.print(f"[bold]{entity}:[/bold] {', '.join(groups)}")
        console.print()
    
    # Implementation Strategy
    console.print(Panel(
        f"[bold cyan]Implementation Strategy[/bold cyan]\n\n{analysis.implementation_strategy}",
        border_style="green"
    ))
    
    # AI Reasoning
    console.print(Panel(
        f"[bold cyan]AI Analysis Summary[/bold cyan]\n\n{analysis.ai_reasoning}",
        border_style="blue"
    ))


def _generate_mermaid_erd(analysis) -> str:
    """Generate Mermaid ERD diagram code."""
    lines = ["erDiagram"]
    
    # Add entities
    for entity in analysis.entities:
        lines.append(f"    {entity.upper()} {{")
        # We don't have field details here, just add placeholder
        lines.append("        string fields")
        lines.append("    }")
    
    # Add relationships
    for rel in analysis.relationships:
        source = rel.source_entity.upper()
        target = rel.target_entity.upper()
        
        # Convert relationship type to Mermaid syntax
        if rel.relationship_type.value == "1:1":
            marker = "||--||"
        elif rel.relationship_type.value == "1:N":
            marker = "||--o{"
        elif rel.relationship_type.value == "N:M":
            marker = "}o--o{"
        else:
            marker = "..--"
        
        lines.append(f"    {source} {marker} {target} : \"{rel.source_field}\"")
    
    return "\n".join(lines)


__all__ = ["schema_app"]
