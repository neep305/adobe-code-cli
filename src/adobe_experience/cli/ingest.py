"""CLI commands for data ingestion to Adobe Experience Platform."""

from pathlib import Path
from typing import List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from adobe_experience.aep.client import AEPClient
from adobe_experience.catalog.client import CatalogServiceClient
from adobe_experience.core.config import get_config
from adobe_experience.ingestion.bulk_upload import BulkIngestClient
from adobe_experience.ingestion.progress_upload import BulkIngestClientWithProgress

console = Console()
ingest_app = typer.Typer(help="Data ingestion commands")


@ingest_app.command("upload-file")
async def upload_file(
    file: Path = typer.Argument(..., help="Path to file to upload", exists=True, dir_okay=False),
    batch_id: str = typer.Option(..., "--batch", "-b", help="Batch ID to upload to"),
    file_name: Optional[str] = typer.Option(None, "--name", "-n", help="Custom file name in AEP (defaults to original filename)"),
    show_progress: bool = typer.Option(True, "--progress/--no-progress", help="Show upload progress bar"),
):
    """Upload a single file to an AEP batch.
    
    Example:
        adobe aep ingest upload-file customers.json --batch abc123
        adobe aep ingest upload-file data.csv --batch abc123 --name customers.csv
    """
    try:
        config = get_config()
        aep_client = AEPClient(
            client_id=config.client_id,
            client_secret=config.client_secret,
            org_id=config.org_id,
            sandbox_name=config.sandbox_name,
        )
        
        if show_progress:
            # Use progress tracking version
            bulk = BulkIngestClientWithProgress(aep_client)
        else:
            bulk = BulkIngestClient(aep_client)
        
        with console.status(f"[bold green]Uploading {file.name}...") as status:
            result = await bulk.upload_file(
                file_path=file,
                batch_id=batch_id,
                file_name=file_name,
            )
        
        if result["success"]:
            panel = Panel(
                f"[green]✓[/green] Successfully uploaded [cyan]{result['file_name']}[/cyan]\n"
                f"Size: {result['size_bytes']:,} bytes\n"
                f"Batch ID: {batch_id}",
                title="Upload Complete",
                border_style="green",
            )
            rprint(panel)
        else:
            console.print(f"[red]✗ Upload failed: {result.get('error', 'Unknown error')}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@ingest_app.command("upload-batch")
async def upload_batch(
    files: List[Path] = typer.Argument(..., help="Paths to files to upload"),
    batch_id: str = typer.Option(..., "--batch", "-b", help="Batch ID to upload to"),
    max_concurrent: int = typer.Option(3, "--concurrent", "-c", help="Maximum concurrent uploads"),
):
    """Upload multiple files to an AEP batch concurrently.
    
    Example:
        adobe aep ingest upload-batch file1.json file2.json file3.json --batch abc123
        adobe aep ingest upload-batch *.json --batch abc123 --concurrent 5
    """
    try:
        # Validate all files exist
        for file in files:
            if not file.exists():
                console.print(f"[red]File not found: {file}[/red]")
                raise typer.Exit(1)
        
        config = get_config()
        aep_client = AEPClient(
            client_id=config.client_id,
            client_secret=config.client_secret,
            org_id=config.org_id,
            sandbox_name=config.sandbox_name,
        )
        
        bulk = BulkIngestClient(aep_client)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Uploading {len(files)} files...", total=len(files))
            
            results = await bulk.upload_multiple_files(
                file_paths=files,
                batch_id=batch_id,
                max_concurrent=max_concurrent,
            )
            
            progress.update(task, completed=len(files))
        
        # Display results
        table = Table(title=f"Upload Results - Batch {batch_id}")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Size", justify="right")
        table.add_column("Details", style="dim")
        
        success_count = 0
        for result in results:
            if result["success"]:
                success_count += 1
                status = "[green]✓ Success[/green]"
                size = f"{result['size_bytes']:,} B"
                details = result['file_name']
            else:
                status = "[red]✗ Failed[/red]"
                size = "-"
                details = result.get('error', 'Unknown error')
            
            table.add_row(
                result.get('file_name', result.get('original_path', 'Unknown')),
                status,
                size,
                details,
            )
        
        console.print(table)
        console.print(f"\n[bold]Summary:[/bold] {success_count}/{len(results)} files uploaded successfully")
        
        if success_count < len(results):
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@ingest_app.command("upload-directory")
async def upload_directory(
    directory: Path = typer.Argument(..., help="Directory path to upload", exists=True, dir_okay=True, file_okay=False),
    batch_id: str = typer.Option(..., "--batch", "-b", help="Batch ID to upload to"),
    pattern: str = typer.Option("*", "--pattern", "-p", help="File glob pattern (e.g., '*.json', '*.csv')"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Search subdirectories recursively"),
    max_concurrent: int = typer.Option(3, "--concurrent", "-c", help="Maximum concurrent uploads"),
):
    """Upload all matching files from a directory to an AEP batch.
    
    Example:
        adobe aep ingest upload-directory ./data --batch abc123 --pattern "*.json"
        adobe aep ingest upload-directory ./exports --batch abc123 --recursive
    """
    try:
        config = get_config()
        aep_client = AEPClient(
            client_id=config.client_id,
            client_secret=config.client_secret,
            org_id=config.org_id,
            sandbox_name=config.sandbox_name,
        )
        
        bulk = BulkIngestClient(aep_client)
        
        with console.status(f"[bold green]Scanning {directory} for {pattern} files..."):
            results = await bulk.upload_directory(
                directory=directory,
                batch_id=batch_id,
                pattern=pattern,
                recursive=recursive,
                max_concurrent=max_concurrent,
            )
        
        if not results:
            console.print(f"[yellow]No files found matching pattern '{pattern}' in {directory}[/yellow]")
            raise typer.Exit(0)
        
        # Display results
        table = Table(title=f"Upload Results - Batch {batch_id}")
        table.add_column("File", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Size", justify="right")
        table.add_column("Details", style="dim")
        
        success_count = 0
        for result in results:
            if result["success"]:
                success_count += 1
                status = "[green]✓ Success[/green]"
                size = f"{result['size_bytes']:,} B"
                details = result['file_name']
            else:
                status = "[red]✗ Failed[/red]"
                size = "-"
                details = result.get('error', 'Unknown error')
            
            # Show relative path from directory
            original = Path(result.get('original_path', ''))
            try:
                rel_path = original.relative_to(directory)
            except ValueError:
                rel_path = original
            
            table.add_row(
                str(rel_path),
                status,
                size,
                details,
            )
        
        console.print(table)
        console.print(f"\n[bold]Summary:[/bold] {success_count}/{len(results)} files uploaded successfully")
        
        if success_count < len(results):
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@ingest_app.command("status")
async def check_status(
    batch_id: str = typer.Argument(..., help="Batch ID to check"),
    file_name: Optional[str] = typer.Option(None, "--file", "-f", help="Specific file to check (optional)"),
):
    """Check upload status of files in a batch.
    
    Example:
        adobe aep ingest status abc123
        adobe aep ingest status abc123 --file customers.json
    """
    try:
        config = get_config()
        aep_client = AEPClient(
            client_id=config.client_id,
            client_secret=config.client_secret,
            org_id=config.org_id,
            sandbox_name=config.sandbox_name,
        )
        
        # Check batch status first
        catalog = CatalogServiceClient(aep_client)
        batch = await catalog.get_batch(batch_id)
        
        if not batch:
            console.print(f"[red]Batch {batch_id} not found[/red]")
            raise typer.Exit(1)
        
        # Display batch info
        panel = Panel(
            f"Status: [bold]{batch.status.value}[/bold]\n"
            f"Dataset: {batch.datasetId}\n"
            f"Created: {batch.created}\n"
            f"Records: {batch.metrics.recordsRead if batch.metrics else 'N/A'}",
            title=f"Batch {batch_id}",
            border_style="blue",
        )
        rprint(panel)
        
        # If specific file requested
        if file_name:
            bulk = BulkIngestClient(aep_client)
            status = await bulk.get_upload_status(batch_id, file_name)
            
            if status["exists"]:
                file_panel = Panel(
                    f"File: [cyan]{status['file_name']}[/cyan]\n"
                    f"Size: {status['size_bytes']:,} bytes\n"
                    f"Records: {status['records']}\n"
                    f"Valid: [{'green' if status['is_valid'] else 'red'}]{status['is_valid']}[/]",
                    title="File Status",
                    border_style="green" if status['is_valid'] else "red",
                )
                rprint(file_panel)
            else:
                console.print(f"[yellow]File '{file_name}' not found in batch[/yellow]")
        else:
            # List all files in batch
            files = await catalog.list_dataset_files(batch.datasetId, batch_id=batch_id)
            
            if files:
                table = Table(title="Files in Batch")
                table.add_column("File Name", style="cyan")
                table.add_column("Size", justify="right")
                table.add_column("Records", justify="right")
                table.add_column("Valid", style="bold")
                
                for file in files:
                    table.add_row(
                        file.name,
                        f"{file.sizeInBytes:,} B" if file.sizeInBytes else "-",
                        str(file.records) if file.records else "-",
                        "[green]✓[/green]" if file.isValid else "[red]✗[/red]",
                    )
                
                console.print(table)
            else:
                console.print("[dim]No files found in batch[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@ingest_app.callback()
def callback():
    """Data ingestion commands for uploading files to AEP batches."""
    pass
