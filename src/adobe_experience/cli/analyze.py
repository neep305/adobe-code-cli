"""Data analysis commands powered by supervisor graph routing."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from adobe_experience.agent.registry import AgentRegistry
from adobe_experience.agent.supervisor_graph import SupervisorGraphRunner
from adobe_experience.cli.command_metadata import (
    CommandCategory,
    command_metadata,
    register_command_group_metadata,
)

console = Console()
analyze_app = typer.Typer(help="Analyze customer data and generate XDM mapping guidance")

register_command_group_metadata(
    "analyze", CommandCategory.ENHANCED, "Supervisor-driven analysis and schema mapping"
)


@analyze_app.callback()
def analyze_callback() -> None:
    """Analyze command group."""


def _default_output_dir() -> Path:
    base = Path.cwd() / ".adobe-workspace" / "output" / "analysis"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _load_records(file_path: Optional[Path]) -> list[dict]:
    if not file_path:
        return []
    if not file_path.exists():
        raise typer.BadParameter(f"File not found: {file_path}")

    if file_path.suffix.lower() == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []

    if file_path.suffix.lower() == ".csv":
        import csv

        with file_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]

    raise typer.BadParameter("Only .json and .csv are supported for --file in v1")


def _render_markdown(state) -> str:
    lines = [
        "# Analysis Report",
        "",
        f"- Request ID: {state.request_id}",
        f"- Route: {state.route}",
        f"- Confidence: {state.confidence:.2f}",
        f"- Summary: {state.final_summary or 'n/a'}",
        "",
        "## Agents",
    ]
    for name in state.selected_agents:
        lines.append(f"- {name}")

    if state.warnings:
        lines.append("")
        lines.append("## Warnings")
        for warning in state.warnings:
            lines.append(f"- {warning}")

    lines.append("")
    lines.append("## Structured Results")
    for agent_name, result in state.results.items():
        lines.append("")
        lines.append(f"### {agent_name}")
        lines.append(f"- Status: {result.status}")
        lines.append(f"- Confidence: {result.confidence:.2f}")
        lines.append("```json")
        lines.append(json.dumps(result.structured_output, indent=2, ensure_ascii=False))
        lines.append("```")

    return "\n".join(lines)


@command_metadata(CommandCategory.ENHANCED, "Run supervisor-based customer data analysis")
@analyze_app.command("run")
def run_analysis(
    intent: str = typer.Option(
        ...,
        "--intent",
        "-i",
        help=(
            "Natural language description of what you want to analyze. "
            "Examples: 'Analyze customer data quality', "
            "'Generate XDM schema mapping for orders', "
            "'Analyze and create schema for customer profiles'"
        ),
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help=(
            "Path to JSON or CSV file containing sample records. "
            "JSON: array of objects or single object. "
            "CSV: header row + data rows. "
            "Example: test-data/ecommerce/customers.json"
        ),
    ),
    dataset_id: Optional[str] = typer.Option(
        None,
        "--dataset-id",
        help="AEP dataset ID (alternative to --file)",
    ),
    directory: Optional[Path] = typer.Option(
        None,
        "--directory",
        help="Directory path (future use)",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for analysis results (default: ./output/analysis)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed agent execution trace with step-by-step progress",
    ),
) -> None:
    """Run AI-powered data analysis through supervisor routing.
    
    The supervisor analyzes your intent and routes to appropriate agents:
    
      • Analysis route: Data quality profiling and relationship detection
      • Schema route: XDM schema mapping recommendations  
      • Mixed route: Both analysis and schema mapping
    
    Examples:
    
      # Analyze customer data quality
      aep analyze run --intent "Analyze customer data" --file customers.json
      
      # Generate XDM schema recommendations
      aep analyze run --intent "Create XDM schema" --file orders.json --verbose
      
      # Full analysis with schema mapping
      aep analyze run --intent "Analyze and map to XDM" --file data.csv -o output/results
    """
    if file and dataset_id:
        raise typer.BadParameter("Use either --file or --dataset-id, not both")

    out_dir = output_dir or _default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    records = _load_records(file)

    request = {
        "request_id": datetime.utcnow().strftime("req-%Y%m%d%H%M%S"),
        "trace_id": datetime.utcnow().strftime("trace-%Y%m%d%H%M%S"),
        "intent": intent,
        "input_source": "file" if file else ("dataset" if dataset_id else "llm"),
        "payload": {
            "records": records,
            "dataset_id": dataset_id,
            "directory": str(directory) if directory else None,
        },
    }

    if verbose:
        console.print("\n[bold cyan]🚀 Starting Supervisor Analysis[/bold cyan]\n")

    runner = SupervisorGraphRunner(AgentRegistry(), verbose=verbose, console=console)
    state = runner.run(request)

    if verbose:
        console.print("\n[bold green]✅ Analysis Complete[/bold green]\n")

    table = Table(title="Analysis Summary")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Route", str(state.route))
    table.add_row("Agents", ", ".join(state.selected_agents) or "n/a")
    table.add_row("Confidence", f"{state.confidence:.2f}")
    table.add_row("Summary", state.final_summary or "n/a")
    console.print(table)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    json_path = out_dir / f"analysis_{timestamp}.json"
    md_path = out_dir / f"analysis_{timestamp}.md"

    json_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(state), encoding="utf-8")

    console.print(f"[green]Saved JSON:[/green] {json_path}")
    console.print(f"[green]Saved Markdown:[/green] {md_path}")
