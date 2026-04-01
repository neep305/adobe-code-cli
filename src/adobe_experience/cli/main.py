"""CLI application for Adobe Experience Platform."""

import typer
from rich.console import Console

from adobe_experience.cli.auth import auth_app
from adobe_experience.cli.ai import ai_app
from adobe_experience.cli.schema import schema_app
from adobe_experience.cli.dataset import dataset_app
from adobe_experience.cli.ingest import ingest_app
from adobe_experience.cli.dataflow import dataflow_app
from adobe_experience.cli.segment import segment_app
from adobe_experience.cli.destination import destination_app
from adobe_experience.cli.onboarding import onboarding_app
from adobe_experience.cli.web import web_app

# Create Adobe Experience Platform CLI with flattened structure
app = typer.Typer(
    name="aep",
    help="Adobe Experience Platform CLI - Manage schemas, datasets, and data ingestion",
    add_completion=False,
    rich_markup_mode="rich",
    epilog="""\n\nCommand Categories:\n\n  🔵 Core AEP API Operations\n     Direct Adobe Platform API wrappers\n\n  🟢 AI-Powered Enhancements\n     AI intelligence and automation features\n\n  ⚡ Hybrid Features\n     APIs with progress tracking and AI\n\n\nExample Workflows:\n\n  🔵 aep schema list\n\n  🟢 aep schema create --use-ai --from-sample data.json\n\n  ⚡ aep ingest upload-file data.parquet --batch <id>\n\n\n💡 Tip: Use --use-ai flag with hybrid commands to enable AI\n""",
)

# Register AEP subcommands (flattened structure)
app.add_typer(schema_app, name="schema", help="🔵⚡ XDM schema management")
app.add_typer(dataset_app, name="dataset", help="🔵 Dataset and batch operations")
app.add_typer(ingest_app, name="ingest", help="⚡ Data ingestion with progress")
app.add_typer(dataflow_app, name="dataflow", help="🔵 Flow Service operations")
app.add_typer(segment_app, name="segment", help="🔵 Segment and audience operations")
app.add_typer(destination_app, name="destination", help="🔵 Destination activation operations")
app.add_typer(onboarding_app, name="onboarding", help="🟢 Interactive tutorials")

# Register common commands
app.add_typer(auth_app, name="auth", help="Authentication management")
app.add_typer(ai_app, name="ai", help="🤖 AI-powered features (chat, generate, analyze, config)")
app.add_typer(web_app, name="web", help="🌐 Web UI server management")

console = Console()


@app.command("init")
def init_command() -> None:
    """Initialize Adobe Experience Platform CLI with interactive setup wizard.
    
    Examples:
        aep init
    """
    from adobe_experience.cli.init import setup
    setup()


@app.command()
def version() -> None:
    """Show version information."""
    from adobe_experience import __version__

    console.print(f"[cyan]Adobe Experience Platform CLI[/cyan] v{__version__}")


@app.command()
def tree() -> None:
    """Show complete command hierarchy tree.
    
    Displays all available commands and subcommands in a tree structure
    for easy navigation and discovery.
    
    Examples:
        aep tree
    """
    from rich.tree import Tree
    
    # Create root tree
    root = Tree(
        "[bold cyan]aep[/bold cyan] - Adobe Experience Platform CLI",
        guide_style="cyan"
    )
    
    # Top-level commands
    top_commands = root.add("[bold yellow]Top-level Commands[/bold yellow]")
    top_commands.add("init - Initialize AEP CLI with setup wizard")
    top_commands.add("version - Show version information")
    top_commands.add("tree - Show this command tree")
    
    # Setup & Configuration
    config_group = root.add("[bold green]Setup & Configuration[/bold green]")
    
    auth_node = config_group.add("[cyan]auth[/cyan] - Authentication management")
    auth_node.add("test - Test AEP authentication")
    auth_node.add("status - Check credential status")
    
    ai_config = config_group.add("[cyan]ai[/cyan] - AI-powered features & config")
    
    # AI Features subgroup
    ai_features = ai_config.add("[magenta]Features[/magenta]")
    ai_features.add("chat - Interactive AI assistant")
    
    ai_generate = ai_features.add("generate - Generate test data")
    ai_generate.add("  └─ from-domain - Generate from domain description")
    
    ai_analyze = ai_features.add("analyze - Supervisor-based analysis")
    ai_analyze.add("  └─ run - Run analysis workflow")
    
    ai_features.add("plan - Generate execution plan")
    
    # AI Config subgroup
    ai_config_group = ai_config.add("[magenta]Configuration[/magenta]")
    ai_config_group.add("set-key - Store AI provider API key")
    ai_config_group.add("list-keys - List configured providers")
    ai_config_group.add("remove-key - Remove API key")
    ai_config_group.add("set-default - Set default provider")
    ai_config_group.add("status - Show AI configuration")
    ai_config_group.add("test - Test AI connectivity")
    
    # AEP Resources
    resources = root.add("[bold blue]AEP Resources[/bold blue]")
    
    schema_node = resources.add("[cyan]schema[/cyan] - XDM schema management")
    schema_node.add("create - Create XDM schema")
    schema_node.add("list - List schemas")
    schema_node.add("get - Get schema details")
    schema_node.add("list-fieldgroups - List field groups")
    schema_node.add("get-fieldgroup - Get field group details")
    schema_node.add("upload-and-validate - Upload with validation")
    
    schema_template = schema_node.add("template - Schema templates")
    schema_template.add("  ├─ list - List templates")
    schema_template.add("  ├─ show - Show template")
    schema_template.add("  ├─ save - Save template")
    schema_template.add("  └─ delete - Delete template")
    
    dataset_node = resources.add("[cyan]dataset[/cyan] - Dataset operations")
    dataset_node.add("create - Create dataset")
    dataset_node.add("list - List datasets")
    dataset_node.add("get - Get dataset details")
    dataset_node.add("delete - Delete dataset")
    dataset_node.add("enable-profile - Enable for Profile")
    dataset_node.add("enable-identity - Enable for Identity")
    dataset_node.add("create-batch - Create batch")
    dataset_node.add("batch-status - Get batch status")
    dataset_node.add("list-batches - List batches")
    dataset_node.add("complete-batch - Complete batch")
    dataset_node.add("abort-batch - Abort batch")
    
    segment_node = resources.add("[cyan]segment[/cyan] - Segment operations")
    segment_node.add("list - List segments")
    segment_node.add("get - Get segment details")
    segment_node.add("create - Create segment")
    segment_node.add("update - Update segment")
    segment_node.add("delete - Delete segment")
    segment_node.add("evaluate - Evaluate segment")
    segment_node.add("job - Get segment job")
    segment_node.add("estimate - Estimate segment size")
    segment_node.add("destinations - List destinations")
    segment_node.add("activate - Activate to destination")
    segment_node.add("deactivate - Deactivate from destination")
    
    destination_node = resources.add("[cyan]destination[/cyan] - Destination operations")
    destination_node.add("list - List destinations")
    destination_node.add("get - Get destination details")
    destination_node.add("segments - List segments for destination")
    destination_node.add("instances - List destination instances")
    
    # AEP Operations
    operations = root.add("[bold magenta]AEP Operations[/bold magenta]")
    
    ingest_node = operations.add("[cyan]ingest[/cyan] - Data ingestion")
    ingest_node.add("upload-file - Upload file to batch")
    ingest_node.add("upload-batch - Upload multiple files")
    ingest_node.add("upload-directory - Upload directory")
    ingest_node.add("status - Get batch status")
    
    dataflow_node = operations.add("[cyan]dataflow[/cyan] - Flow Service operations")
    dataflow_node.add("list - List dataflows")
    dataflow_node.add("get - Get dataflow details")
    dataflow_node.add("runs - List dataflow runs")
    dataflow_node.add("failures - List failures")
    dataflow_node.add("connections - List connections")
    dataflow_node.add("health - Check dataflow health")
    dataflow_node.add("ask - AI-powered dataflow Q&A")
    
    # Utilities
    utilities = root.add("[bold yellow]Utilities[/bold yellow]")
    
    onboarding_node = utilities.add("[cyan]onboarding[/cyan] - Interactive tutorials")
    onboarding_node.add("start - Start tutorial")
    onboarding_node.add("status - Show progress")
    onboarding_node.add("manage - Manage progress")
    
    web_node = utilities.add("[cyan]web[/cyan] - Web UI server")
    web_node.add("start - Start web server")
    web_node.add("stop - Stop web server")
    web_node.add("status - Server status")
    web_node.add("logs - View logs")
    web_node.add("open - Open in browser")
    
    console.print("\n")
    console.print(root)
    console.print("\n")
    console.print("[dim]💡 Tip: Use 'aep <command> --help' for detailed information[/dim]")
    console.print("[dim]💡 Use 'aep ai --help' to see all AI features[/dim]")


if __name__ == "__main__":
    app()
