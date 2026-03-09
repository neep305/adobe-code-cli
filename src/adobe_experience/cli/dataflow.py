"""Dataflow management commands."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from adobe_experience.aep.client import AEPClient
from adobe_experience.cache.dataflow_cache import DataflowCache
from adobe_experience.cli._id_resolver import resolve_dataflow_id_or_fail
from adobe_experience.cli.command_metadata import (
    command_metadata,
    CommandCategory,
    register_command_group_metadata,
)
from adobe_experience.core.config import get_config
from adobe_experience.flow.client import FlowServiceClient
from adobe_experience.flow.models import DataflowState, RunStatus
from adobe_experience.flow.source_parser import (
    extract_source_entity,
    extract_source_summary,
    format_source_params,
)

console = Console()
dataflow_app = typer.Typer(help="Dataflow management and monitoring commands")

# Register command group metadata
register_command_group_metadata("dataflow", CommandCategory.API, "Flow Service API operations")


@command_metadata(CommandCategory.API, "List dataflows from Flow Service")
@dataflow_app.command("list")
def list_dataflows(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of dataflows to display"),
    state: Optional[str] = typer.Option(None, "--state", help="Filter by state (enabled/disabled)"),
    with_sources: bool = typer.Option(False, "--with-sources", help="Include source entity information (slower)"),
    full_id: bool = typer.Option(False, "--full-id", help="Display full UUIDs instead of truncated IDs"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List dataflows in Adobe Experience Platform.

    Examples:
        aep dataflow list
        aep dataflow list --limit 50
        aep dataflow list --state enabled
        aep dataflow list --with-sources
        aep dataflow list --full-id
        aep dataflow list --json
    """

    async def fetch_dataflows():
        async with AEPClient(get_config()) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            property_filter = None
            if state:
                state_value = state.lower()
                if state_value in ["enabled", "disabled"]:
                    property_filter = f"state=={state_value}"
            return await flow_client.list_dataflows(limit=limit, property_filter=property_filter)

    try:
        with console.status("[bold blue]Fetching dataflows..."):
            dataflows = asyncio.run(fetch_dataflows())

        if not dataflows:
            console.print("[yellow]No dataflows found[/yellow]")
            return

        if json_output:
            # Output as JSON
            data = [flow.model_dump(by_alias=True) for flow in dataflows]
            console.print_json(data=data)
            return

        # Cache ID mappings for number-based selection
        cache = DataflowCache()
        id_mappings = {idx: flow.id for idx, flow in enumerate(dataflows, 1)}
        cache.save_mappings(id_mappings)

        # Rich table output
        table = Table(title=f"Dataflows ({len(dataflows)} found)")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan", no_wrap=False, max_width=40)
        table.add_column("ID", style="dim", max_width=40 if full_id else 30)
        table.add_column("State", justify="center")
        if with_sources:
            table.add_column("Source", style="green", max_width=35)
        table.add_column("Flow Spec", style="green", max_width=30)
        table.add_column("Created", style="blue")

        for idx, flow in enumerate(dataflows, 1):
            # Format state with color
            state_text = (
                f"[green]{flow.state.value}[/green]"
                if flow.state == DataflowState.ENABLED
                else f"[yellow]{flow.state.value}[/yellow]"
            )

            # Format creation date
            created_date = datetime.fromtimestamp(flow.created_at / 1000).strftime("%Y-%m-%d %H:%M")

            # Format IDs based on --full-id flag
            if full_id:
                flow_id_display = flow.id
                spec_display = flow.flow_spec.id
            else:
                flow_id_display = flow.id[:24] + "..." if len(flow.id) > 24 else flow.id
                spec_display = (
                    flow.flow_spec.id[:24] + "..." if len(flow.flow_spec.id) > 24 else flow.flow_spec.id
                )
            
            # Fetch source info if requested
            source_display = ""
            if with_sources:
                try:
                    async def get_source():
                        async with AEPClient(get_config()) as aep:
                            fc = FlowServiceClient(aep)
                            conns = await fc.get_dataflow_connections(flow.id)
                            if conns["source_connections"]:
                                return extract_source_summary(conns["source_connections"][0])
                            return "N/A"
                    source_display = asyncio.run(get_source())
                except:
                    source_display = "Error"

            row = [
                str(idx),
                flow.name or "N/A",
                flow_id_display,
                state_text,
            ]
            if with_sources:
                row.append(source_display)
            row.extend([spec_display, created_date])
            
            table.add_row(*row)

        console.print(table)
        console.print(
            f"\n[dim]Tip: Use 'aep dataflow get <ID or #>' for detailed information[/dim]"
        )
        console.print(
            f"[dim]Tip: Use number shortcuts (e.g., 'aep dataflow failures 1') instead of full IDs[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Get dataflow details by ID")
@dataflow_app.command("get")
def get_dataflow(
    flow_id: str = typer.Argument(..., help="Dataflow ID or number from list"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get detailed information about a specific dataflow.

    Examples:
        aep dataflow get 1  # Use number from list
        aep dataflow get d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a
        aep dataflow get <FLOW_ID> --json
    """
    
    # Resolve ID from number or UUID
    try:
        resolved_id = resolve_dataflow_id_or_fail(flow_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    async def fetch_dataflow():
        async with AEPClient(get_config()) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            return await flow_client.get_dataflow(resolved_id)

    try:
        with console.status(f"[bold blue]Fetching dataflow {flow_id}..."):
            flow = asyncio.run(fetch_dataflow())

        if json_output:
            console.print_json(data=flow.model_dump(by_alias=True))
            return

        # Rich formatted output
        panel_content = []

        # Basic info
        panel_content.append(f"[bold]Name:[/bold] {flow.name}")
        panel_content.append(f"[bold]ID:[/bold] {flow.id}")
        panel_content.append(
            f"[bold]State:[/bold] [green]{flow.state.value}[/green]"
            if flow.state == DataflowState.ENABLED
            else f"[bold]State:[/bold] [yellow]{flow.state.value}[/yellow]"
        )

        if flow.description:
            panel_content.append(f"[bold]Description:[/bold] {flow.description}")

        # Timestamps
        created = datetime.fromtimestamp(flow.created_at / 1000).strftime("%Y-%m-%d %H:%M:%S")
        updated = datetime.fromtimestamp(flow.updated_at / 1000).strftime("%Y-%m-%d %H:%M:%S")
        panel_content.append(f"[bold]Created:[/bold] {created}")
        panel_content.append(f"[bold]Updated:[/bold] {updated}")

        # Flow spec
        panel_content.append(f"\n[bold cyan]Flow Specification[/bold cyan]")
        panel_content.append(f"  ID: {flow.flow_spec.id}")
        if flow.flow_spec.version:
            panel_content.append(f"  Version: {flow.flow_spec.version}")

        # Connections with source entity info
        panel_content.append(f"\n[bold cyan]Connections[/bold cyan]")
        panel_content.append(f"  Source Connection IDs: {len(flow.source_connection_ids)}")
        
        # Try to fetch and display source entities
        try:
            async def get_sources():
                async with AEPClient(get_config()) as aep:
                    fc = FlowServiceClient(aep)
                    return await fc.get_dataflow_connections(flow_id)
            
            conn_details = asyncio.run(get_sources())
            for idx, src_conn in enumerate(conn_details["source_connections"], 1):
                entity = extract_source_entity(src_conn)
                if entity:
                    panel_content.append(f"    {idx}. {src_conn.id}")
                    panel_content.append(f"       [green]→ {entity}[/green]")
                else:
                    panel_content.append(f"    {idx}. {src_conn.id}")
        except:
            # Fallback to just showing IDs
            for idx, conn_id in enumerate(flow.source_connection_ids, 1):
                panel_content.append(f"    {idx}. {conn_id}")

        panel_content.append(f"  Target Connection IDs: {len(flow.target_connection_ids)}")
        for idx, conn_id in enumerate(flow.target_connection_ids, 1):
            panel_content.append(f"    {idx}. {conn_id}")

        # Schedule
        if flow.schedule_params:
            panel_content.append(f"\n[bold cyan]Schedule[/bold cyan]")
            if flow.schedule_params.frequency:
                panel_content.append(f"  Frequency: {flow.schedule_params.frequency}")
            if flow.schedule_params.interval:
                panel_content.append(f"  Interval: {flow.schedule_params.interval}")
            if flow.schedule_params.start_time:
                start_time = datetime.fromtimestamp(flow.schedule_params.start_time).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                panel_content.append(f"  Start Time: {start_time}")

        # Inherited attributes (from detailed response)
        if flow.inherited_attributes:
            if flow.inherited_attributes.source_connections:
                panel_content.append(f"\n[bold cyan]Source Connection Details[/bold cyan]")
                for src in flow.inherited_attributes.source_connections:
                    spec_name = src.connection_spec.name if src.connection_spec else "Unknown"
                    panel_content.append(f"  {src.id}: {spec_name}")

            if flow.inherited_attributes.target_connections:
                panel_content.append(f"\n[bold cyan]Target Connection Details[/bold cyan]")
                for tgt in flow.inherited_attributes.target_connections:
                    spec_name = tgt.connection_spec.name if tgt.connection_spec else "Unknown"
                    panel_content.append(f"  {tgt.id}: {spec_name}")

        panel = Panel(
            "\n".join(panel_content),
            title=f"[bold]Dataflow: {flow.name}[/bold]",
            border_style="blue",
        )
        console.print(panel)

        console.print(
            f"\n[dim]Tip: Use 'aep dataflow runs {flow_id}' to see execution history[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "List dataflow runs and executions")
@dataflow_app.command("runs")
def list_runs(
    flow_id: str = typer.Argument(..., help="Dataflow ID or number from list"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of runs to display"),
    days: Optional[int] = typer.Option(None, "--days", help="Filter runs from last N days"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List execution runs for a dataflow.

    Examples:
        aep dataflow runs 1  # Use number from list
        aep dataflow runs d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a
        aep dataflow runs <FLOW_ID> --limit 50
        aep dataflow runs <FLOW_ID> --days 7
        aep dataflow runs <FLOW_ID> --json
    """
    
    # Resolve ID from number or UUID
    try:
        resolved_id = resolve_dataflow_id_or_fail(flow_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    async def fetch_runs():
        async with AEPClient(get_config()) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            if days:
                start_date = datetime.now() - timedelta(days=days)
                return await flow_client.list_runs_by_date_range(
                    resolved_id, start_date=start_date, limit=limit
                )
            else:
                return await flow_client.list_runs(resolved_id, limit=limit)

    try:
        with console.status(f"[bold blue]Fetching runs for dataflow {flow_id}..."):
            runs = asyncio.run(fetch_runs())

        if not runs:
            console.print("[yellow]No runs found for this dataflow[/yellow]")
            return

        if json_output:
            data = [run.model_dump(by_alias=True) for run in runs]
            console.print_json(data=data)
            return

        # Rich table output
        table = Table(title=f"Dataflow Runs ({len(runs)} found)")
        table.add_column("Run ID", style="cyan", max_width=30)
        table.add_column("Status", justify="center")
        table.add_column("Created", style="blue")
        table.add_column("Records Read", justify="right")
        table.add_column("Records Written", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Error", style="red", max_width=40)

        for run in runs:
            # Format status with color
            status_value = run.status or "unknown"
            if status_value == "success":
                status_display = f"[green]{status_value}[/green]"
            elif status_value == "failed":
                status_display = f"[red]{status_value}[/red]"
            elif status_value in ["pending", "inProgress"]:
                status_display = f"[yellow]{status_value}[/yellow]"
            else:
                status_display = status_value

            # Format creation date
            created = datetime.fromtimestamp(run.created_at / 1000).strftime("%Y-%m-%d %H:%M:%S")

            # Get metrics from record_summary
            records_read = "N/A"
            records_written = "N/A"
            if run.metrics and run.metrics.record_summary:
                rs = run.metrics.record_summary
                if rs.input_record_count is not None:
                    records_read = str(rs.input_record_count)
                if rs.output_record_count is not None:
                    records_written = str(rs.output_record_count)

            # Calculate duration
            duration_str = "N/A"
            if run.metrics and run.metrics.duration_summary:
                ds = run.metrics.duration_summary
                if ds.started_at_utc and ds.completed_at_utc:
                    duration_sec = (ds.completed_at_utc - ds.started_at_utc) / 1000.0
                    if duration_sec < 60:
                        duration_str = f"{duration_sec:.1f}s"
                    elif duration_sec < 3600:
                        duration_str = f"{duration_sec / 60:.1f}m"
                    else:
                        duration_str = f"{duration_sec / 3600:.1f}h"

            # Truncate run ID
            run_id_display = run.id[:24] + "..." if len(run.id) > 24 else run.id
            
            # Extract error info if failed
            error_display = ""
            if run.status == "failed":
                if hasattr(run, 'status_detail') and run.status_detail and run.status_detail.errors:
                    first_error = run.status_detail.errors[0]
                    error_msg = first_error.message[:35] if len(first_error.message) > 35 else first_error.message
                    error_display = f"{first_error.code}: {error_msg}"
                    if len(first_error.message) > 35:
                        error_display += "..."
                else:
                    error_display = "Failed (no details)"
            elif status_value == "success":
                error_display = "[green]✓[/green]"
            else:
                error_display = "-"

            table.add_row(
                run_id_display,
                status_display,
                created,
                records_read,
                records_written,
                duration_str,
                error_display,
            )

        console.print(table)
        console.print(
            f"\n[dim]Tip: Use 'aep dataflow failures {flow_id}' to see only failed runs[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "View dataflow run failures")
@dataflow_app.command("failures")
def list_failures(
    flow_id: str = typer.Argument(..., help="Dataflow ID or number from list"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of runs to check"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List only failed runs for a dataflow with error details.

    Examples:
        aep dataflow failures 1  # Use number from list
        aep dataflow failures d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a
        aep dataflow failures <FLOW_ID> --limit 100
        aep dataflow failures <FLOW_ID> --json
    """
    
    # Resolve ID from number or UUID
    try:
        resolved_id = resolve_dataflow_id_or_fail(flow_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    async def fetch_failures():
        async with AEPClient(get_config()) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            return await flow_client.list_failed_runs(resolved_id, limit=limit)

    try:
        with console.status(f"[bold blue]Fetching failed runs for dataflow {flow_id}..."):
            failed_runs = asyncio.run(fetch_failures())

        if not failed_runs:
            console.print("[green]No failed runs found! Dataflow is healthy.[/green]")
            return

        if json_output:
            data = [run.model_dump(by_alias=True) for run in failed_runs]
            console.print_json(data=data)
            return

        # Rich table output
        console.print(f"\n[red bold]Found {len(failed_runs)} failed runs[/red bold]\n")

        for idx, run in enumerate(failed_runs, 1):
            # Format creation date
            created = datetime.fromtimestamp(run.created_at / 1000).strftime("%Y-%m-%d %H:%M:%S")

            panel_content = []
            panel_content.append(f"[bold]Run ID:[/bold] {run.id}")
            panel_content.append(f"[bold]Created:[/bold] {created}")
            panel_content.append(f"[bold]Status:[/bold] [red]{run.status or 'failed'}[/red]")

            if run.metrics:
                panel_content.append(f"\n[bold cyan]Metrics[/bold cyan]")
                if run.metrics.record_summary:
                    rs = run.metrics.record_summary
                    if rs.input_record_count is not None:
                        panel_content.append(f"  Records Read: {rs.input_record_count}")
                    if rs.output_record_count is not None:
                        panel_content.append(f"  Records Written: {rs.output_record_count}")
                    if rs.failed_record_count is not None:
                        panel_content.append(f"  Records Failed: [red]{rs.failed_record_count}[/red]")

            # Display activity failures
            if run.activities:
                failed_activities = [a for a in run.activities if a.status_summary and a.status_summary.status == "failed"]
                if failed_activities:
                    panel_content.append(f"\n[bold red]Failed Activities ({len(failed_activities)})[/bold red]")
                    for activity in failed_activities:
                        panel_content.append(f"  [red]Activity:[/red] {activity.name or activity.id}")
                        if activity.status_summary:
                            panel_content.append(f"  [red]Status:[/red] {activity.status_summary.status}")
                        panel_content.append("")  # Empty line between activities

            panel = Panel(
                "\n".join(panel_content),
                title=f"[red bold]Failed Run #{idx}[/red bold]",
                border_style="red",
            )
            console.print(panel)

        console.print(
            f"\n[dim]Total failed runs: {len(failed_runs)}. Use --limit to check more runs.[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "List connections for dataflows")
@dataflow_app.command("connections")
def get_connections(
    flow_id: str = typer.Argument(..., help="Dataflow ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get connection details for a dataflow.

    Shows source and target connection information including
    connection types, parameters, and dataset IDs.

    Examples:
        aep dataflow connections d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a
        aep dataflow connections <FLOW_ID> --json
    """

    async def fetch_connections():
        async with AEPClient(get_config()) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            return await flow_client.get_dataflow_connections(flow_id)

    try:
        with console.status(f"[bold blue]Fetching connections for dataflow {flow_id}..."):
            details = asyncio.run(fetch_connections())

        if json_output:
            data = {
                "dataflow": details["dataflow"].model_dump(by_alias=True),
                "source_connections": [
                    conn.model_dump(by_alias=True) for conn in details["source_connections"]
                ],
                "target_connections": [
                    conn.model_dump(by_alias=True) for conn in details["target_connections"]
                ],
            }
            console.print_json(data=data)
            return

        # Rich formatted output
        dataflow = details["dataflow"]
        console.print(f"\n[bold cyan]Dataflow:[/bold cyan] {dataflow.name}\n")

        # Source connections
        if details["source_connections"]:
            console.print(f"[bold green]Source Connections ({len(details['source_connections'])})[/bold green]\n")
            for src in details["source_connections"]:
                panel_content = []
                panel_content.append(f"[bold]ID:[/bold] {src.id}")
                if src.name:
                    panel_content.append(f"[bold]Name:[/bold] {src.name}")

                spec_name = src.connection_spec.name if src.connection_spec.name else src.connection_spec.id
                panel_content.append(f"[bold]Type:[/bold] {spec_name}")
                
                # Extract and display source entity
                entity = extract_source_entity(src)
                if entity:
                    panel_content.append(f"[bold]Data Source:[/bold] [green]{entity}[/green]")

                if src.base_connection_id:
                    panel_content.append(f"[bold]Base Connection:[/bold] {src.base_connection_id}")

                if src.params:
                    panel_content.append(f"\n[bold cyan]Parameters:[/bold cyan]")
                    formatted_params = format_source_params(src.params)
                    panel_content.append(f"  {formatted_params}")
                    panel_content.append(f"\n[bold cyan]Raw Parameters:[/bold cyan]")
                    for key, value in src.params.items():
                        # Truncate long values
                        value_str = str(value)
                        if len(value_str) > 80:
                            value_str = value_str[:80] + "..."
                        panel_content.append(f"  {key}: {value_str}")

                panel = Panel(
                    "\n".join(panel_content),
                    title="Source Connection",
                    border_style="green",
                )
                console.print(panel)
        else:
            console.print("[yellow]No source connections found[/yellow]\n")

        # Target connections
        if details["target_connections"]:
            console.print(f"\n[bold blue]Target Connections ({len(details['target_connections'])})[/bold blue]\n")
            for tgt in details["target_connections"]:
                panel_content = []
                panel_content.append(f"[bold]ID:[/bold] {tgt.id}")
                if tgt.name:
                    panel_content.append(f"[bold]Name:[/bold] {tgt.name}")

                spec_name = tgt.connection_spec.name if tgt.connection_spec.name else tgt.connection_spec.id
                panel_content.append(f"[bold]Type:[/bold] {spec_name}")

                if tgt.base_connection_id:
                    panel_content.append(f"[bold]Base Connection:[/bold] {tgt.base_connection_id}")

                if tgt.params:
                    panel_content.append(f"\n[bold cyan]Parameters:[/bold cyan]")
                    for key, value in tgt.params.items():
                        # Highlight dataset ID
                        value_str = str(value)
                        if key == "dataSetId":
                            panel_content.append(f"  [bold]{key}:[/bold] [green]{value_str}[/green]")
                        else:
                            if len(value_str) > 80:
                                value_str = value_str[:80] + "..."
                            panel_content.append(f"  {key}: {value_str}")

                panel = Panel(
                    "\n".join(panel_content),
                    title="Target Connection",
                    border_style="blue",
                )
                console.print(panel)
        else:
            console.print("[yellow]No target connections found[/yellow]\n")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Check dataflow health status")
@dataflow_app.command("health")
def analyze_health(
    flow_id: str = typer.Argument(..., help="Dataflow ID or number from list"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Analyze dataflow health based on recent runs.

    Provides statistics including success rate, failure count,
    average duration, and common errors.

    Examples:
        aep dataflow health 1  # Use number from list
        aep dataflow health d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a
        aep dataflow health <FLOW_ID> --days 30
        aep dataflow health <FLOW_ID> --json
    """
    
    # Resolve ID from number or UUID
    try:
        resolved_id = resolve_dataflow_id_or_fail(flow_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    async def fetch_health():
        async with AEPClient(get_config()) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            return await flow_client.analyze_dataflow_health(resolved_id, lookback_days=days)

    try:
        with console.status(f"[bold blue]Analyzing dataflow health (last {days} days)..."):
            health = asyncio.run(fetch_health())

        if json_output:
            console.print_json(data=health)
            return

        # Rich formatted output
        panel_content = []

        # Summary stats
        panel_content.append(f"[bold]Analysis Period:[/bold] Last {health['lookback_days']} days")
        panel_content.append(f"[bold]Total Runs:[/bold] {health['total_runs']}")

        # Success rate with color
        success_rate = health['success_rate']
        if success_rate >= 95:
            rate_color = "green"
        elif success_rate >= 80:
            rate_color = "yellow"
        else:
            rate_color = "red"
        panel_content.append(f"[bold]Success Rate:[/bold] [{rate_color}]{success_rate:.1f}%[/{rate_color}]")

        # Run statistics
        panel_content.append(f"\n[bold cyan]Run Statistics[/bold cyan]")
        panel_content.append(f"  Success: [green]{health['success_runs']}[/green]")
        panel_content.append(f"  Failed: [red]{health['failed_runs']}[/red]")
        panel_content.append(f"  Pending/In Progress: [yellow]{health['pending_runs']}[/yellow]")

        # Duration
        avg_duration = health['average_duration_seconds']
        if avg_duration > 0:
            if avg_duration < 60:
                duration_display = f"{avg_duration:.1f} seconds"
            elif avg_duration < 3600:
                duration_display = f"{avg_duration / 60:.1f} minutes"
            else:
                duration_display = f"{avg_duration / 3600:.1f} hours"
            panel_content.append(f"[bold]Average Duration:[/bold] {duration_display}")

        # Errors
        if health['errors']:
            panel_content.append(f"\n[bold red]Recent Errors ({len(health['errors'])})[/bold red]")
            # Group errors by code
            error_counts = {}
            for error in health['errors']:
                code = error['code']
                if code not in error_counts:
                    error_counts[code] = {
                        'count': 0,
                        'message': error['message'],
                        'run_ids': []
                    }
                error_counts[code]['count'] += 1
                error_counts[code]['run_ids'].append(error['run_id'])

            for code, info in sorted(error_counts.items(), key=lambda x: x[1]['count'], reverse=True):
                panel_content.append(f"\n  [red]{code}[/red] (occurred {info['count']} times)")
                panel_content.append(f"  Message: {info['message']}")
                panel_content.append(f"  Sample Run ID: {info['run_ids'][0][:40]}...")
        else:
            panel_content.append(f"\n[green]No errors found in the analysis period![/green]")

        # Health assessment
        panel_content.append(f"\n[bold cyan]Health Assessment[/bold cyan]")
        if success_rate >= 95 and health['failed_runs'] == 0:
            assessment = "[green]Excellent - Dataflow is running smoothly[/green]"
        elif success_rate >= 80:
            assessment = "[yellow]Good - Some failures detected, monitor closely[/yellow]"
        elif success_rate >= 50:
            assessment = "[red]Poor - Significant failures, investigation recommended[/red]"
        else:
            assessment = "[red bold]Critical - High failure rate, immediate action required[/red bold]"
        panel_content.append(f"  {assessment}")

        panel = Panel(
            "\n".join(panel_content),
            title=f"[bold]Dataflow Health Analysis[/bold]",
            border_style="blue",
        )
        console.print(panel)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Ask questions about dataflows in natural language")
def _handle_single_question(
    question: str,
    days: int,
    json_output: bool,
    detected_lang: Optional[str] = None
) -> None:
    """Handle a single dataflow question (one-shot mode).
    
    Args:
        question: The question to ask
        days: Number of days to analyze
        json_output: Whether to output as JSON
        detected_lang: Pre-detected language (or None to auto-detect)
    """
    async def fetch_and_analyze():
        from adobe_experience.agent.inference import AIInferenceEngine
        from adobe_experience.i18n import t
        
        # Detect language from question (if not already detected)
        lang = detected_lang or ("ko" if any('\uac00' <= c <= '\ud7a3' for c in question) else "en")
        
        # Fetch all dataflows
        async with AEPClient(get_config()) as aep_client:
            flow_client = FlowServiceClient(aep_client)
            dataflows = await flow_client.list_dataflows(limit=100)
            
            if not dataflows:
                return None, lang
            
            # Initialize AI engine
            engine = AIInferenceEngine(get_config())
            
            # Ask AI to analyze
            result = await engine.answer_dataflow_question(
                question=question,
                dataflows=dataflows,
                language=lang,
                lookback_days=days
            )
            
            return result, lang
    
    try:
        # Auto-detect language if not provided
        lang = detected_lang or ("ko" if any('\uac00' <= c <= '\ud7a3' for c in question) else "en")
        
        # Show thinking message
        thinking_msg = "AI가 dataflow 상태를 분석하고 있습니다..." if lang == "ko" else "AI is analyzing dataflow status..."
        
        with console.status(f"[bold blue]{thinking_msg}"):
            result, lang = asyncio.run(fetch_and_analyze())
        
        if result is None:
            no_dataflows_msg = "dataflow가 없습니다." if lang == "ko" else "No dataflows found."
            console.print(f"[yellow]{no_dataflows_msg}[/yellow]")
            return
        
        if json_output:
            # JSON output
            console.print_json(data=result.model_dump())
            return
        
        # Rich formatted output
        # 1. AI Summary Panel
        summary_panel = Panel(
            result.summary,
            title=f"[bold]{'AI 분석 결과' if lang == 'ko' else 'AI Analysis Result'}[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(summary_panel)
        console.print()
        
        # 2. Dataflows Table (if issues found)
        if result.failed_dataflows:
            table = Table(
                title=f"{'문제가 있는 Dataflows' if lang == 'ko' else 'Dataflows with Issues'} ({len(result.failed_dataflows)} found)"
            )
            table.add_column("#", style="dim", width=4)
            table.add_column("Name" if lang == "en" else "이름", style="cyan", no_wrap=False, max_width=40)
            table.add_column("ID", style="dim", max_width=20)
            table.add_column("State" if lang == "en" else "상태", justify="center")
            table.add_column("Success Rate" if lang == "en" else "성공률", justify="right")
            table.add_column("Failed Runs" if lang == "en" else "실패 횟수", justify="right")
            
            for idx, flow_info in enumerate(result.failed_dataflows, 1):
                success_rate = flow_info.get("success_rate", 0)
                
                # Color-code success rate
                if success_rate >= 95:
                    rate_color = "green"
                elif success_rate >= 80:
                    rate_color = "yellow"
                else:
                    rate_color = "red"
                
                state_val = flow_info.get("state", "unknown")
                state_text = (
                    f"[green]{state_val}[/green]" 
                    if state_val == "enabled" 
                    else f"[yellow]{state_val}[/yellow]"
                )
                
                table.add_row(
                    str(idx),
                    flow_info.get("name", "N/A"),
                    flow_info.get("id", "")[:20] + "...",
                    state_text,
                    f"[{rate_color}]{success_rate:.1f}%[/{rate_color}]",
                    str(flow_info.get("failed_runs", 0))
                )
            
            console.print(table)
            console.print()
            
            # Tips
            tip_msg = (
                f"\n[dim]💡 팁: 'aep dataflow failures <번호>'로 상세 오류를 확인할 수 있습니다[/dim]"
                if lang == "ko"
                else f"\n[dim]💡 Tip: Use 'aep dataflow failures <number>' to see detailed errors[/dim]"
            )
            console.print(tip_msg)
        else:
            # No issues found
            success_msg = (
                f"[green]✓ 좋은 소식입니다! 최근 {days}일간 문제가 발견되지 않았습니다.[/green]"
                if lang == "ko"
                else f"[green]✓ Good news! No issues found in the last {days} days.[/green]"
            )
            console.print(success_msg)
        
        # Metadata footer
        footer = (
            f"[dim]분석 기간: 최근 {days}일 | 총 {result.total_checked}개 dataflow 확인됨[/dim]"
            if lang == "ko"
            else f"[dim]Analysis period: Last {days} days | {result.total_checked} dataflows checked[/dim]"
        )
        console.print(f"\n{footer}")
        
    except ValueError as ve:
        # AI API key errors
        lang = detected_lang or "en"  # Fallback to English if not detected
        console.print(f"[red]Error: {ve}[/red]")
        if "API authentication failed" in str(ve):
            console.print("\n[yellow]AI 기능을 사용하려면 API 키 설정이 필요합니다.[/yellow]" if lang == "ko" else "\n[yellow]AI features require API key configuration.[/yellow]")
            console.print(f"[dim]Run: aep ai set-key anthropic[/dim]" if lang == "en" else f"[dim]실행: aep ai set-key anthropic[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _interactive_ask_mode(days: int, json_output: bool) -> None:
    """Interactive mode for asking multiple dataflow questions.
    
    Args:
        days: Number of days to analyze
        json_output: Whether to output as JSON
    """
    from adobe_experience.i18n import t
    
    # Detect user's language preference from environment/locale
    # For now, we'll let the first question determine the language
    
    # Show welcome message
    welcome_panel = Panel(
        "[bold cyan]Interactive Dataflow Analysis Mode[/bold cyan]\n\n"
        "Ask questions in natural language (Korean or English).\n"
        "Type your question and press Enter.\n"
        "Type 'exit', 'quit', or 'q' to leave.\n\n"
        "[dim]Examples:[/dim]\n"
        "  • 현재 fail된 dataflow를 알려줘\n"
        "  • Show me failed dataflows\n"
        "  • Which dataflows have low success rates?",
        title="[bold]🤖 AI Dataflow Assistant[/bold]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(welcome_panel)
    console.print()
    
    # Interactive loop
    try:
        while True:
            # Prompt for question
            try:
                question = Prompt.ask("[bold cyan]Your question[/bold cyan] [dim](exit/q to quit)[/dim]").strip()
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit gracefully[/yellow]")
                continue
            
            # Check for exit commands
            if question.lower() in ['exit', 'quit', 'q', '종료', '나가기']:
                console.print("[dim]Exiting interactive mode...[/dim]")
                break
            
            # Skip empty questions
            if not question:
                console.print("[yellow]Please enter a question[/yellow]")
                continue
            
            # Handle the question
            console.print()  # Add spacing
            _handle_single_question(question, days, json_output)
            console.print()  # Add spacing after result
            console.print("[dim]" + "─" * 80 + "[/dim]")  # Separator
            console.print()
            
    except KeyboardInterrupt:
        console.print("\n[dim]Exiting interactive mode...[/dim]")


@dataflow_app.command("ask")
def ask_dataflow_question(
    question: Optional[str] = typer.Argument(None, help="Natural language question (Korean or English). Omit to enter interactive mode."),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Ask questions about dataflows using natural language.

    Uses AI to understand your question and provide intelligent analysis
    of dataflow health status, failures, and issues.

    MODES:
        One-shot: aep dataflow ask "your question"
        Interactive: aep dataflow ask (then type questions)

    Examples:
        # One-shot mode (backward compatible)
        aep dataflow ask "현재 fail된 dataflow를 알려줘"
        aep dataflow ask "Show me failed dataflows"
        aep dataflow ask "Which dataflows have low success rates?"
        aep dataflow ask "최근 3일간 문제가 있었던 것은?" --days 3
        
        # Interactive mode (no quotes needed!)
        aep dataflow ask
        > 현재 fail된 dataflow를 알려줘
        > Show me dataflows with issues
        > exit
    """
    if question:
        # One-shot mode (backward compatible)
        _handle_single_question(question, days, json_output)
    else:
        # Interactive mode
        _interactive_ask_mode(days, json_output)
