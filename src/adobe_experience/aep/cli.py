"""Adobe Experience Platform CLI commands."""

import typer
from rich.console import Console

# Import subcommands
from adobe_experience.cli.schema import schema_app
from adobe_experience.cli.dataset import dataset_app
from adobe_experience.cli.ingest import ingest_app

# Create AEP CLI app
aep_app = typer.Typer(
    name="aep",
    help="Adobe Experience Platform commands",
    rich_markup_mode="rich",
)

console = Console()

# Register subcommands
aep_app.add_typer(schema_app, name="schema")
aep_app.add_typer(dataset_app, name="dataset")
aep_app.add_typer(ingest_app, name="ingest")


# Add init command
@aep_app.command("init")
def aep_init():
    """Initialize Adobe Experience Platform credentials.
    
    In dry-run mode, this simulates credential setup without creating actual files.
    
    Examples:
        adobe aep init
    """
    from adobe_experience.core.config import load_onboarding_state, TutorialMode
    from rich.panel import Panel
    from rich.prompt import Confirm
    
    state = load_onboarding_state()
    
    # Check if in dry-run mode
    if state and state.mode == TutorialMode.DRY_RUN:
        console.print("[bold yellow]🎓 Dry-Run Mode: Simulating AEP initialization[/bold yellow]\n")
        console.print(Panel(
            f"[bold]Simulated AEP Setup[/bold]\n\n"
            f"Would perform the following:\n"
            f"  • Create .env file with AEP credentials\n"
            f"  • Configure OAuth Server-to-Server authentication\n"
            f"  • Set up sandbox and tenant configuration\n"
            f"  • Test connection to Adobe Experience Platform\n\n"
            f"[dim]In online mode, this would prompt for actual credentials from Adobe Developer Console.[/dim]\n\n"
            f"Required credentials:\n"
            f"  • Client ID\n"
            f"  • Client Secret\n"
            f"  • Organization ID (format: XXXXX@AdobeOrg)\n"
            f"  • Technical Account ID\n"
            f"  • Sandbox Name\n"
            f"  • Tenant ID",
            border_style="yellow",
        ))
        console.print(f"[green]✓[/green] Dry-run completed successfully!")
        console.print(f"\n[dim]To set up real credentials, exit dry-run mode and run: adobe aep init[/dim]")
        return
    
    # Redirect to actual init setup
    from adobe_experience.cli.init import setup
    console.print("[cyan]Running interactive setup wizard...[/cyan]\n")
    setup()


# Add info command
@aep_app.command("info")
def aep_info():
    """Show Adobe Experience Platform information."""
    console.print("[cyan]Adobe Experience Platform CLI[/cyan]")
    console.print("Manage schemas, datasets, and data ingestion")


__all__ = ["aep_app"]
