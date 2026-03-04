"""Destination management commands."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from adobe_experience.aep.client import AEPClient
from adobe_experience.cache.destination_cache import DestinationCache
from adobe_experience.cli._id_resolver import resolve_destination_id_or_fail
from adobe_experience.cli.command_metadata import (
    CommandCategory,
    command_metadata,
    register_command_group_metadata,
)
from adobe_experience.core.config import get_config
from adobe_experience.destination.client import DestinationServiceClient
from adobe_experience.destination.models import DestinationType

console = Console()
destination_app = typer.Typer(help="Destination management commands")

# Register command group metadata
register_command_group_metadata(
    "destination", CommandCategory.API, "Destination management API operations"
)


@command_metadata(CommandCategory.API, "List available destinations")
@destination_app.command("list")
def list_destinations(
    limit: int = typer.Option(50, "--limit", "-l", help="Number of destinations to display"),
    dest_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by destination type (EMAIL, ADS, CDP, etc.)"
    ),
    full_id: bool = typer.Option(False, "--full-id", help="Display full UUIDs instead of truncated IDs"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List available destinations in the catalog.

    Shows all destination types available for activation in Adobe Experience Platform.

    Examples:
        aep destination list
        aep destination list --limit 100
        aep destination list --type EMAIL
        aep destination list --full-id
        aep destination list --json
    """

    async def list_dests():
        # Parse destination type if provided
        destination_type = None
        if dest_type:
            try:
                destination_type = DestinationType(dest_type.upper())
            except ValueError:
                console.print(
                    f"[red]Invalid destination type: {dest_type}[/red]"
                )
                console.print(
                    f"[yellow]Valid types: {', '.join([dt.value for dt in DestinationType])}[/yellow]"
                )
                raise typer.Exit(1)

        async with AEPClient(get_config()) as aep_client:
            dest_client = DestinationServiceClient(aep_client)
            return await dest_client.list_destinations(
                limit=limit, destination_type=destination_type
            )

    try:
        with console.status("[bold blue]Fetching destinations..."):
            destinations = asyncio.run(list_dests())

        if json_output:
            print(
                json.dumps(
                    [d.model_dump(mode="json") for d in destinations], indent=2
                )
            )
            return

        if not destinations:
            console.print("\n[yellow]No destinations found[/yellow]")
            return

        # Save to cache for number shortcuts
        cache = DestinationCache()
        mappings = {idx: dest.id for idx, dest in enumerate(destinations, 1)}
        cache.save_mappings(mappings)

        # Display destinations table
        table = Table(title="AEP Destinations")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("ID", style="blue")
        table.add_column("Supported Identities", style="green")

        for idx, dest in enumerate(destinations, 1):
            identities_str = (
                ", ".join(dest.supported_identities[:3])
                if dest.supported_identities
                else "N/A"
            )
            if dest.supported_identities and len(dest.supported_identities) > 3:
                identities_str += f" (+{len(dest.supported_identities) - 3} more)"

            # Display full or truncated ID based on flag
            display_id = dest.id if full_id else (dest.id[:8] + "..." if len(dest.id) > 8 else dest.id)

            table.add_row(
                str(idx),
                dest.name,
                dest.destination_type.value if dest.destination_type else "N/A",
                display_id,
                identities_str,
            )

        console.print(table)
        console.print(f"\n[green]✓[/green] Found {len(destinations)} destination(s)")
        console.print(
            "\n[dim]💡 Tip: Use 'aep destination get <# or ID>' to view details.[/dim]"
        )
        console.print(
            "[dim]💡 Tip: Use number shortcuts (e.g., 'aep destination get 1') for quick access.[/dim]"
        )

    except NotImplementedError as e:
        console.print(f"\n[yellow]⚠ Feature not yet implemented[/yellow]")
        console.print(f"[dim]{str(e)}[/dim]")
        console.print(
            "\n[cyan]TODO:[/cyan] Verify Adobe Destination API endpoints and implement client methods."
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Get destination details")
@destination_app.command("get")
def get_destination(
    destination_id: str = typer.Argument(..., help="Destination ID or number from list"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get detailed information about a destination.

    Shows destination configuration, supported identities, and connection specs.

    Examples:
        aep destination get <destination-id>
        aep destination get 1        # Using number from list
        aep destination get <id> --json
    """

    async def fetch_destination():
        # Resolve destination ID (supports number shortcuts)
        try:
            resolved_id = resolve_destination_id_or_fail(destination_id)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        async with AEPClient(get_config()) as aep_client:
            dest_client = DestinationServiceClient(aep_client)
            return await dest_client.get_destination(resolved_id)

    try:
        with console.status(
            f"[bold blue]Fetching destination {destination_id}..."
        ):
            destination = asyncio.run(fetch_destination())

        if json_output:
            print(json.dumps(destination.model_dump(mode="json"), indent=2))
            return

        # Display destination details
        console.print(f"\n[bold cyan]{destination.name}[/bold cyan]")
        console.print(f"[dim]ID: {destination.id}[/dim]\n")

        if destination.description:
            console.print(Panel(destination.description, title="Description"))

        # Destination info
        info_lines = []
        info_lines.append(
            f"[cyan]Type:[/cyan] {destination.destination_type.value if destination.destination_type else 'N/A'}"
        )
        if destination.connection_spec:
            info_lines.append(
                f"[cyan]Connection Spec:[/cyan] {destination.connection_spec.name} ({destination.connection_spec.id[:8]}...)"
            )
        if destination.version:
            info_lines.append(f"[cyan]Version:[/cyan] {destination.version}")

        console.print(Panel("\n".join(info_lines), title="Details"))

        # Supported identities
        if destination.supported_identities:
            identities_table = Table(title="Supported Identities")
            identities_table.add_column("Identity Namespace", style="green")

            for identity in destination.supported_identities:
                identities_table.add_row(identity)

            console.print(identities_table)

        # Required attributes
        if destination.required_attributes:
            console.print(
                f"\n[cyan]Required Attributes:[/cyan] {', '.join(destination.required_attributes)}"
            )

    except NotImplementedError as e:
        console.print(f"\n[yellow]⚠ Feature not yet implemented[/yellow]")
        console.print(f"[dim]{str(e)}[/dim]")
        console.print(
            "\n[cyan]TODO:[/cyan] Verify Adobe Destination API endpoints and implement client methods."
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "List segments activated to destination")
@destination_app.command("segments")
def list_destination_segments(
    destination_id: str = typer.Argument(..., help="Destination instance ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all segments activated to a destination.

    Shows which segments are sending data to this destination,
    along with activation status and schedule.

    Examples:
        aep destination segments <destination-id>
        aep destination segments <id> --json
    """

    async def list_segs():
        async with AEPClient(get_config()) as aep_client:
            dest_client = DestinationServiceClient(aep_client)
            return await dest_client.list_destination_segments(destination_id)

    try:
        with console.status(
            f"[bold blue]Fetching segments for destination {destination_id}..."
        ):
            activations = asyncio.run(list_segs())

        if json_output:
            print(
                json.dumps(
                    [a.model_dump(mode="json") for a in activations], indent=2
                )
            )
            return

        if not activations:
            console.print(
                f"\n[yellow]No segments activated to destination {destination_id}[/yellow]"
            )
            console.print(
                "\n[dim]Use 'aep segment activate' to activate segments to this destination.[/dim]"
            )
            return

        # Display activations table
        table = Table(title=f"Segments for Destination {destination_id}")
        table.add_column("#", style="dim", width=4)
        table.add_column("Segment ID", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Dataflow ID", style="blue")
        table.add_column("Schedule", style="green")

        for idx, activation in enumerate(activations, 1):
            status_color = "green" if activation.status == "ACTIVE" else "yellow"
            schedule_str = (
                activation.schedule.get("frequency", "N/A")
                if activation.schedule
                else "N/A"
            )

            table.add_row(
                str(idx),
                activation.segment_id[:8] + "..."
                if len(activation.segment_id) > 8
                else activation.segment_id,
                f"[{status_color}]{activation.status}[/{status_color}]",
                activation.dataflow_id[:8] + "..."
                if activation.dataflow_id and len(activation.dataflow_id) > 8
                else (activation.dataflow_id or "N/A"),
                schedule_str,
            )

        console.print(table)
        console.print(
            f"\n[green]✓[/green] Found {len(activations)} activated segment(s)"
        )

    except NotImplementedError as e:
        console.print(f"\n[yellow]⚠ Feature not yet implemented[/yellow]")
        console.print(f"[dim]{str(e)}[/dim]")
        console.print(
            "\n[cyan]TODO:[/cyan] Verify Adobe Destination API endpoints and implement client methods."
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "List configured destination instances")
@destination_app.command("instances")
def list_destination_instances(
    limit: int = typer.Option(50, "--limit", "-l", help="Number of instances to display"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List configured destination instances.

    Shows destinations that have been configured with credentials
    and are ready to receive segment activations.

    Examples:
        aep destination instances
        aep destination instances --limit 100
        aep destination instances --json
    """

    async def list_instances():
        async with AEPClient(get_config()) as aep_client:
            dest_client = DestinationServiceClient(aep_client)
            return await dest_client.list_destination_instances(limit=limit)

    try:
        with console.status("[bold blue]Fetching destination instances..."):
            instances = asyncio.run(list_instances())

        if json_output:
            print(
                json.dumps(
                    [i.model_dump(mode="json") for i in instances], indent=2
                )
            )
            return

        if not instances:
            console.print("\n[yellow]No configured destination instances found[/yellow]")
            console.print(
                "\n[dim]Configure destinations in the AEP UI to create instances.[/dim]"
            )
            return

        # Display instances table
        table = Table(title="AEP Destination Instances")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("State", style="green")
        table.add_column("ID", style="blue")

        for idx, instance in enumerate(instances, 1):
            state_color = "green" if instance.state == "enabled" else "yellow"

            table.add_row(
                str(idx),
                instance.name,
                instance.destination_type.value
                if instance.destination_type
                else "N/A",
                f"[{state_color}]{instance.state}[/{state_color}]",
                instance.id[:8] + "..." if len(instance.id) > 8 else instance.id,
            )

        console.print(table)
        console.print(
            f"\n[green]✓[/green] Found {len(instances)} instance(s)"
        )
        console.print(
            "\n[dim]Use 'aep destination segments <ID>' to view activated segments.[/dim]"
        )

    except NotImplementedError as e:
        console.print(f"\n[yellow]⚠ Feature not yet implemented[/yellow]")
        console.print(f"[dim]{str(e)}[/dim]")
        console.print(
            "\n[cyan]TODO:[/cyan] Verify Adobe Destination API endpoints and implement client methods."
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
