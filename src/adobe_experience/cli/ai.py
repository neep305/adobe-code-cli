"""AI provider key management commands."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

ai_app = typer.Typer(help="AI provider configuration")
console = Console()


def get_credentials_file() -> Path:
    """Get AI credentials file path."""
    adobe_dir = Path.home() / ".adobe"
    adobe_dir.mkdir(exist_ok=True)
    return adobe_dir / "ai-credentials.json"


def load_credentials() -> dict:
    """Load stored AI credentials."""
    cred_file = get_credentials_file()
    if not cred_file.exists():
        return {}
    
    try:
        return json.loads(cred_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_credentials(credentials: dict) -> None:
    """Save AI credentials."""
    cred_file = get_credentials_file()
    cred_file.write_text(
        json.dumps(credentials, indent=2),
        encoding="utf-8"
    )
    # Set file permissions (Unix/Mac only)
    try:
        cred_file.chmod(0o600)  # Owner read/write only
    except Exception:
        pass


@ai_app.command("set-key")
def set_api_key(
    provider: str = typer.Argument(
        ...,
        help="AI provider (openai or anthropic)"
    ),
    api_key: Optional[str] = typer.Argument(
        None,
        help="API key to store (will prompt if not provided)"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Default model to use with this provider"
    ),
) -> None:
    """Store API key for AI provider.
    
    Examples:
        adobe-aep ai set-key openai
        adobe-aep ai set-key openai sk-xxxxx
        adobe-aep ai set-key anthropic --model claude-3-5-sonnet-20241022
    """
    provider = provider.lower()
    
    if provider not in ["openai", "anthropic"]:
        console.print(f"[red]Error: Unsupported provider '{provider}'[/red]")
        console.print("Supported providers: openai, anthropic")
        raise typer.Exit(1)
    
    # API 키가 제공되지 않았으면 대화형으로 입력받기
    if not api_key:
        console.print(f"\n[bold]Setting up {provider.upper()} API key[/bold]")
        console.print(f"[yellow]Note: Input will be visible. Use direct argument to hide: adobe-aep ai set-key {provider} YOUR_KEY[/yellow]")
        
        # Windows에서 붙여넣기가 작동하도록 일반 input() 사용
        # 보안을 위해 직접 인자로 전달하는 것을 권장
        api_key = Prompt.ask(f"Enter your {provider.upper()} API key")
        
        if not api_key or api_key.strip() == "":
            console.print("[red]Error: API key cannot be empty[/red]")
            raise typer.Exit(1)
    
    # 모델도 설정되지 않았으면 suggested model 사용 (Enter로 자동 적용)
    if not model:
        default_models = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022"
        }
        
        suggested_model = default_models.get(provider, "")
        
        model_input = Prompt.ask(
            "Default model",
            default=suggested_model,
            show_default=True
        )
        
        # Enter를 누르면 suggested model 자동 적용
        model = model_input.strip() if model_input.strip() else suggested_model
    
    # Load existing credentials
    credentials = load_credentials()
    
    # Update credentials
    credentials[provider] = {
        "api_key": api_key.strip(),
        "model": model
    }
    
    # Save
    save_credentials(credentials)
    
    console.print(f"\n[green]✓[/green] API key for [cyan]{provider}[/cyan] saved successfully")
    if model:
        console.print(f"  Default model: [cyan]{model}[/cyan]")
    console.print(f"  Location: [dim]{get_credentials_file()}[/dim]")
    
    # 사용 팁 표시
    console.print(f"\n[dim]Tip: Set this as default provider with:[/dim]")
    console.print(f"  [cyan]adobe-aep ai set-default {provider}[/cyan]")


@ai_app.command("list-keys")
def list_api_keys() -> None:
    """List stored API keys.
    
    Examples:
        adobe-aep ai list-keys
    """
    credentials = load_credentials()
    
    if not credentials:
        console.print("[yellow]No API keys stored[/yellow]")
        console.print("\nTo add a key, run:")
        console.print("  [cyan]adobe-aep ai set-key openai YOUR_API_KEY[/cyan]")
        return
    
    table = Table(title="Stored AI API Keys")
    table.add_column("Provider", style="cyan")
    table.add_column("API Key", style="dim")
    table.add_column("Default Model", style="magenta")
    
    for provider, data in credentials.items():
        # Skip internal keys
        if provider.startswith("_"):
            continue
            
        # Mask key for security
        api_key = data.get("api_key", "")
        if len(api_key) > 20:
            masked_key = f"{api_key[:8]}...{api_key[-4:]}"
        else:
            masked_key = f"{api_key[:4]}...{api_key[-2:]}"
        
        model = data.get("model") or "[dim]not set[/dim]"
        
        table.add_row(provider, masked_key, model)
    
    console.print(table)
    
    # Show default provider if set
    if "_default" in credentials:
        console.print(f"\n[cyan]Default provider:[/cyan] {credentials['_default']}")
    
    console.print(f"\n[dim]Location: {get_credentials_file()}[/dim]")


@ai_app.command("remove-key")
def remove_api_key(
    provider: str = typer.Argument(
        ...,
        help="AI provider to remove (openai or anthropic)"
    ),
) -> None:
    """Remove stored API key.
    
    Examples:
        adobe-aep ai remove-key openai
        adobe-aep ai remove-key anthropic
    """
    provider = provider.lower()
    
    credentials = load_credentials()
    
    if provider not in credentials:
        console.print(f"[yellow]No API key stored for '{provider}'[/yellow]")
        raise typer.Exit(0)
    
    # Remove the key
    del credentials[provider]
    save_credentials(credentials)
    
    console.print(f"[green]✓[/green] API key for [cyan]{provider}[/cyan] removed")


@ai_app.command("set-default")
def set_default_provider(
    provider: str = typer.Argument(
        ...,
        help="Default AI provider to use (openai or anthropic)"
    ),
) -> None:
    """Set default AI provider.
    
    Examples:
        adobe-aep ai set-default openai
        adobe-aep ai set-default anthropic
    """
    provider = provider.lower()
    
    if provider not in ["openai", "anthropic"]:
        console.print(f"[red]Error: Unsupported provider '{provider}'[/red]")
        raise typer.Exit(1)
    
    credentials = load_credentials()
    
    # Check if key exists
    if provider not in credentials:
        console.print(f"[yellow]Warning: No API key stored for '{provider}'[/yellow]")
        console.print(f"Run: [cyan]adobe-aep ai set-key {provider} YOUR_API_KEY[/cyan]")
        raise typer.Exit(1)
    
    # Set default
    credentials["_default"] = provider
    save_credentials(credentials)
    
    console.print(f"[green]✓[/green] Default provider set to [cyan]{provider}[/cyan]")
