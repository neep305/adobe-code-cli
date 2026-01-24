"""Adobe Experience Platform CLI commands."""

import typer
from rich.console import Console

# Import subcommands
from adobe_experience.cli.schema import schema_app

# Create AEP CLI app
aep_app = typer.Typer(
    name="aep",
    help="Adobe Experience Platform commands",
    rich_markup_mode="rich",
)

console = Console()

# Register subcommands
aep_app.add_typer(schema_app, name="schema")

# Add info command
@aep_app.command("info")
def aep_info():
    """Show Adobe Experience Platform information."""
    console.print("[cyan]Adobe Experience Platform CLI[/cyan]")
    console.print("Manage schemas, datasets, and data ingestion")


__all__ = ["aep_app"]
