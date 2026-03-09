"""Segment and audience management commands."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from adobe_experience.aep.client import AEPClient
from adobe_experience.cache.segment_cache import SegmentCache
from adobe_experience.cli._id_resolver import resolve_segment_id_or_fail
from adobe_experience.destination.client import DestinationServiceClient
from adobe_experience.segmentation.client import SegmentationServiceClient
from adobe_experience.segmentation.models import SegmentJobStatus, SegmentStatus
from adobe_experience.cli.command_metadata import (
    command_metadata,
    CommandCategory,
    register_command_group_metadata,
)
from adobe_experience.core.config import get_config

console = Console()
segment_app = typer.Typer(help="Segment and audience management commands")

# Register command group metadata
register_command_group_metadata("segment", CommandCategory.API, "Segment and audience API operations")


@command_metadata(CommandCategory.API, "List segment definitions")
@segment_app.command("list")
def list_segments(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of segments to display"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status (DRAFT, ACTIVE, INACTIVE)"),
    full_id: bool = typer.Option(False, "--full-id", help="Display full UUIDs instead of truncated IDs"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List segment definitions from Adobe Experience Platform.

    Displays all segment definitions with their names, status, and PQL expressions.
    Segment numbers can be used with other commands (e.g., 'aep segment get 1').

    Examples:
        aep segment list
        aep segment list --limit 50
        aep segment list --status ACTIVE
        aep segment list --full-id
        aep segment list --json
    """

    async def fetch_segments():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            status_filter = SegmentStatus(status) if status else None
            return await segment_client.list_segments(limit=limit, status=status_filter)

    try:
        with console.status("[bold blue]Fetching segments..."):
            segments = asyncio.run(fetch_segments())

        if not segments:
            console.print("[yellow]No segments found[/yellow]")
            return
        
        # Save to cache for number-based access
        cache = SegmentCache()
        id_mappings = {idx: seg.id for idx, seg in enumerate(segments, 1)}
        cache.save_mappings(id_mappings)

        if json_output:
            output = [
                {
                    "id": seg.id,
                    "name": seg.name,
                    "status": seg.status.value,
                    "description": seg.description,
                    "pql": seg.expression.value,
                    "created": seg.created,
                    "updated": seg.updated,
                }
                for seg in segments
            ]
            console.print(json.dumps(output, indent=2))
            return

        table = Table(title=f"Segment Definitions ({len(segments)} found)")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan", no_wrap=False)
        table.add_column("Status", justify="center")
        table.add_column("PQL Expression", style="dim", no_wrap=False)
        table.add_column("ID", style="dim")

        for idx, seg in enumerate(segments, 1):
            # Color status
            if seg.status == SegmentStatus.ACTIVE:
                status_str = f"[green]{seg.status.value}[/green]"
            elif seg.status == SegmentStatus.DRAFT:
                status_str = f"[yellow]{seg.status.value}[/yellow]"
            else:
                status_str = f"[red]{seg.status.value}[/red]"

            # Truncate PQL for display
            pql = seg.expression.value
            pql_display = (pql[:80] + "...") if len(pql) > 80 else pql

            # Display ID (full or truncated)
            seg_id = seg.id or "N/A"
            if full_id:
                id_display = seg_id
            else:
                id_display = (seg_id[:16] + "...") if len(seg_id) > 16 else seg_id

            table.add_row(
                str(idx),
                seg.name,
                status_str,
                pql_display,
                id_display,
            )

        console.print(table)
        
        # Add helpful tips
        console.print(f"\n[dim]💡 Tip: Use 'aep segment get <# or ID>' to see full details[/dim]")
        console.print(f"[dim]💡 Tip: Use number shortcuts (e.g., 'aep segment evaluate 1')[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Get segment definition details")
@segment_app.command("get")
def get_segment(
    segment_id: str = typer.Argument(..., help="Segment ID or number from list command"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get detailed information about a segment definition.

    Examples:
        aep segment get 1
        aep segment get abc123...
        aep segment get abc123... --json
    """
    
    # Resolve segment ID (number or UUID)
    try:
        resolved_id = resolve_segment_id_or_fail(segment_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    async def fetch_segment():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            return await segment_client.get_segment(resolved_id)

    try:
        with console.status(f"[bold blue]Fetching segment {segment_id}..."):
            segment = asyncio.run(fetch_segment())

        if json_output:
            console.print(segment.model_dump_json(indent=2))
            return

        # Display as formatted panel
        info_lines = [
            f"[cyan]Name:[/cyan] {segment.name}",
            f"[cyan]ID:[/cyan] {segment.id}",
            f"[cyan]Status:[/cyan] {segment.status.value}",
            f"[cyan]Schema:[/cyan] {segment.schema.get('name', 'N/A')}",
        ]

        if segment.description:
            info_lines.append(f"[cyan]Description:[/cyan] {segment.description}")

        if segment.ttlInDays:
            info_lines.append(f"[cyan]TTL:[/cyan] {segment.ttlInDays} days")

        if segment.created_at:
            info_lines.append(f"[cyan]Created:[/cyan] {segment.created_at}")

        if segment.updated_at:
            info_lines.append(f"[cyan]Updated:[/cyan] {segment.updated_at}")

        console.print(Panel("\n".join(info_lines), title="Segment Details", border_style="blue"))

        # PQL Expression
        console.print("\n[bold]PQL Expression:[/bold]")
        console.print(Panel(segment.expression.value, border_style="green"))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Create a new segment definition")
@segment_app.command("create")
def create_segment(
    name: str = typer.Option(..., "--name", "-n", help="Segment name"),
    pql: str = typer.Option(..., "--pql", "-q", help="PQL query expression"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Segment description"),
    ttl: Optional[int] = typer.Option(None, "--ttl", help="Time to live in days"),
    schema: str = typer.Option("_xdm.context.profile", "--schema", help="Schema name"),
) -> None:
    """Create a new segment definition with PQL expression.

    The PQL (Profile Query Language) expression defines the criteria for segment membership.

    Examples:
        aep segment create -n "High Value" -q "person.totalSpent > 1000"
        aep segment create -n "Recent Buyers" -q 'person.lastPurchase > now() - duration("P7D")' -d "Last 7 days"
        aep segment create -n "Young Adults" -q "person.age >= 18 AND person.age <= 35" --ttl 30
    """

    async def create():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            return await segment_client.create_segment(
                name=name,
                pql_expression=pql,
                schema_name=schema,
                description=description,
                ttl_in_days=ttl,
            )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Creating segment..."),
            console=console,
        ) as progress:
            progress.add_task("create", total=None)
            segment_id = asyncio.run(create())

        console.print(f"\n[green]✓[/green] Segment created successfully!")
        console.print(f"[cyan]Segment ID:[/cyan] {segment_id}")
        console.print(f"\nView details: [yellow]aep segment get {segment_id}[/yellow]")
        console.print(f"Evaluate: [yellow]aep segment evaluate {segment_id}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Update a segment definition")
@segment_app.command("update")
def update_segment(
    segment_id: str = typer.Argument(..., help="Segment ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New segment name"),
    pql: Optional[str] = typer.Option(None, "--pql", "-q", help="New PQL expression"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    status: Optional[str] = typer.Option(None, "--status", help="New status (ACTIVE, INACTIVE)"),
) -> None:
    """Update an existing segment definition.

    Examples:
        aep segment update abc123... --status ACTIVE
        aep segment update abc123... --name "New Name" --description "Updated"
        aep segment update abc123... --pql "person.totalSpent > 2000"
    """

    async def update():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            status_enum = SegmentStatus(status) if status else None
            return await segment_client.update_segment(
                segment_id=segment_id,
                name=name,
                pql_expression=pql,
                description=description,
                status=status_enum,
            )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Updating segment..."),
            console=console,
        ) as progress:
            progress.add_task("update", total=None)
            updated = asyncio.run(update())

        console.print(f"\n[green]✓[/green] Segment updated successfully!")
        console.print(f"[cyan]Name:[/cyan] {updated.name}")
        console.print(f"[cyan]Status:[/cyan] {updated.status.value}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Delete a segment definition")
@segment_app.command("delete")
def delete_segment(
    segment_id: str = typer.Argument(..., help="Segment ID or number from list command"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a segment definition.

    This action cannot be undone. The segment will be permanently removed.

    Examples:
        aep segment delete 1
        aep segment delete abc123...
        aep segment delete abc123... --yes
    """
    
    # Resolve segment ID (number or UUID)
    try:
        resolved_id = resolve_segment_id_or_fail(segment_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if not confirm:
        confirmed = typer.confirm(
            f"Are you sure you want to delete segment {segment_id}?",
            default=False,
        )
        if not confirmed:
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    async def delete():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            await segment_client.delete_segment(resolved_id)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold red]Deleting segment..."),
            console=console,
        ) as progress:
            progress.add_task("delete", total=None)
            asyncio.run(delete())

        console.print(f"\n[green]✓[/green] Segment deleted successfully")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Trigger segment evaluation")
@segment_app.command("evaluate")
def evaluate_segment(
    segment_id: str = typer.Argument(..., help="Segment ID or number from list command"),
    wait: bool = typer.Option(False, "--wait", help="Wait for evaluation to complete"),
    max_wait: int = typer.Option(300, "--max-wait", help="Maximum seconds to wait"),
) -> None:
    """Trigger on-demand segment evaluation.

    Creates a segment job that evaluates the segment criteria against all
    profiles in the platform.

    Examples:
        aep segment evaluate 1
        aep segment evaluate abc123...
        aep segment evaluate abc123... --wait
    """
    
    # Resolve segment ID (number or UUID)
    try:
        resolved_id = resolve_segment_id_or_fail(segment_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    async def evaluate():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            job_id = await segment_client.evaluate_segment(resolved_id)

            if wait:
                console.print(f"[cyan]Waiting for evaluation to complete...[/cyan]")
                job = await segment_client.wait_for_job_completion(
                    job_id, max_wait=float(max_wait)
                )
                return job_id, job
            else:
                return job_id, None

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Starting evaluation..."),
            console=console,
        ) as progress:
            progress.add_task("evaluate", total=None)
            job_id, job = asyncio.run(evaluate())

        console.print(f"\n[green]✓[/green] Evaluation job created!")
        console.print(f"[cyan]Job ID:[/cyan] {job_id}")

        if job:
            console.print(f"[cyan]Status:[/cyan] {job.status.value}")
            if job.metrics and job.metrics.segmentedProfileCounter:
                console.print(f"[cyan]Profiles:[/cyan] {job.metrics.segmentedProfileCounter}")
        else:
            console.print(f"\nCheck status: [yellow]aep segment job {job_id}[/yellow]")

    except TimeoutError as e:
        console.print(f"[yellow]Warning: {e}[/yellow]")
        console.print(f"Job is still running. Check status manually.")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Get segment job status")
@segment_app.command("job")
def get_segment_job(
    job_id: str = typer.Argument(..., help="Segment job ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get segment evaluation job status and metrics.

    Examples:
        aep segment job job123...
        aep segment job job123... --json
    """

    async def fetch_job():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            return await segment_client.get_segment_job(job_id)

    try:
        with console.status(f"[bold blue]Fetching job {job_id}..."):
            job = asyncio.run(fetch_job())

        if json_output:
            console.print(job.model_dump_json(indent=2))
            return

        # Display job details
        info_lines = [
            f"[cyan]Job ID:[/cyan] {job.id}",
            f"[cyan]Status:[/cyan] {job.status.value}",
        ]

        if job.segments:
            info_lines.append(f"[cyan]Segments:[/cyan] {len(job.segments)}")

        if job.created_at:
            info_lines.append(f"[cyan]Created:[/cyan] {job.created_at}")

        if job.updated_at:
            info_lines.append(f"[cyan]Updated:[/cyan] {job.updated_at}")

        console.print(Panel("\n".join(info_lines), title="Segment Job", border_style="blue"))

        # Metrics
        if job.metrics:
            console.print("\n[bold]Metrics:[/bold]")
            metrics_lines = []

            if job.metrics.totalTime:
                metrics_lines.append(f"[cyan]Total Time:[/cyan] {job.metrics.totalTime}ms")

            if job.metrics.segmentedProfileCounter:
                metrics_lines.append(
                    f"[cyan]Profiles:[/cyan] {job.metrics.segmentedProfileCounter}"
                )

            if metrics_lines:
                console.print(Panel("\n".join(metrics_lines), border_style="green"))

        # Errors
        if job.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for error in job.errors[:5]:  # Show first 5 errors
                console.print(f"  • {error}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Estimate segment size")
@segment_app.command("estimate")
def estimate_segment(
    pql: str = typer.Option(..., "--pql", "-q", help="PQL query expression"),
    schema: str = typer.Option("_xdm.context.profile", "--schema", help="Schema name"),
) -> None:
    """Estimate segment size without full evaluation.

    Provides a quick estimate of how many profiles match the criteria.

    Examples:
        aep segment estimate --pql "person.age > 25"
        aep segment estimate -q "person.totalSpent > 1000"
    """

    async def estimate():
        async with AEPClient(get_config()) as aep_client:
            segment_client = SegmentationServiceClient(aep_client)
            return await segment_client.estimate_segment_size(
                pql_expression=pql, schema_name=schema
            )

    try:
        with console.status("[bold blue]Estimating segment size..."):
            estimate = asyncio.run(estimate())

        console.print(f"\n[green]✓[/green] Estimate completed!")
        console.print(f"[cyan]Estimated Size:[/cyan] {estimate.estimatedSize:,} profiles")

        if estimate.confidenceInterval:
            console.print(f"[cyan]Confidence:[/cyan] {estimate.confidenceInterval}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "List segment activations to destinations")
@segment_app.command("destinations")
def list_segment_destinations(
    segment_id: str = typer.Argument(..., help="Segment ID or number from list"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all destinations where a segment is activated.

    Shows which destinations are receiving this segment's data,
    along with activation status, schedule, and mappings.

    Examples:
        aep segment destinations <segment-id>
        aep segment destinations 1        # Using number from list
        aep segment destinations <id> --json
    """

    async def list_activations():
        # Resolve segment ID (supports number shortcuts)
        try:
            resolved_id = resolve_segment_id_or_fail(segment_id)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        async with AEPClient(get_config()) as aep_client:
            dest_client = DestinationServiceClient(aep_client)
            return await dest_client.list_segment_activations(resolved_id)

    try:
        with console.status(f"[bold blue]Fetching activations for segment {segment_id}..."):
            activations = asyncio.run(list_activations())

        if json_output:
            print(json.dumps([a.model_dump(mode="json") for a in activations], indent=2))
            return

        if not activations:
            console.print(f"\n[yellow]No activations found for segment {segment_id}[/yellow]")
            console.print("\n[dim]Use 'aep segment activate' to activate this segment to a destination.[/dim]")
            return

        # Display activations table
        table = Table(title=f"Activations for Segment {segment_id}")
        table.add_column("#", style="dim", width=4)
        table.add_column("Destination", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Dataflow ID", style="blue")
        table.add_column("Schedule", style="green")

        for idx, activation in enumerate(activations, 1):
            status_color = "green" if activation.status == "ACTIVE" else "yellow"
            schedule_str = activation.schedule.get("frequency", "N/A") if activation.schedule else "N/A"
            
            table.add_row(
                str(idx),
                activation.destination_id[:8] + "..." if len(activation.destination_id) > 8 else activation.destination_id,
                f"[{status_color}]{activation.status}[/{status_color}]",
                activation.dataflow_id[:8] + "..." if activation.dataflow_id and len(activation.dataflow_id) > 8 else (activation.dataflow_id or "N/A"),
                schedule_str,
            )

        console.print(table)
        console.print(f"\n[green]✓[/green] Found {len(activations)} activation(s)")

    except NotImplementedError as e:
        console.print(f"\n[yellow]⚠ Feature not yet implemented[/yellow]")
        console.print(f"[dim]{str(e)}[/dim]")
        console.print("\n[cyan]TODO:[/cyan] Verify Adobe Destination API endpoints and implement client methods.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Activate segment to destination")
@segment_app.command("activate")
def activate_segment_to_destination(
    segment_id: str = typer.Argument(..., help="Segment ID or number from list"),
    destination_id: str = typer.Argument(..., help="Destination instance ID"),
    schedule_frequency: Optional[str] = typer.Option(None, "--schedule", help="Schedule frequency (daily, hourly)"),
    mapping_file: Optional[str] = typer.Option(None, "--mappings", help="Path to JSON file with field mappings"),
) -> None:
    """Activate a segment to a destination.

    Creates an activation dataflow that exports segment membership data
    to the specified destination instance.

    Examples:
        aep segment activate <segment-id> <destination-id>
        aep segment activate 1 <destination-id>  # Using number
        aep segment activate <id> <dest> --schedule daily
        aep segment activate <id> <dest> --mappings mappings.json
    """

    async def activate():
        # Resolve segment ID (supports number shortcuts)
        try:
            resolved_segment_id = resolve_segment_id_or_fail(segment_id)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        # Load mapping config if provided
        mapping_config = None
        if mapping_file:
            try:
                with open(mapping_file) as f:
                    mapping_config = json.load(f)
            except Exception as e:
                console.print(f"[red]Error loading mapping file: {e}[/red]")
                raise typer.Exit(1)

        # Build schedule config
        schedule = None
        if schedule_frequency:
            schedule = {"frequency": schedule_frequency}

        async with AEPClient(get_config()) as aep_client:
            dest_client = DestinationServiceClient(aep_client)
            return await dest_client.activate_segment(
                segment_id=resolved_segment_id,
                destination_id=destination_id,
                mapping_config=mapping_config,
                schedule=schedule,
            )

    try:
        with console.status(f"[bold blue]Activating segment {segment_id} to destination..."):
            activation_id = asyncio.run(activate())

        console.print(f"\n[green]✓[/green] Segment activated successfully!")
        console.print(f"[cyan]Activation ID:[/cyan] {activation_id}")
        console.print(f"\n[dim]Use 'aep segment destinations {segment_id}' to view activation status.[/dim]")

    except NotImplementedError as e:
        console.print(f"\n[yellow]⚠ Feature not yet implemented[/yellow]")
        console.print(f"[dim]{str(e)}[/dim]")
        console.print("\n[cyan]TODO:[/cyan] Verify Adobe Destination API endpoints and implement client methods.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Deactivate segment from destination")
@segment_app.command("deactivate")
def deactivate_segment_from_destination(
    segment_id: str = typer.Argument(..., help="Segment ID or number from list"),
    destination_id: str = typer.Argument(..., help="Destination instance ID"),
) -> None:
    """Deactivate a segment from a destination.

    Stops exporting segment membership data to the specified destination.

    Examples:
        aep segment deactivate <segment-id> <destination-id>
        aep segment deactivate 1 <destination-id>  # Using number
    """

    async def deactivate():
        # Resolve segment ID (supports number shortcuts)
        try:
            resolved_segment_id = resolve_segment_id_or_fail(segment_id)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        async with AEPClient(get_config()) as aep_client:
            dest_client = DestinationServiceClient(aep_client)
            await dest_client.deactivate_segment(
                segment_id=resolved_segment_id,
                destination_id=destination_id,
            )

    try:
        with console.status(f"[bold blue]Deactivating segment {segment_id} from destination..."):
            asyncio.run(deactivate())

        console.print(f"\n[green]✓[/green] Segment deactivated successfully!")
        console.print(f"\n[dim]Segment {segment_id} is no longer sending data to destination {destination_id}.[/dim]")

    except NotImplementedError as e:
        console.print(f"\n[yellow]⚠ Feature not yet implemented[/yellow]")
        console.print(f"[dim]{str(e)}[/dim]")
        console.print("\n[cyan]TODO:[/cyan] Verify Adobe Destination API endpoints and implement client methods.")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
