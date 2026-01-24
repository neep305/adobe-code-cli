"""Legacy CLI wrapper for backward compatibility.

This module provides the adobe-aep command for backward compatibility.
Users are encouraged to migrate to the new 'adobe aep' command structure.
"""

import sys
import typer
from rich.console import Console

from adobe_experience.cli.main import app as main_app
from adobe_experience.aep.cli import aep_app

# Create legacy app
legacy_aep_app = typer.Typer(
    name="adobe-aep",
    help="[deprecated] Use 'adobe aep' instead. This command will be removed in v1.0.0",
    add_completion=False,
)

console = Console()


def show_deprecation_warning():
    """Show deprecation warning to users."""
    console.print(
        "\n[yellow]⚠️  Deprecation Warning:[/yellow]"
        "\n[dim]The 'adobe-aep' command is deprecated and will be removed in v1.0.0[/dim]"
        "\n[dim]Please use 'adobe aep' instead:[/dim]"
        "\n"
    )
    
    # Show migration example based on command
    if len(sys.argv) > 1:
        old_cmd = " ".join(["adobe-aep"] + sys.argv[1:])
        new_cmd = " ".join(["adobe", "aep"] + sys.argv[1:])
        console.print(f"[dim]  Old:[/dim] [red]{old_cmd}[/red]")
        console.print(f"[dim]  New:[/dim] [green]{new_cmd}[/green]")
    
    console.print()


# Redirect all commands to AEP app
@legacy_aep_app.callback(invoke_without_command=True)
def legacy_callback(ctx: typer.Context):
    """Legacy adobe-aep command wrapper."""
    show_deprecation_warning()
    
    # If no subcommand, show help
    if not ctx.invoked_subcommand:
        console.print("[cyan]Run 'adobe aep --help' for available commands[/cyan]\n")
        raise typer.Exit(0)


# Mirror AEP commands
from adobe_experience.cli.schema import schema_app
from adobe_experience.cli.auth import auth_app
from adobe_experience.cli.ai import ai_app

legacy_aep_app.add_typer(schema_app, name="schema")
legacy_aep_app.add_typer(auth_app, name="auth")
legacy_aep_app.add_typer(ai_app, name="ai")


@legacy_aep_app.command("init")
def legacy_init():
    """Initialize Adobe Experience Cloud CLI."""
    show_deprecation_warning()
    from adobe_experience.cli.init import setup
    setup()


@legacy_aep_app.command("version")
def legacy_version():
    """Show version information."""
    show_deprecation_warning()
    from adobe_experience import __version__
    console.print(f"[cyan]Adobe Experience Cloud CLI[/cyan] v{__version__}")
    console.print("[dim](Legacy adobe-aep wrapper)[/dim]")


__all__ = ["legacy_aep_app"]
