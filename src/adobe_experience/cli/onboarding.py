"""Onboarding tutorial CLI commands."""

import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn

from adobe_experience.core.config import (
    OnboardingState,
    TutorialScenario,
    Milestone,
    load_onboarding_state,
    save_onboarding_state,
)
from adobe_experience.i18n import get_i18n, t

console = Console()
onboarding_app = typer.Typer(
    name="onboarding",
    help="Interactive onboarding tutorials",
    rich_markup_mode="rich",
)


@onboarding_app.command("start")
def start_tutorial(
    scenario: str = typer.Option(
        None,
        "--scenario",
        "-s",
        help="Tutorial scenario (basic, data-engineer, marketer, custom)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Practice mode without real API calls",
    ),
    offline: str = typer.Option(
        None,
        "--offline",
        help="Path to offline tutorial package",
    ),
    language: str = typer.Option(
        None,
        "--language",
        "-l",
        help="Language (en, ko)",
    ),
) -> None:
    """Start interactive onboarding tutorial.

    Examples:
        adobe onboarding start
        adobe onboarding start --scenario basic
        adobe onboarding start --dry-run
        adobe onboarding start --language ko
    """
    # Load or create onboarding state
    state = load_onboarding_state()

    # Language selection
    if not language:
        if state.language:
            language = state.language
        else:
            console.print("\n[cyan]🌍 Language / 언어 선택[/cyan]\n")
            language = Prompt.ask(
                "Select language / 언어를 선택하세요",
                choices=["en", "ko"],
                default="en",
            )

    # Initialize i18n
    i18n = get_i18n(language)
    state.language = language

    # Welcome message
    console.print()
    console.print(
        Panel(
            f"[bold cyan]{t('onboarding.welcome', language)}[/bold cyan]\n\n"
            f"{t('help.context_help', language)}",
            border_style="cyan",
            expand=False,
        )
    )
    console.print()

    # Scenario selection
    if not scenario:
        console.print(f"[yellow]{t('onboarding.scenario_select', language)}[/yellow]\n")

        scenarios_table = Table(show_header=False, box=None)
        scenarios_table.add_column("Choice", style="cyan")
        scenarios_table.add_column("Description")

        for sc in TutorialScenario:
            scenarios_table.add_row(
                sc.value,
                t(f"onboarding.scenarios.{sc.value.replace('-', '_')}", language),
            )

        console.print(scenarios_table)
        console.print()

        scenario = Prompt.ask(
            t("onboarding.scenario_select", language),
            choices=[s.value for s in TutorialScenario],
            default="basic",
        )

    state.scenario = TutorialScenario(scenario)

    # Mode selection
    if offline:
        mode = "offline"
        console.print(f"\n[yellow]📦 {t('onboarding.modes.offline', language)}[/yellow]")
    elif dry_run:
        mode = "dry-run"
        console.print(f"\n[yellow]🎓 {t('onboarding.modes.dry_run', language)}[/yellow]")
    else:
        mode = "online"
        console.print(f"\n[green]🌐 {t('onboarding.modes.online', language)}[/green]")

    # Save initial state
    if state.started_at is None:
        from datetime import datetime

        state.started_at = datetime.now()

    save_onboarding_state(state)

    # Start tutorial workflow
    console.print(f"\n[bold green]✓[/bold green] {t('onboarding.messages.step_complete', language)}\n")
    console.print(
        f"[dim]Use [cyan]adobe onboarding status[/cyan] to check progress[/dim]"
    )
    console.print(
        f"[dim]Use [cyan]adobe onboarding resume[/cyan] to continue[/dim]"
    )


@onboarding_app.command("status")
def show_status() -> None:
    """Show onboarding progress and status.

    Examples:
        adobe onboarding status
    """
    state = load_onboarding_state()

    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]adobe onboarding start[/cyan]")
        return

    i18n = get_i18n(state.language)

    # Progress header
    console.print()
    console.print(
        Panel(
            f"[bold]{t('onboarding.welcome', state.language)}[/bold]",
            border_style="cyan",
        )
    )

    # Progress bar
    total_steps = 6  # Basic scenario has 6 steps
    progress_pct = state.get_progress_percentage(total_steps)

    console.print()
    console.print(f"[cyan]{t('onboarding.messages.progress', state.language)}:[/cyan]")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        progress.add_task("", completed=progress_pct, total=100)

    # Steps tree
    console.print()
    tree = Tree(f"[bold]{state.scenario.value.title()} Tutorial[/bold]")

    for step_num in range(1, total_steps + 1):
        if step_num in state.completed_steps:
            status = f"[green]✅ {t('onboarding.status.completed', state.language)}[/green]"
        elif step_num == state.current_step:
            status = f"[yellow]🔄 {t('onboarding.status.in_progress', state.language)}[/yellow]"
        elif step_num in state.skipped_steps:
            status = f"[dim]⚠️ {t('onboarding.status.skipped', state.language)}[/dim]"
        else:
            status = f"[dim]⬜ {t('onboarding.status.not_started', state.language)}[/dim]"

        step_key = ["auth", "ai_provider", "schema", "upload_schema", "dataset", "ingest"][
            step_num - 1
        ]
        step_name = t(f"onboarding.steps.{step_key}", state.language)
        tree.add(f"{step_name} - {status}")

    console.print(tree)

    # Milestones
    if state.milestones_achieved:
        console.print()
        console.print("[bold yellow]🏆 Achievements:[/bold yellow]")
        for milestone in state.milestones_achieved:
            milestone_text = t(f"onboarding.milestones.{milestone.value.replace('-', '_')}", state.language)
            console.print(f"  {milestone_text}")

    console.print()


@onboarding_app.command("resume")
def resume_tutorial() -> None:
    """Resume onboarding tutorial from last checkpoint.

    Examples:
        adobe onboarding resume
    """
    state = load_onboarding_state()

    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]adobe onboarding start[/cyan]")
        return

    console.print(
        f"\n[green]Resuming {state.scenario.value} tutorial at step {state.current_step}...[/green]\n"
    )
    console.print("[dim]Tutorial resume functionality coming soon[/dim]")


@onboarding_app.command("achievements")
def show_achievements() -> None:
    """Show earned achievements and milestones.

    Examples:
        adobe onboarding achievements
    """
    state = load_onboarding_state()
    i18n = get_i18n(state.language)

    console.print()
    console.print("[bold yellow]🏆 Your Achievements[/bold yellow]\n")

    if not state.milestones_achieved:
        console.print("[dim]No achievements yet. Start the tutorial to earn badges![/dim]")
        console.print("Use: [cyan]adobe onboarding start[/cyan]")
        return

    for milestone in state.milestones_achieved:
        milestone_text = t(
            f"onboarding.milestones.{milestone.value.replace('-', '_')}",
            state.language,
        )
        console.print(f"  {milestone_text}")

    console.print()


@onboarding_app.command("reset")
def reset_progress(
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Reset onboarding progress.

    Examples:
        adobe onboarding reset
        adobe onboarding reset --yes
    """
    if not confirm:
        confirm = Confirm.ask("Are you sure you want to reset all progress?", default=False)

    if not confirm:
        console.print("[yellow]Reset cancelled[/yellow]")
        return

    from pathlib import Path

    state_file = Path.home() / ".adobe" / "onboarding_progress.json"
    if state_file.exists():
        state_file.unlink()

    console.print("[green]✓ Onboarding progress reset[/green]")


@onboarding_app.command("ask")
def ask_ai_tutor(
    question: str = typer.Argument(..., help="Your question for the AI tutor"),
) -> None:
    """Ask the AI tutor for help with the tutorial.

    The AI tutor provides context-aware assistance based on your current
    tutorial progress, recent errors, and specific questions.

    Examples:
        adobe onboarding ask "How do I authenticate?"
        adobe onboarding ask "What is XDM schema?"
        adobe onboarding ask "I'm getting an authentication error, what should I do?"
    """
    from adobe_experience.agent.inference import AIInferenceEngine

    # Load current state
    state = load_onboarding_state()

    if not state:
        console.print("[yellow]No tutorial in progress. Start one with:[/yellow]")
        console.print("  [cyan]adobe onboarding start[/cyan]")
        console.print()
        console.print("[dim]Answering your question anyway...[/dim]\n")
        state = OnboardingState(
            scenario=TutorialScenario.BASIC,
            language="en",
        )

    # Get i18n instance for language
    i18n = get_i18n()
    if state.language:
        i18n.change_language(state.language)

    # Display question
    console.print(Panel(
        f"[bold cyan]{t('ai_tutor.ask', state.language)}[/bold cyan]\n\n{question}",
        border_style="cyan",
    ))

    # Prepare context
    context = {
        "scenario": state.scenario.value if state.scenario else "basic",
        "current_step": state.current_step or 0,
        "completed_steps": state.completed_steps or [],
        "language": state.language or "en",
        "milestones": [m.value for m in state.milestones_achieved] if state.milestones_achieved else [],
    }

    # Call AI tutor
    try:
        engine = AIInferenceEngine()

        with console.status(f"[bold blue]{t('ai_tutor.thinking', state.language)}[/bold blue]"):
            answer = asyncio.run(
                engine.answer_tutorial_question(
                    question=question,
                    context=context,
                    language=state.language,
                )
            )

        # Display answer
        console.print()
        console.print(Panel(
            answer,
            title=f"[bold green]{t('ai_tutor.answer', state.language)}[/bold green]",
            border_style="green",
        ))

    except ValueError as e:
        if "No AI provider configured" in str(e):
            console.print(f"\n[red]{t('errors.auth_failed', state.language)}[/red]")
            console.print("[yellow]AI tutor requires an API key. Configure one with:[/yellow]")
            console.print("  [cyan]adobe ai set-key anthropic[/cyan]")
            console.print("  [cyan]adobe ai set-key openai[/cyan]")
        else:
            console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


__all__ = ["onboarding_app"]
