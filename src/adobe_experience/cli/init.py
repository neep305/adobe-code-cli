"""Initialization and setup commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

init_app = typer.Typer(help="Initialize and configure Adobe AEP Agent")
console = Console()


@init_app.command()
def setup() -> None:
    """Interactive setup wizard for Adobe AEP credentials.
    
    This will guide you through setting up your Adobe Developer Console
    credentials and create a .env file for configuration.
    
    Examples:
        adobe-aep init
    """
    # ASCII art banner
    banner = """

      █████╗ ███████╗██████╗      ██████╗██╗     ██╗
     ██╔══██╗██╔════╝██╔══██╗    ██╔════╝██║     ██║
     ███████║█████╗  ██████╔╝    ██║     ██║     ██║
     ██╔══██║██╔══╝  ██╔═══╝     ██║     ██║     ██║
     ██║  ██║███████╗██║         ╚██████╗███████╗██║
     ╚═╝  ╚═╝╚══════╝╚═╝          ╚═════╝╚══════╝╚═╝

           Adobe Experience Platform Agent
    """
    
    console.print(f"[bold red]{banner}[/bold red]")
    
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
    """)
    
    if not Confirm.ask("\nHave you completed the Adobe Developer Console setup?", default=False):
        console.print("\n[yellow]Please complete the setup and run this command again[/yellow]")
        console.print("[dim]Guide: https://experienceleague.adobe.com/en/docs/platform-learn/tutorials/platform-api-authentication[/dim]")
        raise typer.Exit(0)
    
    console.print("\n[bold]Step 2: Enter Your Credentials[/bold]")
    console.print("[dim]You can find these in Adobe Developer Console > Your Project > OAuth Server-to-Server[/dim]\n")
    
    # Collect credentials
    client_id = Prompt.ask("Client ID")
    client_secret = Prompt.ask("Client Secret", password=True)
    org_id = Prompt.ask("Organization ID (format: XXXXX@AdobeOrg)")
    tech_account_id = Prompt.ask("Technical Account ID (format: XXXXX@techacct.adobe.com)")
    
    console.print("\n[bold]Step 3: Sandbox Configuration[/bold]")
    sandbox_name = Prompt.ask("Sandbox name", default="prod")
    
    console.print("\n[bold]Step 4: AI Configuration (Optional)[/bold]")
    console.print("[dim]For AI-powered schema generation and recommendations[/dim]\n")
    
    use_ai = Confirm.ask("Do you want to enable AI features?", default=True)
    anthropic_key = ""
    if use_ai:
        anthropic_key = Prompt.ask("Anthropic API Key", password=True, default="")
    
    # Create .env file
    env_content = f"""# Adobe Experience Platform Credentials
AEP_CLIENT_ID={client_id}
AEP_CLIENT_SECRET={client_secret}
AEP_ORG_ID={org_id}
AEP_TECHNICAL_ACCOUNT_ID={tech_account_id}
AEP_SANDBOX_NAME={sandbox_name}

# AI Provider
ANTHROPIC_API_KEY={anthropic_key}

# Optional: OpenAI (if using as alternative)
# OPENAI_API_KEY=your_openai_api_key
"""
    
    env_path.write_text(env_content, encoding="utf-8")
    
    console.print("\n[bold green]✓ Configuration saved to .env[/bold green]")
    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. Run: [cyan]adobe-aep auth test[/cyan] - Test your connection")
    console.print("2. Run: [cyan]adobe-aep schema list[/cyan] - List existing schemas")
    console.print("3. Run: [cyan]adobe-aep schema create --help[/cyan] - Create new schemas")
    
    console.print("\n[dim]Tip: Never commit .env file to version control![/dim]")
