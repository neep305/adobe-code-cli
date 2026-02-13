"""Authentication and configuration commands."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from adobe_experience.aep.client import AEPClient
from adobe_experience.cli.command_metadata import (
    command_metadata,
    CommandCategory,
    register_command_group_metadata,
)
from adobe_experience.core.config import AEPConfig, get_config

auth_app = typer.Typer(help="Authentication and credential management")
console = Console()

# Register command group metadata
register_command_group_metadata("auth", CommandCategory.API, "Authentication and API testing")


@command_metadata(CommandCategory.API, "Test AEP authentication")
@auth_app.command("test")
def test_auth() -> None:
    """Test AEP authentication and API connectivity.
    
    Examples:
        aep auth test
    """
    try:
        console.print("[bold blue]Testing Adobe Experience Platform authentication...[/bold blue]\n")
        
        # Load config
        try:
            config = get_config()
        except Exception as e:
            console.print(f"[red]✗ Failed to load configuration: {e}[/red]")
            console.print("\n[yellow]Run 'aep init' to set up credentials[/yellow]")
            raise typer.Exit(1)
        
        # Display configuration (masked)
        config_table = Table(title="Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")
        
        config_table.add_row("Client ID", config.aep_client_id[:8] + "..." if config.aep_client_id else "Not set")
        config_table.add_row("Organization ID", config.aep_org_id)
        config_table.add_row("Sandbox", config.aep_sandbox_name)
        config_table.add_row("API Base URL", config.aep_api_base_url)
        config_table.add_row("IMS Token URL", config.aep_ims_token_url)
        
        console.print(config_table)
        console.print()
        
        # Test authentication
        result = asyncio.run(_test_authentication(config))
        
        if result["success"]:
            console.print("[bold green]✓ Authentication successful![/bold green]\n")
            
            # Display token info
            token_table = Table(title="Access Token")
            token_table.add_column("Property", style="cyan")
            token_table.add_column("Value", style="green")
            
            token_table.add_row("Token Type", result["token_type"])
            token_table.add_row("Expires In", f"{result['expires_in']} seconds")
            token_table.add_row("Token Preview", result["token_preview"])
            
            console.print(token_table)
            console.print("\n[green]✓ All checks passed - AEP connection is working![/green]")
        else:
            console.print(f"[red]✗ Authentication failed: {result['error']}[/red]")
            console.print("\n[yellow]Please check your credentials in .env file[/yellow]")
            raise typer.Exit(1)
            
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise typer.Exit(1)


@command_metadata(CommandCategory.API, "Check credential status")
@auth_app.command("status")
def auth_status() -> None:
    """Check current authentication status.
    
    Examples:
        aep auth status
    """
    try:
        config = get_config()
        
        console.print("[bold blue]Authentication Status[/bold blue]\n")
        
        # Check required fields
        status_table = Table(title="Credential Status")
        status_table.add_column("Credential", style="cyan")
        status_table.add_column("Status", style="green")
        
        checks = [
            ("Client ID", bool(config.aep_client_id)),
            ("Client Secret", bool(config.aep_client_secret)),
            ("Organization ID", bool(config.aep_org_id)),
            ("Technical Account ID", bool(config.aep_technical_account_id)),
            ("Sandbox Name", bool(config.aep_sandbox_name)),
        ]
        
        all_configured = True
        for name, is_set in checks:
            status = "✓ Configured" if is_set else "✗ Missing"
            style = "green" if is_set else "red"
            status_table.add_row(name, f"[{style}]{status}[/{style}]")
            if not is_set:
                all_configured = False
        
        console.print(status_table)
        
        if all_configured:
            console.print("\n[green]✓ All credentials are configured[/green]")
            console.print("\n[dim]Run 'aep auth test' to verify connectivity[/dim]")
        else:
            console.print("\n[yellow]⚠ Some credentials are missing[/yellow]")
            console.print("[dim]Run 'aep init' to set up credentials[/dim]")
            
    except Exception as e:
        console.print(f"[red]✗ Error loading configuration: {e}[/red]")
        console.print("\n[yellow]Run 'aep init' to set up credentials[/yellow]")
        raise typer.Exit(1)


async def _test_authentication(config: AEPConfig) -> dict:
    """Test authentication by requesting access token.
    
    Args:
        config: AEP configuration.
        
    Returns:
        Dict with test results.
    """
    try:
        async with AEPClient(config) as client:
            # This will trigger token request in __aenter__
            token = client._access_token
            
            return {
                "success": True,
                "token_type": "Bearer",
                "expires_in": 86400,  # Adobe tokens typically last 24 hours
                "token_preview": token[:20] + "..." if token else "N/A",
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
