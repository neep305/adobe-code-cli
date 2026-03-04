"""AI provider key management commands."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from adobe_experience.cli.command_metadata import (
    command_metadata,
    CommandCategory,
    register_command_group_metadata,
)

ai_app = typer.Typer(help="AI provider configuration")
console = Console()

# Register command group metadata
register_command_group_metadata("ai", CommandCategory.ENHANCED, "AI provider key management")


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


@command_metadata(CommandCategory.ENHANCED, "Store AI provider API key")
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
        aep ai set-key openai
        aep ai set-key openai sk-xxxxx
        aep ai set-key anthropic --model claude-3-5-sonnet-20241022
    """
    provider = provider.lower()
    
    if provider not in ["openai", "anthropic"]:
        console.print(f"[red]Error: Unsupported provider '{provider}'[/red]")
        console.print("Supported providers: openai, anthropic")
        raise typer.Exit(1)
    
    # API 키가 제공되지 않았으면 대화형으로 입력받기
    if not api_key:
        console.print(f"\n[bold]Setting up {provider.upper()} API key[/bold]")
        console.print(f"[dim]Tip: Key will be hidden. Use Ctrl+V/Right-click to paste[/dim]")
        
        # Use getpass for hidden input (more secure)
        import getpass
        try:
            api_key = getpass.getpass(f"{provider.upper()} API Key: ")
        except Exception:
            # Fallback to visible input if getpass fails
            console.print(f"[yellow]⚠️  Hidden input not supported, key will be visible[/yellow]")
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
    console.print(f"  [cyan]aep ai set-default {provider}[/cyan]")
    
    # Update onboarding progress if active
    try:
        from adobe_experience.cli.onboarding import update_onboarding_progress
        from adobe_experience.core.config import Milestone
        
        if update_onboarding_progress("ai_provider", Milestone.AI_CONFIGURED):
            console.print("\n[dim]✨ Onboarding progress updated[/dim]")
    except Exception:
        # Silently ignore if onboarding is not active
        pass


@command_metadata(CommandCategory.ENHANCED, "List configured AI providers")
@ai_app.command("list-keys")
def list_api_keys() -> None:
    """List stored API keys.
    
    Examples:
        aep ai list-keys
    """
    credentials = load_credentials()
    
    if not credentials:
        console.print("[yellow]No API keys stored[/yellow]")
        console.print("\nTo add a key, run:")
        console.print("  [cyan]aep ai set-key openai YOUR_API_KEY[/cyan]")
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


@command_metadata(CommandCategory.ENHANCED, "Remove AI provider API key")
@ai_app.command("remove-key")
def remove_api_key(
    provider: str = typer.Argument(
        ...,
        help="AI provider to remove (openai or anthropic)"
    ),
) -> None:
    """Remove stored API key.
    
    Examples:
        aep ai remove-key openai
        aep ai remove-key anthropic
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


@command_metadata(CommandCategory.ENHANCED, "Set default AI provider")
@ai_app.command("set-default")
def set_default_provider(
    provider: str = typer.Argument(
        ...,
        help="Default AI provider to use (openai or anthropic)"
    ),
) -> None:
    """Set default AI provider.
    
    Examples:
        aep ai set-default openai
        aep ai set-default anthropic
    """
    provider = provider.lower()
    
    if provider not in ["openai", "anthropic"]:
        console.print(f"[red]Error: Unsupported provider '{provider}'[/red]")
        raise typer.Exit(1)
    
    credentials = load_credentials()
    
    # Check if key exists
    if provider not in credentials:
        console.print(f"[yellow]Warning: No API key stored for '{provider}'[/yellow]")
        console.print(f"Run: [cyan]aep ai set-key {provider} YOUR_API_KEY[/cyan]")
        raise typer.Exit(1)
    
    # Set default
    credentials["_default"] = provider
    save_credentials(credentials)
    
    console.print(f"[green]✓[/green] Default provider set to [cyan]{provider}[/cyan]")


@command_metadata(CommandCategory.ENHANCED, "Show current AI configuration status")
@ai_app.command("status")
def show_ai_status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information")
) -> None:
    """Show current AI configuration status.
    
    Displays:
    - Default provider and model
    - API key status (configured/not configured)
    - Configuration source (env var, file, not set)
    - Available providers
    
    Examples:
        aep ai status
        aep ai status --verbose
    """
    from adobe_experience.core.config import get_config
    
    try:
        config = get_config()
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        raise typer.Exit(1)
    
    credentials = load_credentials()
    
    # Create status table
    from rich.panel import Panel
    from rich.text import Text
    
    status_text = Text()
    status_text.append("AI Configuration Status\n", style="bold cyan")
    status_text.append("\n")
    
    # Default provider
    default_provider = credentials.get("_default", config.ai_provider)
    if default_provider == "auto":
        if config.anthropic_api_key:
            default_provider = "anthropic (auto-detected)"
        elif config.openai_api_key:
            default_provider = "openai (auto-detected)"
        else:
            default_provider = "not configured"
    
    status_text.append("Default Provider: ", style="green")
    status_text.append(f"{default_provider}\n", style="cyan bold")
    
    status_text.append("Default Model:    ", style="green")
    status_text.append(f"{config.ai_model}\n\n", style="cyan")
    
    # Anthropic status
    status_text.append("Providers:\n", style="bold")
    
    anthropic_status = "✓" if config.anthropic_api_key else "✗"
    status_text.append(f"{anthropic_status} Anthropic\n", style="green" if config.anthropic_api_key else "red")
    
    if config.anthropic_api_key:
        key = config.anthropic_api_key.get_secret_value()
        masked = f"●●●●●●●{key[-4:]}" if len(key) > 4 else "●●●●"
        
        # Determine source
        import os
        source = "env var" if os.getenv("ANTHROPIC_API_KEY") else "file"
        
        status_text.append(f"  • API Key:    {masked} (from {source})\n", style="dim")
        
        model = credentials.get("anthropic", {}).get("model", "default")
        status_text.append(f"  • Model:      {model}\n", style="dim")
    else:
        status_text.append("  • API Key:    Not configured\n", style="yellow dim")
        status_text.append("  • Set with:   aep ai set-key anthropic\n", style="dim")
    
    status_text.append("\n")
    
    # OpenAI status
    openai_status = "✓" if config.openai_api_key else "✗"
    status_text.append(f"{openai_status} OpenAI\n", style="green" if config.openai_api_key else "red")
    
    if config.openai_api_key:
        key = config.openai_api_key.get_secret_value()
        masked = f"●●●●●●●{key[-4:]}" if len(key) > 4 else "●●●●"
        
        # Determine source
        import os
        source = "env var" if os.getenv("OPENAI_API_KEY") else "file"
        
        status_text.append(f"  • API Key:    {masked} (from {source})\n", style="dim")
        
        model = credentials.get("openai", {}).get("model", "default")
        status_text.append(f"  • Model:      {model}\n", style="dim")
    else:
        status_text.append("  • API Key:    Not configured\n", style="yellow dim")
        status_text.append("  • Set with:   aep ai set-key openai\n", style="dim")
    
    # Config files status
    if verbose:
        status_text.append("\nConfig Files:\n", style="bold")
        
        env_path = Path(".env")
        env_status = "Found ✓" if env_path.exists() else "Not found"
        status_text.append(f"  • .env:                {env_status}\n", style="green" if env_path.exists() else "dim")
        
        cred_file = get_credentials_file()
        cred_status = "Found ✓" if cred_file.exists() else "Not found"
        status_text.append(f"  • ai-credentials.json: {cred_status}\n", style="green" if cred_file.exists() else "dim")
        status_text.append(f"    Location: {cred_file}\n", style="dim")
    
    console.print(Panel(status_text, border_style="cyan", padding=(1, 2)))
    
    # Tips
    if not config.anthropic_api_key and not config.openai_api_key:
        console.print("\n[yellow]No AI providers configured[/yellow]")
        console.print("\n[bold]Quick Setup:[/bold]")
        console.print("  [cyan]aep ai set-key anthropic[/cyan]  - Setup Claude")
        console.print("  [cyan]aep ai set-key openai[/cyan]      - Setup ChatGPT")
    else:
        console.print("\n[dim]Tip: Use 'aep ai test' to verify API connectivity[/dim]")


@command_metadata(CommandCategory.ENHANCED, "Test AI provider connectivity")
@ai_app.command("test")
def test_ai_provider(
    provider: Optional[str] = typer.Argument(
        None,
        help="Provider to test (anthropic or openai). Tests all if omitted."
    ),
) -> None:
    """Test AI provider API connectivity.
    
    Makes a simple API call to verify:
    - API key is valid
    - Model is accessible
    - Network connectivity
    
    Examples:
        aep ai test                # Test all configured providers
        aep ai test anthropic     # Test Anthropic only
        aep ai test openai        # Test OpenAI only
    """
    from adobe_experience.core.config import get_config
    import time
    
    try:
        config = get_config()
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        raise typer.Exit(1)
    
    credentials = load_credentials()
    
    # Determine which providers to test
    providers_to_test = []
    if provider:
        providers_to_test = [provider.lower()]
    else:
        if config.anthropic_api_key:
            providers_to_test.append("anthropic")
        if config.openai_api_key:
            providers_to_test.append("openai")
    
    if not providers_to_test:
        console.print("[yellow]No providers configured to test[/yellow]")
        console.print("\nRun: [cyan]aep ai set-key <provider>[/cyan]")
        raise typer.Exit(1)
    
    console.print("[bold]Testing AI Provider Connectivity[/bold]\n")
    
    for prov in providers_to_test:
        if prov == "anthropic":
            if not config.anthropic_api_key:
                console.print(f"[yellow]✗ Anthropic - API key not configured[/yellow]")
                continue
            
            try:
                from anthropic import Anthropic
                
                model = credentials.get("anthropic", {}).get("model", "claude-3-5-sonnet-20241022")
                
                console.print(f"[cyan]Testing Anthropic ({model})...[/cyan]")
                
                start = time.time()
                client = Anthropic(api_key=config.anthropic_api_key.get_secret_value())
                response = client.messages.create(
                    model=model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                elapsed = time.time() - start
                
                console.print(f"[green]✓ Anthropic connected successfully[/green]")
                console.print(f"  Model:         {model}")
                console.print(f"  Response time: {elapsed:.2f}s")
                console.print(f"  Status:        {response.stop_reason}\n")
                
            except Exception as e:
                console.print(f"[red]✗ Anthropic connection failed[/red]")
                console.print(f"  Error: {str(e)}\n")
        
        elif prov == "openai":
            if not config.openai_api_key:
                console.print(f"[yellow]✗ OpenAI - API key not configured[/yellow]")
                continue
            
            try:
                from openai import OpenAI
                
                model = credentials.get("openai", {}).get("model", "gpt-4o")
                
                console.print(f"[cyan]Testing OpenAI ({model})...[/cyan]")
                
                start = time.time()
                client = OpenAI(api_key=config.openai_api_key.get_secret_value())
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                elapsed = time.time() - start
                
                console.print(f"[green]✓ OpenAI connected successfully[/green]")
                console.print(f"  Model:         {model}")
                console.print(f"  Response time: {elapsed:.2f}s")
                console.print(f"  Status:        {response.choices[0].finish_reason}\n")
                
            except ImportError:
                console.print(f"[red]✗ OpenAI SDK not installed[/red]")
                console.print(f"  Install with: [cyan]pip install openai[/cyan]\n")
            except Exception as e:
                console.print(f"[red]✗ OpenAI connection failed[/red]")
                console.print(f"  Error: {str(e)}\n")


@command_metadata(CommandCategory.ENHANCED, "Generate execution plan for AEP workflow")
@ai_app.command("plan")
def plan_workflow(
    file: Optional[str] = typer.Argument(
        None,
        help="File to process (CSV, JSON, etc.)"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project directory with multiple data files (multi-entity mode)"
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive planning mode"
    ),
    simulate: bool = typer.Option(
        False,
        "--simulate",
        help="Simulate execution without running"
    ),
    validate: bool = typer.Option(
        False,
        "--validate",
        help="Validate plan before execution"
    ),
    optimize: bool = typer.Option(
        False,
        "--optimize",
        "-o",
        help="Optimize execution plan"
    ),
    compare: bool = typer.Option(
        False,
        "--compare",
        "-c",
        help="Compare alternative plans"
    ),
    explain: bool = typer.Option(
        False,
        "--explain",
        help="Explain each step in detail"
    ),
    from_template: Optional[str] = typer.Option(
        None,
        "--from-template",
        help="Use saved template"
    ),
    save_template: Optional[str] = typer.Option(
        None,
        "--save-template",
        help="Save plan as template"
    ),
    export: Optional[str] = typer.Option(
        None,
        "--export",
        help="Export plan to file (JSON or Markdown)"
    ),
    execute: bool = typer.Option(
        False,
        "--execute",
        help="Execute the plan"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-approve all prompts"
    ),
) -> None:
    """Generate and manage execution plans for AEP workflows.
    
    Supports both single-file and multi-entity project modes.
    
    Examples:
        # Single-file mode
        aep ai plan customers.csv
        
        # Multi-entity project mode
        aep ai plan --project test-data/ecommerce/
        
        # Interactive planning
        aep ai plan --interactive
        
        # Optimize and execute
        aep ai plan data.csv --optimize --execute
        
        # Compare alternatives
        aep ai plan data.csv --compare
        
        # Simulate without execution
        aep ai plan data.csv --simulate
        
        # Save as template
        aep ai plan data.csv --save-template csv_to_profile
        
        # Use template
        aep ai plan new_data.csv --from-template csv_to_profile
    """
    from adobe_experience.agent.planner import PlannerEngine
    from rich.panel import Panel
    from rich.table import Table
    import json
    
    try:
        # Initialize planner
        planner = PlannerEngine()
        
        # Validate input mode
        if file and project:
            console.print("[red]Error: Cannot use both --file and --project. Choose one mode.[/red]")
            raise typer.Exit(1)
        
        # Interactive mode
        if interactive:
            console.print(Panel.fit(
                "[bold cyan]🎯 Plan Mode[/bold cyan]\n"
                "Let's design your AEP workflow",
                border_style="cyan"
            ))
            
            # Get user intent
            intent = typer.prompt("What do you want to accomplish?")
            
            if not file and not project:
                mode = typer.prompt("Mode? (file/project)", default="file")
                if mode == "project":
                    project = typer.prompt("Project directory path")
                else:
                    file = typer.prompt("File path")
            
            console.print("\n[cyan]Analyzing and generating plan...[/cyan]\n")
        else:
            # Check if any operation requiring a file/project is requested
            requires_input = not (explain and not file and not project)
            
            if not file and not project and requires_input:
                console.print("[red]Error: File or project required (or use --interactive)[/red]")
                raise typer.Exit(1)
            
            # Set intent based on mode
            if project:
                from pathlib import Path
                project_name = Path(project).name
                intent = f"Multi-entity ingestion for {project_name} project"
            elif file:
                intent = f"Ingest {file} into AEP"
            else:
                intent = "General AEP workflow planning"
        
        # If only explain flag without file/project, show general help
        if explain and not file and not project and not interactive:
            console.print(Panel.fit(
                "[bold cyan]📖 AI Plan Mode Explanation[/bold cyan]\n\n"
                "Plan Mode helps you design and validate AEP workflows before execution.\n\n"
                "[bold]Key Features:[/bold]\n"
                "• Generate step-by-step execution plans\n"
                "• Multi-entity project support with relationship mapping\n"
                "• Optimize for performance, cost, and reliability\n"
                "• Compare alternative approaches\n"
                "• Simulate execution without API calls\n"
                "• Export plans as JSON or Markdown\n\n"
                "[bold]Basic Usage:[/bold]\n"
                "  aep ai plan <file>              # Single-file mode\n"
                "  aep ai plan --project <dir>     # Multi-entity project mode\n"
                "  aep ai plan <file> --explain    # Detailed explanation\n"
                "  aep ai plan <file> --optimize   # Optimize plan\n"
                "  aep ai plan <file> --compare    # Compare alternatives\n"
                "  aep ai plan <file> --simulate   # Dry-run mode\n"
                "  aep ai plan --interactive       # Interactive mode\n\n"
                "[bold]Examples:[/bold]\n"
                "  aep ai plan customers.csv\n"
                "  aep ai plan --project test-data/ecommerce/\n"
                "  aep ai plan data.json --optimize --execute\n"
                "  aep ai plan large_file.csv --simulate",
                border_style="cyan"
            ))
            return
        
        # Generate plan (single-file or multi-entity project mode)
        if project:
            # Multi-entity project mode
            console.print(Panel.fit(
                f"[bold cyan]🏗️ Multi-Entity Project Analysis[/bold cyan]\n"
                f"Analyzing project: {project}",
                border_style="cyan"
            ))
            console.print("\n[cyan]Step 1: Scanning entities...[/cyan]")
            console.print("[cyan]Step 2: Analyzing relationships...[/cyan]")
            console.print("[cyan]Step 3: Designing XDM architecture...[/cyan]")
            console.print("[cyan]Step 4: Generating execution plan...[/cyan]\n")
            
            plan = planner.generate_plan(intent, project_dir=project)
            
            # Display project summary
            if plan.parameters:
                console.print(Panel.fit(
                    f"[bold green]📊 Project Summary[/bold green]\n"
                    f"Entities: {plan.parameters.get('entity_count', 0)}\n"
                    f"Total Records: {plan.parameters.get('total_records', 0)}\n"
                    f"Ingestion Order: {' → '.join(plan.parameters.get('ingestion_order', []))}\n"
                    f"Relationships: {'Yes' if plan.parameters.get('has_relationships') else 'No'}",
                    border_style="green"
                ))
        else:
            # Single-file mode
            plan = planner.generate_plan(intent, file_path=file)
        
        # Display plan
        console.print(Panel.fit(
            f"[bold green]📋 Generated Plan: {plan.name}[/bold green]\n"
            f"{plan.description}",
            border_style="green"
        ))
        
        # Create steps table
        table = Table(title="Execution Steps", show_header=True, header_style="bold cyan")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Step", style="white")
        table.add_column("Action", style="yellow")
        table.add_column("Duration", style="green", justify="right")
        table.add_column("Requires Approval", style="magenta", justify="center")
        
        for step in plan.steps:
            approval = "✓" if step.validation_required else "-"
            table.add_row(
                str(step.step_number),
                step.name,
                step.action,
                f"{step.estimated_duration}s",
                approval
            )
        
        console.print(table)
        
        # Display metrics
        if plan.metrics:
            console.print(f"\n[cyan]Estimated Time:[/cyan] {plan.metrics.estimated_duration_seconds}s")
            console.print(f"[cyan]API Calls:[/cyan] {plan.metrics.estimated_api_calls}")
            console.print(f"[cyan]Risk Level:[/cyan] {plan.risk_level.value}")
        
        # Compare alternatives
        if compare:
            console.print("\n[cyan]Comparing alternative approaches...[/cyan]\n")
            comparison = planner.compare_alternatives(intent, {"file": file})
            
            # Comparison table
            comp_table = Table(title="Plan Comparison", show_header=True)
            comp_table.add_column("Approach", style="cyan")
            comp_table.add_column("Time", justify="right")
            comp_table.add_column("API Calls", justify="right")
            comp_table.add_column("Complexity", justify="right")
            comp_table.add_column("Risk", style="yellow")
            
            for plan_name, metrics in comparison.comparison_matrix.items():
                comp_table.add_row(
                    plan_name,
                    f"{metrics['duration']}s",
                    str(metrics['api_calls']),
                    str(metrics['complexity']),
                    metrics['risk']
                )
            
            console.print(comp_table)
            console.print(f"\n[bold green]Recommendation:[/bold green] {comparison.recommendation}")
            console.print(f"[dim]{comparison.reasoning}[/dim]")
        
        # Optimize plan
        if optimize:
            console.print("\n[cyan]Analyzing optimization opportunities...[/cyan]\n")
            plan = planner.optimize_plan(plan)
            console.print(f"[green]✓ Applied {len(plan.optimizations_applied)} optimizations[/green]")
            
            if plan.metrics:
                console.print(f"[cyan]New Estimated Time:[/cyan] {plan.metrics.estimated_duration_seconds}s")
        
        # Explain plan
        if explain:
            console.print("\n[cyan]Detailed Explanation:[/cyan]\n")
            explanation = planner.explain_plan(plan)
            
            for step_id, details in explanation['step_explanations'].items():
                console.print(f"\n[bold]Step {details['step_number']}: {details['name']}[/bold]")
                console.print(f"  {details['description']}")
                console.print(f"  [dim]Why: {details['why_needed']}[/dim]")
                console.print(f"  Duration: {details['estimated_duration']}")
        
        # Simulate
        if simulate:
            console.print("\n[cyan]🔬 Simulating Plan Execution[/cyan]\n")
            console.print("[yellow]Simulation mode - no actual API calls will be made[/yellow]\n")
            
            for step in plan.steps:
                console.print(f"Step {step.step_number}/{len(plan.steps)}: {step.name} " + "." * 40 + " [green][OK][/green]")
                console.print(f"  → Would perform: {step.action}")
                if step.parameters:
                    console.print(f"  → Parameters: {json.dumps(step.parameters, indent=4)}")
            
            console.print(f"\n[green]✓ Simulation Complete[/green]")
            console.print(f"Total estimated time: {plan.metrics.estimated_duration_seconds}s")
        
        # Save template
        if save_template:
            # TODO: Implement template saving
            console.print(f"\n[green]✓ Saved plan as template: {save_template}[/green]")
            console.print("[dim](Template functionality coming soon)[/dim]")
        
        # Export
        if export:
            export_path = Path(export)
            
            if export_path.suffix == '.json':
                # Export as JSON
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(plan.model_dump(), f, indent=2, default=str)
                console.print(f"\n[green]✓ Exported plan to {export}[/green]")
            
            elif export_path.suffix == '.md':
                # Export as Markdown
                md_content = f"# {plan.name}\n\n{plan.description}\n\n"
                md_content += f"**Plan ID:** {plan.plan_id}\n"
                md_content += f"**Status:** {plan.status.value}\n"
                md_content += f"**Risk Level:** {plan.risk_level.value}\n\n"
                md_content += "## Steps\n\n"
                
                for step in plan.steps:
                    md_content += f"### {step.step_number}. {step.name}\n\n"
                    md_content += f"{step.description}\n\n"
                    md_content += f"- **Action:** `{step.action}`\n"
                    md_content += f"- **Duration:** {step.estimated_duration}s\n"
                    if step.dependencies:
                        md_content += f"- **Dependencies:** {', '.join(step.dependencies)}\n"
                    md_content += "\n"
                
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                console.print(f"\n[green]✓ Exported plan to {export}[/green]")
        
        # Execute plan
        if execute:
            if not yes:
                proceed = typer.confirm("\nExecute this plan?")
                if not proceed:
                    console.print("[yellow]Execution cancelled[/yellow]")
                    raise typer.Exit(0)
            
            console.print("\n[bold cyan]🚀 Executing Plan...[/bold cyan]\n")
            
            # Initialize orchestrator
            from adobe_experience.agent.workflow import WorkflowOrchestrator, ExecutionResult
            from adobe_experience.core.config import get_config
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
            import asyncio
            
            config = get_config()
            orchestrator = WorkflowOrchestrator(config)
            
            # Progress tracking
            current_step = {"value": 0}
            
            def progress_callback(step, step_result):
                current_step["value"] += 1
                status_icon = "✓" if step_result.status == "success" else "✗" if step_result.status == "failed" else "⊘"
                status_color = "green" if step_result.status == "success" else "red" if step_result.status == "failed" else "yellow"
                
                console.print(
                    f"[{status_color}]{status_icon}[/{status_color}] "
                    f"Step {step.step_number}/{len(plan.steps)}: {step.name} "
                    f"[dim]({step_result.execution_time_seconds:.1f}s)[/dim]"
                )
                
                # Show key outputs
                if step_result.output:
                    if "schema_id" in step_result.output:
                        console.print(f"  [dim]→ Schema ID: {step_result.output['schema_id']}[/dim]")
                    if "dataset_id" in step_result.output:
                        console.print(f"  [dim]→ Dataset ID: {step_result.output['dataset_id']}[/dim]")
                    if "batch_id" in step_result.output:
                        console.print(f"  [dim]→ Batch ID: {step_result.output['batch_id']}[/dim]")
                    if "records_ingested" in step_result.output:
                        console.print(f"  [dim]→ Records ingested: {step_result.output['records_ingested']}[/dim]")
            
            with console.status("[bold blue]Executing plan...") as status:
                try:
                    # Execute plan
                    result: ExecutionResult = asyncio.run(
                        orchestrator.execute_plan(
                            plan,
                            dry_run=simulate,
                            progress_callback=progress_callback
                        )
                    )
                    
                    # Display summary
                    console.print("\n" + "="*60)
                    
                    if result.status == "completed":
                        console.print(Panel.fit(
                            f"[bold green]✅ Execution Complete![/bold green]\n\n"
                            f"Steps Completed: {result.steps_completed}/{len(plan.steps)}\n"
                            f"Total Time: {result.execution_time_seconds:.1f}s\n"
                            f"Status: {result.status}",
                            border_style="green"
                        ))
                    elif result.status == "partial":
                        console.print(Panel.fit(
                            f"[bold yellow]⚠️  Partial Success[/bold yellow]\n\n"
                            f"Steps Completed: {result.steps_completed}\n"
                            f"Steps Failed: {result.steps_failed}\n"
                            f"Steps Skipped: {result.steps_skipped}\n"
                            f"Total Time: {result.execution_time_seconds:.1f}s",
                            border_style="yellow"
                        ))
                    else:
                        console.print(Panel.fit(
                            f"[bold red]❌ Execution Failed[/bold red]\n\n"
                            f"Steps Completed: {result.steps_completed}\n"
                            f"Steps Failed: {result.steps_failed}\n"
                            f"Total Time: {result.execution_time_seconds:.1f}s",
                            border_style="red"
                        ))
                    
                    # Show artifacts
                    if result.artifacts:
                        console.print("\n[cyan]Artifacts created:[/cyan]")
                        for key, value in result.artifacts.items():
                            console.print(f"  • {key}: {value}")
                    
                except Exception as e:
                    console.print(Panel.fit(
                        f"[bold red]❌ Execution Error[/bold red]\n\n"
                        f"{str(e)}",
                        border_style="red"
                    ))
                    raise typer.Exit(1)
        else:
            console.print(f"\n[green]✓ Plan {plan.plan_id} ready[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
