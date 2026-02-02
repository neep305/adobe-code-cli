"""Dataset and batch management commands."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from adobe_experience.aep.client import AEPClient
from adobe_experience.catalog.client import CatalogServiceClient
from adobe_experience.catalog.models import BatchStatus
from adobe_experience.core.config import get_config

console = Console()
dataset_app = typer.Typer(help="Dataset and batch management commands")


@dataset_app.command("list")
def list_datasets(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of datasets to display"),
    schema_id: Optional[str] = typer.Option(None, "--schema", help="Filter by schema ID"),
    state: Optional[str] = typer.Option(None, "--state", help="Filter by state (DRAFT or ENABLED)"),
) -> None:
    """List datasets in Adobe Experience Platform.

    Examples:
        adobe aep dataset list
        adobe aep dataset list --limit 50
        adobe aep dataset list --schema "https://ns.adobe.com/.../schemas/..."
        adobe aep dataset list --state ENABLED
    """

    async def fetch_datasets():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.list_datasets(limit=limit, schema_id=schema_id, state=state)

    try:
        with console.status("[bold blue]Fetching datasets..."):
            datasets = asyncio.run(fetch_datasets())

        if not datasets:
            console.print("[yellow]No datasets found[/yellow]")
            return

        table = Table(title=f"📊 Datasets ({len(datasets)} found)")
        table.add_column("Name", style="cyan", no_wrap=False)
        table.add_column("ID", style="dim")
        table.add_column("State", justify="center")
        table.add_column("Schema ID", style="green")

        for ds in datasets:
            schema_display = (
                ds.schema_ref.id[-60:] + "..." if len(ds.schema_ref.id) > 60 else ds.schema_ref.id
            )
            table.add_row(
                ds.name or "N/A",
                ds.id[:24] + "..." if ds.id and len(ds.id) > 24 else ds.id or "N/A",
                f"[green]{ds.state}[/green]" if ds.state == "ENABLED" else f"[yellow]{ds.state}[/yellow]" if ds.state else "N/A",
                schema_display if ds.schema_ref else "N/A",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("create")
def create_dataset(
    name: str = typer.Option(..., "--name", "-n", help="Dataset name"),
    schema_id: str = typer.Option(..., "--schema", "-s", help="Schema ID (full URI)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Dataset description"),
    enable_profile: bool = typer.Option(False, "--enable-profile", help="Enable for Real-Time Customer Profile"),
    enable_identity: bool = typer.Option(False, "--enable-identity", help="Enable for Identity Service"),
) -> None:
    """Create a new dataset.

    The dataset will be associated with an existing XDM schema. You must provide
    the full schema URI (e.g., https://ns.adobe.com/{tenant}/schemas/{id}).

    Examples:
        adobe aep dataset create --name "Customer Events" --schema "https://..."
        adobe aep dataset create -n "Orders" -s "https://..." --enable-profile
        adobe aep dataset create -n "Products" -s "https://..." -d "Product catalog"
    """

    async def create():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.create_dataset(
                name=name,
                schema_id=schema_id,
                description=description,
                enable_profile=enable_profile,
                enable_identity=enable_identity,
            )

    try:
        with console.status(f"[bold blue]Creating dataset '{name}'..."):
            dataset_id = asyncio.run(create())

        console.print()
        console.print(Panel(
            f"[green]✓[/green] Dataset created successfully!\n\n"
            f"[cyan]Dataset ID:[/cyan] {dataset_id}\n"
            f"[cyan]Name:[/cyan] {name}\n"
            f"[cyan]Profile Enabled:[/cyan] {'Yes' if enable_profile else 'No'}\n"
            f"[cyan]Identity Enabled:[/cyan] {'Yes' if enable_identity else 'No'}",
            title="✨ Dataset Created",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("get")
def get_dataset(
    dataset_id: str = typer.Argument(..., help="Dataset ID"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save to JSON file"),
) -> None:
    """Get dataset details by ID.

    Examples:
        adobe aep dataset get 5c8c3c555033b814b69f947f
        adobe aep dataset get 5c8c3c555033b814b69f947f --output dataset.json
    """

    async def fetch_dataset():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.get_dataset(dataset_id)

    try:
        with console.status("[bold blue]Fetching dataset..."):
            dataset = asyncio.run(fetch_dataset())

        if output:
            dataset_dict = dataset.model_dump(by_alias=True, exclude_none=True)
            output.write_text(json.dumps(dataset_dict, indent=2))
            console.print(f"[green]✓[/green] Dataset details saved to {output}")
        else:
            # Display in console
            console.print()
            console.print(Panel(
                f"[cyan]Name:[/cyan] {dataset.name}\n"
                f"[cyan]ID:[/cyan] {dataset.id}\n"
                f"[cyan]State:[/cyan] {dataset.state or 'N/A'}\n"
                f"[cyan]Description:[/cyan] {dataset.description or 'N/A'}\n"
                f"[cyan]Schema:[/cyan] {dataset.schema_ref.id if dataset.schema_ref else 'N/A'}\n"
                f"[cyan]Organization:[/cyan] {dataset.ims_org or 'N/A'}\n"
                f"[cyan]Created:[/cyan] {dataset.created or 'N/A'}\n"
                f"[cyan]Updated:[/cyan] {dataset.updated or 'N/A'}",
                title=f"📊 Dataset: {dataset.name}",
                border_style="cyan"
            ))

            if dataset.tags:
                tags_info = []
                if dataset.tags.unified_profile:
                    tags_info.append(f"[green]Profile:[/green] {', '.join(dataset.tags.unified_profile)}")
                if dataset.tags.unified_identity:
                    tags_info.append(f"[green]Identity:[/green] {', '.join(dataset.tags.unified_identity)}")
                
                if tags_info:
                    console.print("\n[bold]Tags:[/bold]")
                    for tag in tags_info:
                        console.print(f"  {tag}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("delete")
def delete_dataset(
    dataset_id: str = typer.Argument(..., help="Dataset ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a dataset.

    WARNING: This action cannot be undone. All data in the dataset will be lost.

    Examples:
        adobe aep dataset delete 5c8c3c555033b814b69f947f
        adobe aep dataset delete 5c8c3c555033b814b69f947f --yes
    """

    if not yes:
        confirm = typer.confirm(
            f"⚠️  Are you sure you want to delete dataset {dataset_id}?\n"
            "This action cannot be undone and all data will be lost.",
            abort=True
        )

    async def delete():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            await catalog.delete_dataset(dataset_id)

    try:
        with console.status(f"[bold red]Deleting dataset {dataset_id}..."):
            asyncio.run(delete())

        console.print(f"[green]✓[/green] Dataset {dataset_id} deleted successfully")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("enable-profile")
def enable_profile(
    dataset_id: str = typer.Argument(..., help="Dataset ID"),
) -> None:
    """Enable dataset for Real-Time Customer Profile.

    This allows the dataset's data to be included in unified customer profiles.

    Examples:
        adobe aep dataset enable-profile 5c8c3c555033b814b69f947f
    """

    async def enable():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.enable_dataset_for_profile(dataset_id)

    try:
        with console.status(f"[bold blue]Enabling Profile for dataset {dataset_id}..."):
            dataset = asyncio.run(enable())

        console.print(
            f"[green]✓[/green] Profile enabled for dataset [cyan]{dataset.name}[/cyan] ({dataset_id})"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("enable-identity")
def enable_identity(
    dataset_id: str = typer.Argument(..., help="Dataset ID"),
) -> None:
    """Enable dataset for Identity Service.

    This allows the dataset's data to be used for identity graph construction.

    Examples:
        adobe aep dataset enable-identity 5c8c3c555033b814b69f947f
    """

    async def enable():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.enable_dataset_for_identity(dataset_id)

    try:
        with console.status(f"[bold blue]Enabling Identity for dataset {dataset_id}..."):
            dataset = asyncio.run(enable())

        console.print(
            f"[green]✓[/green] Identity enabled for dataset [cyan]{dataset.name}[/cyan] ({dataset_id})"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# ==================== Batch Commands ====================


@dataset_app.command("create-batch")
def create_batch_cmd(
    dataset_id: str = typer.Option(..., "--dataset", "-d", help="Dataset ID"),
    format: str = typer.Option("parquet", "--format", "-f", help="Input format: parquet, json, csv, avro"),
) -> None:
    """Create a new batch for data ingestion.

    A batch is a container for uploading data files. After creating a batch,
    you must upload files and then complete the batch to trigger processing.

    Examples:
        adobe aep dataset create-batch --dataset 5c8c3c555033b814b69f947f --format json
        adobe aep dataset create-batch -d 5c8c3c555033b814b69f947f -f parquet
    """

    async def create():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.create_batch(dataset_id=dataset_id, format=format)

    try:
        with console.status(f"[bold blue]Creating batch for dataset {dataset_id}..."):
            batch_id = asyncio.run(create())

        console.print()
        console.print(Panel(
            f"[green]✓[/green] Batch created successfully!\n\n"
            f"[cyan]Batch ID:[/cyan] {batch_id}\n"
            f"[cyan]Dataset:[/cyan] {dataset_id}\n"
            f"[cyan]Format:[/cyan] {format}\n\n"
            f"[yellow]Next steps:[/yellow]\n"
            f"1. Upload files to the batch\n"
            f"2. Complete the batch: [cyan]adobe aep dataset complete-batch {batch_id}[/cyan]\n"
            f"3. Monitor status: [cyan]adobe aep dataset batch-status {batch_id}[/cyan]",
            title="✨ Batch Created",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("batch-status")
def batch_status(
    batch_id: str = typer.Argument(..., help="Batch ID"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch status updates (poll every 5 seconds)"),
) -> None:
    """Check batch ingestion status.

    Examples:
        adobe aep dataset batch-status 5d01230fc78a4e4f8c0c6b387b4b8d1c
        adobe aep dataset batch-status 5d01230fc78a4e4f8c0c6b387b4b8d1c --watch
    """

    async def get_status():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.get_batch(batch_id)

    async def watch_status():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            return await catalog.wait_for_batch_completion(batch_id, timeout=600, poll_interval=5)

    try:
        if watch:
            console.print(f"[bold blue]Watching batch {batch_id}...[/bold blue]")
            console.print("[dim]Press Ctrl+C to stop watching[/dim]\n")

            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Polling batch status...", total=None)

                    batch = asyncio.run(watch_status())

                console.print(f"\n[green]✓[/green] Batch completed successfully!")
                _display_batch_details(batch)

            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped watching[/yellow]")
                batch = asyncio.run(get_status())
                _display_batch_details(batch)

        else:
            with console.status("[bold blue]Fetching batch status..."):
                batch = asyncio.run(get_status())

            _display_batch_details(batch)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("list-batches")
def list_batches(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of batches to display"),
    dataset_id: Optional[str] = typer.Option(None, "--dataset", "-d", help="Filter by dataset ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (loading, processing, success, failed)"),
) -> None:
    """List batches in Adobe Experience Platform.

    Examples:
        adobe aep dataset list-batches
        adobe aep dataset list-batches --dataset 5c8c3c555033b814b69f947f
        adobe aep dataset list-batches --status success --limit 50
    """

    async def fetch_batches():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            batch_status_enum = BatchStatus(status) if status else None
            return await catalog.list_batches(
                limit=limit,
                dataset_id=dataset_id,
                status=batch_status_enum
            )

    try:
        with console.status("[bold blue]Fetching batches..."):
            batches = asyncio.run(fetch_batches())

        if not batches:
            console.print("[yellow]No batches found[/yellow]")
            return

        table = Table(title=f"📦 Batches ({len(batches)} found)")
        table.add_column("Batch ID", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Records", justify="right")
        table.add_column("Created", style="dim")

        for batch in batches:
            status_color = {
                BatchStatus.SUCCESS: "green",
                BatchStatus.FAILED: "red",
                BatchStatus.PROCESSING: "yellow",
                BatchStatus.LOADING: "blue",
            }.get(batch.status, "white")

            records = "N/A"
            if batch.metrics and batch.metrics.records_written is not None:
                records = str(batch.metrics.records_written)

            table.add_row(
                batch.id[:24] + "...",
                f"[{status_color}]{batch.status.value}[/{status_color}]",
                records,
                str(batch.created) if batch.created else "N/A",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("complete-batch")
def complete_batch(
    batch_id: str = typer.Argument(..., help="Batch ID"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for batch processing to complete"),
) -> None:
    """Complete a batch (signal that all files have been uploaded).

    After uploading all files to a batch, you must complete the batch to
    trigger AEP's data processing pipeline.

    Examples:
        adobe aep dataset complete-batch 5d01230fc78a4e4f8c0c6b387b4b8d1c
        adobe aep dataset complete-batch 5d01230fc78a4e4f8c0c6b387b4b8d1c --wait
    """

    async def complete():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            await catalog.complete_batch(batch_id)

    async def complete_and_wait():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            await catalog.complete_batch(batch_id)
            return await catalog.wait_for_batch_completion(batch_id, timeout=600, poll_interval=5)

    try:
        if wait:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Completing batch and waiting for processing...", total=None)
                batch = asyncio.run(complete_and_wait())

            console.print(f"\n[green]✓[/green] Batch processing completed!")
            _display_batch_details(batch)

        else:
            with console.status(f"[bold blue]Completing batch {batch_id}..."):
                asyncio.run(complete())

            console.print(f"[green]✓[/green] Batch {batch_id} marked as complete")
            console.print(f"[dim]Monitor status with: adobe aep dataset batch-status {batch_id}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@dataset_app.command("abort-batch")
def abort_batch(
    batch_id: str = typer.Argument(..., help="Batch ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Abort a batch ingestion.

    Examples:
        adobe aep dataset abort-batch 5d01230fc78a4e4f8c0c6b387b4b8d1c
        adobe aep dataset abort-batch 5d01230fc78a4e4f8c0c6b387b4b8d1c --yes
    """

    if not yes:
        typer.confirm(f"Are you sure you want to abort batch {batch_id}?", abort=True)

    async def abort():
        async with AEPClient(get_config()) as aep_client:
            catalog = CatalogServiceClient(aep_client)
            await catalog.abort_batch(batch_id)

    try:
        with console.status(f"[bold red]Aborting batch {batch_id}..."):
            asyncio.run(abort())

        console.print(f"[green]✓[/green] Batch {batch_id} aborted")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# ==================== Helper Functions ====================


def _display_batch_details(batch) -> None:
    """Display batch details in a formatted panel."""
    status_color = {
        BatchStatus.SUCCESS: "green",
        BatchStatus.FAILED: "red",
        BatchStatus.PROCESSING: "yellow",
        BatchStatus.LOADING: "blue",
    }.get(batch.status, "white")

    details = [
        f"[cyan]Batch ID:[/cyan] {batch.id}",
        f"[cyan]Status:[/cyan] [{status_color}]{batch.status.value}[/{status_color}]",
        f"[cyan]Created:[/cyan] {batch.created}",
        f"[cyan]Updated:[/cyan] {batch.updated}",
    ]

    if batch.metrics:
        details.append("\n[bold]Metrics:[/bold]")
        if batch.metrics.records_read is not None:
            details.append(f"  [cyan]Records Read:[/cyan] {batch.metrics.records_read:,}")
        if batch.metrics.records_written is not None:
            details.append(f"  [cyan]Records Written:[/cyan] {batch.metrics.records_written:,}")
        if batch.metrics.records_failed is not None:
            details.append(f"  [cyan]Records Failed:[/cyan] {batch.metrics.records_failed:,}")
        if batch.metrics.failure_reason:
            details.append(f"  [red]Failure Reason:[/red] {batch.metrics.failure_reason}")

    if batch.errors:
        details.append("\n[bold red]Errors:[/bold red]")
        for error in batch.errors[:5]:  # Show first 5 errors
            details.append(f"  [red]•[/red] {error.code}: {error.description}")
        if len(batch.errors) > 5:
            details.append(f"  [dim]... and {len(batch.errors) - 5} more errors[/dim]")

    console.print()
    console.print(Panel(
        "\n".join(details),
        title="📦 Batch Details",
        border_style=status_color
    ))
