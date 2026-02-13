"""Initialization and setup commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

init_app = typer.Typer(help="Initialize and configure aep Agent")
console = Console()


@init_app.command()
def setup() -> None:
    """Interactive setup wizard for aep credentials.
    
    This will guide you through setting up your Adobe Developer Console
    credentials and create a .env file for configuration.
    
    Examples:
        aep init
    """
    # ASCII art banner
    banner = """

      █████╗ ██████╗  ██████╗ ██████╗ ███████╗     ██████╗ ██████╗ ██████╗ ███████╗
     ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
     ███████║██║  ██║██║   ██║██████╔╝█████╗      ██║     ██║   ██║██║  ██║█████╗  
     ██╔══██║██║  ██║██║   ██║██╔══██╗██╔══╝      ██║     ██║   ██║██║  ██║██╔══╝  
     ██║  ██║██████╔╝╚██████╔╝██████╔╝███████╗    ╚██████╗╚██████╔╝██████╔╝███████╗
     ╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═════╝ ╚══════╝     ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝

           Adobe Experience Cloud Agent
    """
    
    console.print(f"[bold cyan]{banner}[/bold cyan]")
    
    console.print(Panel.fit(
        "[bold blue]Welcome to Adobe Experience Platform CLI Agent![/bold blue]\n\n"
        "This wizard will help you configure your AEP credentials.\n"
        "You'll need OAuth Server-to-Server credentials from Adobe Developer Console.",
        border_style="blue"
    ))
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        console.print("\n[yellow]⚠ .env file already exists[/yellow]")
        if not Confirm.ask("Do you want to overwrite it?", default=False):
            console.print("[yellow]Setup cancelled[/yellow]")
            raise typer.Exit(0)
    
    console.print("\n[bold]Step 1: Adobe Developer Console Setup[/bold]")
    console.print("""
1. Go to https://developer.adobe.com/console
2. Create a new project or select existing one
3. Add 'Experience Platform API' to your project
4. Select 'OAuth Server-to-Server' credential type
5. Add required API permissions:
   - Schema Registry (Read/Write)
   - Catalog Service (Read/Write)
   - Data Ingestion (Read/Write)
   - Sandbox Management (Read)
6. Generate credentials
7. Note your Tenant ID from 'Credentials Details' tab
    """)
    
    if not Confirm.ask("\nHave you completed the Adobe Developer Console setup?", default=False):
        console.print("\n[yellow]Please complete the setup and run this command again[/yellow]")
        console.print("[dim]Guide: https://experienceleague.adobe.com/en/docs/platform-learn/tutorials/platform-api-authentication[/dim]")
        raise typer.Exit(0)
    
    console.print("\n[bold]Step 2: Enter Your Credentials[/bold]")
    console.print("[dim]You can find these in Adobe Developer Console > Your Project > OAuth Server-to-Server[/dim]\n")
    
    # Collect credentials
    client_id = Prompt.ask("Client ID")
    console.print("[yellow]Note: Input will be visible. Use Ctrl+V to paste.[/yellow]")
    client_secret = Prompt.ask("Client Secret")
    org_id = Prompt.ask("Organization ID (format: XXXXX@AdobeOrg)")
    tech_account_id = Prompt.ask("Technical Account ID (format: XXXXX@techacct.adobe.com)")
    
    console.print("\n[bold]Step 3: Sandbox & Tenant Configuration[/bold]")
    console.print("[dim]Tenant ID is required for schema operations[/dim]\n")
    
    sandbox_name = Prompt.ask("Sandbox name", default="prod")
    tenant_id = Prompt.ask(
        "Tenant ID (find in Developer Console under 'Credentials Details')",
        default=""
    )
    container_id = Prompt.ask("Container ID", default="tenant")
    
    console.print("\n[bold]Step 4: AI Configuration (Optional)[/bold]")
    console.print("[dim]For AI-powered schema generation and recommendations[/dim]\n")
    
    use_ai = Confirm.ask("Do you want to enable AI features?", default=True)
    anthropic_key = ""
    openai_key = ""
    
    if use_ai:
        ai_provider = Prompt.ask(
            "Which AI provider do you want to use?",
            choices=["anthropic", "openai", "both", "skip"],
            default="openai"
        )
        
        if ai_provider == "anthropic" or ai_provider == "both":
            console.print("[yellow]Note: Input will be visible. Use Ctrl+V to paste.[/yellow]")
            anthropic_key = Prompt.ask("Anthropic API Key", default="")
        
        if ai_provider == "openai" or ai_provider == "both":
            console.print("[yellow]Note: Input will be visible. Use Ctrl+V to paste.[/yellow]")
            openai_key = Prompt.ask("OpenAI API Key", default="")
        
        if ai_provider != "skip":
            console.print(f"\n[dim]Tip: You can change AI keys later with 'aep ai set-key'[/dim]")
    
    # Create .env file
    env_content = f"""# Adobe Experience Platform Credentials
AEP_CLIENT_ID={client_id}
AEP_CLIENT_SECRET={client_secret}
AEP_ORG_ID={org_id}
AEP_TECHNICAL_ACCOUNT_ID={tech_account_id}
AEP_SANDBOX_NAME={sandbox_name}

# Tenant ID (Required for schema operations)
AEP_TENANT_ID={tenant_id}

# Container ID (Schema Registry)
AEP_CONTAINER_ID={container_id}

# AI Provider Configuration
ANTHROPIC_API_KEY={anthropic_key}
OPENAI_API_KEY={openai_key}
"""
    
    env_path.write_text(env_content, encoding="utf-8")
    
    console.print("\n[bold green]✓ Configuration saved to .env[/bold green]")
    
    # Validation warnings
    if not tenant_id:
        console.print("\n[yellow]⚠ Warning: Tenant ID not provided[/yellow]")
        console.print("[dim]  You won't be able to upload schemas until you add AEP_TENANT_ID to .env[/dim]")
    
    if not anthropic_key and not openai_key and use_ai:
        console.print("\n[yellow]⚠ Warning: No AI API keys configured[/yellow]")
        console.print("[dim]  AI features will be disabled. Run 'aep ai set-key' to add them later[/dim]")
    
    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. Run: [cyan]aep auth test[/cyan] - Test your connection")
    console.print("2. Run: [cyan]aep schema list[/cyan] - List existing schemas")
    console.print("3. Run: [cyan]aep schema create --help[/cyan] - Create new schemas")
    
    if use_ai and (anthropic_key or openai_key):
        console.print("4. Run: [cyan]aep ai list-keys[/cyan] - View AI configuration")
    
    console.print("\n[dim]Tip: Never commit .env file to version control![/dim]")
    console.print("[dim]Tip: Use 'aep ai set-key' to update AI keys anytime[/dim]")
    
    # Update onboarding progress if active
    try:
        from adobe_experience.cli.onboarding import update_onboarding_progress
        from adobe_experience.core.config import Milestone
        
        if update_onboarding_progress("auth", Milestone.FIRST_AUTH):
            console.print("\n[dim]✨ Onboarding progress updated[/dim]")
    except Exception:
        # Silently ignore if onboarding is not active
        pass
