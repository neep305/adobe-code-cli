"""CLI application for Adobe Experience Platform."""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from adobe_experience.aep.client import AEPClient
from adobe_experience.agent.inference import AIInferenceEngine, SchemaGenerationRequest
from adobe_experience.cli.auth import auth_app
from adobe_experience.cli.ai import ai_app
from adobe_experience.cli.schema import schema_app
from adobe_experience.cli.dataset import dataset_app
from adobe_experience.cli.ingest import ingest_app
from adobe_experience.cli.dataflow import dataflow_app
from adobe_experience.cli.onboarding import onboarding_app
from adobe_experience.core.config import get_config
from adobe_experience.schema.xdm import XDMSchemaAnalyzer, XDMSchemaRegistry

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
app.add_typer(onboarding_app, name="onboarding", help="🟢 Interactive tutorials")

# Register common commands
app.add_typer(auth_app, name="auth", help="Authentication management")
app.add_typer(ai_app, name="ai", help="AI provider configuration")

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


if __name__ == "__main__":
    app()
