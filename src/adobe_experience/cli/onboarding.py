"""Onboarding tutorial CLI commands."""

import asyncio
import json
from pathlib import Path
from typing import Dict, Set, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn

from adobe_experience.cli.command_metadata import (
    command_metadata,
    CommandCategory,
    register_command_group_metadata,
)
from adobe_experience.core.config import (
    OnboardingState,
    TutorialScenario,
    TutorialMode,
    Milestone,
    load_onboarding_state,
    save_onboarding_state,
    load_qa_cache,
    save_qa_cache,
)
from adobe_experience.i18n import get_i18n, t

console = Console()
onboarding_app = typer.Typer(
    name="onboarding",
    help="Interactive onboarding tutorials",
)

# Register command group metadata
register_command_group_metadata("onboarding", CommandCategory.ENHANCED, "Interactive AI-powered tutorials")


def detect_completed_steps(scenario: Optional[TutorialScenario] = None) -> Dict[str, Milestone]:
    """Auto-detect which onboarding steps are already completed based on system state.
    
    Checks:
    - .env file exists with required AEP credentials → auth step
    - ~/.adobe/ai-credentials.json exists with valid API keys → ai_provider step
    
    Args:
        scenario: Tutorial scenario to check steps for. If None, checks all common steps.
    
    Returns:
        Dict mapping step keys to their associated milestones
    """
    completed = {}
    
    # Check AEP authentication (.env file)
    env_path = Path(".env")
    if env_path.exists():
        try:
            env_content = env_path.read_text(encoding="utf-8")
            # Check for required AEP credentials
            required_fields = [
                "AEP_CLIENT_ID",
                "AEP_CLIENT_SECRET",
                "AEP_ORG_ID",
                "AEP_TECHNICAL_ACCOUNT_ID"
            ]
            
            has_all_fields = all(
                field in env_content and f"{field}=" in env_content
                for field in required_fields
            )
            
            # Check that fields have actual values (not empty)
            if has_all_fields:
                has_values = True
                for field in required_fields:
                    # Find the line with this field
                    for line in env_content.split("\n"):
                        if line.strip().startswith(field + "="):
                            value = line.split("=", 1)[1].strip()
                            if not value or value == "":
                                has_values = False
                                break
                    if not has_values:
                        break
                
                if has_values:
                    completed["auth"] = Milestone.FIRST_AUTH
        except Exception:
            pass
    
    # Check AI provider configuration
    ai_creds_file = Path.home() / ".adobe" / "ai-credentials.json"
    if ai_creds_file.exists():
        try:
            creds = json.loads(ai_creds_file.read_text(encoding="utf-8"))
            # Check if at least one provider has an API key
            has_api_key = False
            
            if "openai" in creds and isinstance(creds["openai"], dict):
                api_key = creds["openai"].get("api_key", "")
                if api_key and api_key.strip():
                    has_api_key = True
            
            if "anthropic" in creds and isinstance(creds["anthropic"], dict):
                api_key = creds["anthropic"].get("api_key", "")
                if api_key and api_key.strip():
                    has_api_key = True
            
            if has_api_key:
                completed["ai_provider"] = Milestone.AI_CONFIGURED
        except Exception:
            pass
    
    return completed


def update_onboarding_progress(step_key: str, milestone: Optional[Milestone] = None) -> bool:
    """Update onboarding progress when a step is completed outside the tutorial flow.
    
    Args:
        step_key: The step key (e.g., 'auth', 'ai_provider')
        milestone: Optional milestone to award
    
    Returns:
        True if state was updated, False if no onboarding in progress
    """
    state = load_onboarding_state()
    
    # Only update if onboarding is active
    if not state.scenario:
        return False
    
    # Get steps for current scenario
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    
    # Find step number by key
    step_num = None
    for idx, step_info in enumerate(steps, start=1):
        if step_info["key"] == step_key:
            step_num = idx
            break
    
    if step_num is None:
        return False
    
    # Mark step as completed if not already
    if step_num not in state.completed_steps:
        state.completed_steps.append(step_num)
        state.completed_steps.sort()
    
    # Award milestone if provided
    if milestone and milestone not in state.milestones_achieved:
        state.milestones_achieved.append(milestone)
    
    # Save state
    return state.save()


# Tutorial step definitions
TUTORIAL_STEPS = {
    "basic": [
        {
            "key": "auth",
            "name_en": "Step 1: Authentication Setup",
            "name_ko": "1단계: 인증 설정",
            "description_en": "Configure Adobe Experience Platform credentials",
            "description_ko": "Adobe Experience Platform 자격 증명 구성",
            "command": "aep init",
        },
        {
            "key": "ai_provider",
            "name_en": "Step 2: AI Provider Configuration",
            "name_ko": "2단계: AI 프로바이더 설정",
            "description_en": "Set up Anthropic or OpenAI API key for AI features",
            "description_ko": "AI 기능을 위한 Anthropic 또는 OpenAI API 키 설정",
            "command": "aep ai set-key anthropic",
        },
        {
            "key": "schema",
            "name_en": "Step 3: Schema Creation",
            "name_ko": "3단계: 스키마 생성",
            "description_en": "Design and create XDM schemas for your data",
            "description_ko": "데이터를 위한 XDM 스키마 설계 및 생성",
            "command": "aep schema create --name MySchema --interactive",
        },
        {
            "key": "upload_schema",
            "name_en": "Step 4: Upload Schema to AEP",
            "name_ko": "4단계: AEP에 스키마 업로드",
            "description_en": "Register your schema in Adobe Experience Platform",
            "description_ko": "Adobe Experience Platform에 스키마 등록",
            "command": "aep schema create --name MySchema --from-sample data.json --upload",
        },
        {
            "key": "dataset",
            "name_en": "Step 5: Create Dataset",
            "name_ko": "5단계: 데이터셋 생성",
            "description_en": "Set up datasets linked to your schemas",
            "description_ko": "스키마와 연결된 데이터셋 설정",
            "command": "aep dataset list",
        },
        {
            "key": "ingest",
            "name_en": "Step 6: Data Ingestion",
            "name_ko": "6단계: 데이터 수집",
            "description_en": "Upload data to Adobe Experience Platform",
            "description_ko": "Adobe Experience Platform에 데이터 업로드",
            "command": "aep dataset upload --dataset-id <id> --file data.csv",
        },
    ],
    "data-engineer": [
        {
            "key": "auth",
            "name_en": "Step 1: Authentication Setup",
            "name_ko": "1단계: 인증 설정",
            "description_en": "Configure AEP credentials with production access",
            "description_ko": "프로덕션 액세스를 위한 AEP 자격 증명 구성",
            "command": "aep init",
        },
        {
            "key": "ai_provider",
            "name_en": "Step 2: AI Provider Configuration",
            "name_ko": "2단계: AI 프로바이더 설정",
            "description_en": "Set up AI provider for schema generation and validation",
            "description_ko": "스키마 생성 및 검증을 위한 AI 프로바이더 설정",
            "command": "aep ai set-key anthropic",
        },
        {
            "key": "analyze_data",
            "name_en": "Step 3: Analyze Existing Data",
            "name_ko": "3단계: 기존 데이터 분석",
            "description_en": "Scan and analyze your data sources",
            "description_ko": "데이터 소스 스캔 및 분석",
            "command": "aep schema analyze --directory ./data",
        },
        {
            "key": "schema_design",
            "name_en": "Step 4: Schema Design",
            "name_ko": "4단계: 스키마 설계",
            "description_en": "Create XDM schemas from sample data with AI assistance",
            "description_ko": "AI 지원을 통한 샘플 데이터로부터 XDM 스키마 생성",
            "command": "aep schema create --from-sample data.json --use-ai",
        },
        {
            "key": "schema_validation",
            "name_en": "Step 5: Schema Validation",
            "name_ko": "5단계: 스키마 검증",
            "description_en": "Validate schemas against XDM standards",
            "description_ko": "XDM 표준에 대한 스키마 검증",
            "command": "aep schema validate --file schema.json",
        },
        {
            "key": "upload_schema",
            "name_en": "Step 6: Upload Schema to AEP",
            "name_ko": "6단계: AEP에 스키마 업로드",
            "description_en": "Register schemas in Adobe Experience Platform",
            "description_ko": "Adobe Experience Platform에 스키마 등록",
            "command": "aep schema upload --file schema.json",
        },
        {
            "key": "dataset_creation",
            "name_en": "Step 7: Create Datasets",
            "name_ko": "7단계: 데이터셋 생성",
            "description_en": "Create datasets linked to your schemas",
            "description_ko": "스키마와 연결된 데이터셋 생성",
            "command": "aep dataset create --schema-id <id> --name MyDataset",
        },
        {
            "key": "batch_ingestion",
            "name_en": "Step 8: Batch Data Ingestion",
            "name_ko": "8단계: 배치 데이터 수집",
            "description_en": "Upload large datasets using batch ingestion",
            "description_ko": "배치 수집을 사용한 대용량 데이터셋 업로드",
            "command": "aep dataset upload --dataset-id <id> --file data.csv --batch-size 10000",
        },
        {
            "key": "monitoring",
            "name_en": "Step 9: Monitor Ingestion Status",
            "name_ko": "9단계: 수집 상태 모니터링",
            "description_en": "Check batch ingestion status and troubleshoot",
            "description_ko": "배치 수집 상태 확인 및 문제 해결",
            "command": "aep dataset status --batch-id <id>",
        },
    ],
    "marketer": [
        {
            "key": "auth",
            "name_en": "Step 1: Authentication Setup",
            "name_ko": "1단계: 인증 설정",
            "description_en": "Connect to Adobe Experience Platform",
            "description_ko": "Adobe Experience Platform 연결",
            "command": "aep init",
        },
        {
            "key": "ai_provider",
            "name_en": "Step 2: AI Provider Configuration",
            "name_ko": "2단계: AI 프로바이더 설정",
            "description_en": "Enable AI-powered features",
            "description_ko": "AI 기반 기능 활성화",
            "command": "aep ai set-key anthropic",
        },
        {
            "key": "customer_schema",
            "name_en": "Step 3: Create Customer Profile Schema",
            "name_ko": "3단계: 고객 프로필 스키마 생성",
            "description_en": "Design schema for customer data",
            "description_ko": "고객 데이터를 위한 스키마 설계",
            "command": "aep schema create --name CustomerProfile --interactive",
        },
        {
            "key": "event_schema",
            "name_en": "Step 4: Create Event Schema",
            "name_ko": "4단계: 이벤트 스키마 생성",
            "description_en": "Design schema for customer events and interactions",
            "description_ko": "고객 이벤트 및 상호작용을 위한 스키마 설계",
            "command": "aep schema create --name CustomerEvents --interactive",
        },
        {
            "key": "upload_schemas",
            "name_en": "Step 5: Upload Schemas to AEP",
            "name_ko": "5단계: AEP에 스키마 업로드",
            "description_en": "Register schemas in Adobe Experience Platform",
            "description_ko": "Adobe Experience Platform에 스키마 등록",
            "command": "aep schema upload --file schema.json",
        },
        {
            "key": "import_data",
            "name_en": "Step 6: Import Customer Data",
            "name_ko": "6단계: 고객 데이터 가져오기",
            "description_en": "Upload customer profiles and historical data",
            "description_ko": "고객 프로필 및 과거 데이터 업로드",
            "command": "aep dataset upload --dataset-id <id> --file customers.csv",
        },
        {
            "key": "segments",
            "name_en": "Step 7: Create Audience Segments",
            "name_ko": "7단계: 오디언스 세그먼트 생성",
            "description_en": "Define customer segments for targeting",
            "description_ko": "타겟팅을 위한 고객 세그먼트 정의",
            "command": "aep segment create --name HighValueCustomers",
        },
        {
            "key": "activation",
            "name_en": "Step 8: Activate Destinations",
            "name_ko": "8단계: 대상 활성화",
            "description_en": "Connect to marketing channels and activate segments",
            "description_ko": "마케팅 채널 연결 및 세그먼트 활성화",
            "command": "aep destination activate --segment-id <id>",
        },
    ],
}


@command_metadata(CommandCategory.ENHANCED, "Start interactive tutorial")
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
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Reset and start from beginning",
    ),
) -> None:
    """Start or continue onboarding tutorial.
    
    Automatically resumes if a tutorial is in progress. Use --reset to start over.

    Examples:
        aep onboarding start
        aep onboarding start --scenario basic
        aep onboarding start --dry-run
        aep onboarding start --language ko
        aep onboarding start --reset
    """
    # Load or create onboarding state
    state = load_onboarding_state()
    
    # Check if tutorial is already in progress
    if state.scenario and not reset and not scenario:
        steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
        total_steps = len(steps)
        completed_count = len(state.completed_steps)
        
        console.print(f"\n[yellow]⚠  Tutorial in progress: {state.scenario.value}[/yellow]")
        console.print(f"[dim]Progress: {completed_count}/{total_steps} steps completed[/dim]\n")
        
        if not Confirm.ask("Continue from where you left off?", default=True):
            if Confirm.ask("Start a new tutorial instead?", default=False):
                reset = True
            else:
                console.print("[yellow]Cancelled[/yellow]")
                return
    
    # Reset if requested
    if reset:
        from pathlib import Path
        state_file = Path.home() / ".adobe" / "onboarding_progress.json"
        if state_file.exists():
            state_file.unlink()
        state = load_onboarding_state()
        console.print("[green]✓ Progress reset[/green]\n")

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

    # Mode selection and save
    if offline:
        state.mode = TutorialMode.OFFLINE
        console.print(f"\n[yellow]📦 {t('onboarding.modes.offline', language)}[/yellow]")
    elif dry_run:
        state.mode = TutorialMode.DRY_RUN
        console.print(f"\n[yellow]🎓 {t('onboarding.modes.dry_run', language)}[/yellow]")
    else:
        state.mode = TutorialMode.ONLINE
        console.print(f"\n[green]🌐 {t('onboarding.modes.online', language)}[/green]")

    # Show dry-run mode explanation
    if state.mode == TutorialMode.DRY_RUN:
        console.print()
        console.print(Panel(
            f"[bold yellow]🎓 Dry-Run Mode Enabled[/bold yellow]\n\n"
            f"• Commands will be simulated without making actual API calls\n"
            f"• You'll see what would happen without affecting your AEP environment\n"
            f"• Perfect for learning and practicing before production use\n"
            f"• All tutorial steps and guidance remain the same",
            border_style="yellow",
            expand=False,
        ))

    # Save initial state
    if state.started_at is None:
        from datetime import datetime

        state.started_at = datetime.now()

    save_onboarding_state(state)

    # Start tutorial workflow
    console.print(f"\n[bold green]✓[/bold green] {t('onboarding.messages.step_complete', language)}\n")
    console.print(
        f"[dim]Use [cyan]aep onboarding status[/cyan] to check progress[/dim]"
    )
    console.print(
        f"[dim]Use [cyan]aep onboarding manage[/cyan] to control steps manually[/dim]"
    )


@command_metadata(CommandCategory.ENHANCED, "View tutorial progress")
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

    # Auto-detect completed steps and sync state
    detected_steps = detect_completed_steps(state.scenario)
    
    if detected_steps:
        # Get steps for current scenario
        steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
        
        # Check for new completions
        synced_items = []
        for step_key, milestone in detected_steps.items():
            # Find step number
            for idx, step_info in enumerate(steps, start=1):
                if step_info["key"] == step_key and idx not in state.completed_steps:
                    state.completed_steps.append(idx)
                    synced_items.append(step_key)
                    
                    # Award milestone if not already achieved
                    if milestone not in state.milestones_achieved:
                        state.milestones_achieved.append(milestone)
                    break
        
        # Save if any changes were made
        if synced_items:
            state.completed_steps.sort()
            state.save()
            console.print(f"[dim]✨ Auto-detected and synced: {', '.join(synced_items)}[/dim]\n")

    i18n = get_i18n(state.language)

    # Progress header with mode indicator
    mode_emoji = {
        TutorialMode.ONLINE: "🌐",
        TutorialMode.DRY_RUN: "🎓",
        TutorialMode.OFFLINE: "📦",
    }
    mode_color = {
        TutorialMode.ONLINE: "green",
        TutorialMode.DRY_RUN: "yellow",
        TutorialMode.OFFLINE: "blue",
    }
    
    console.print()
    console.print(
        Panel(
            f"[bold]{t('onboarding.welcome', state.language)}[/bold]\n\n"
            f"[{mode_color[state.mode]}]{mode_emoji[state.mode]} Mode: {state.mode.value.title()}[/{mode_color[state.mode]}]",
            border_style="cyan",
        )
    )

    # Get tutorial steps
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    total_steps = len(steps)

    # Progress bar
    progress_pct = state.get_progress_percentage(total_steps)

    console.print()
    console.print(f"[cyan]{t('onboarding.messages.progress', state.language)}:[/cyan]")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        progress.add_task("", completed=progress_pct, total=100)

    # Steps tree with details
    console.print()
    tree = Tree(f"[bold]{state.scenario.value.title()} Tutorial[/bold]")

    for step_num, step_info in enumerate(steps, start=1):
        if step_num in state.completed_steps:
            status_icon = "[green]✅[/green]"
            status_text = f"[green]{t('onboarding.status.completed', state.language)}[/green]"
        elif step_num == state.current_step:
            status_icon = "[yellow]🔄[/yellow]"
            status_text = f"[yellow]{t('onboarding.status.in_progress', state.language)}[/yellow]"
        elif step_num in state.skipped_steps:
            status_icon = "[dim]⚠️[/dim]"
            status_text = f"[dim]{t('onboarding.status.skipped', state.language)}[/dim]"
        else:
            status_icon = "[dim]⬜[/dim]"
            status_text = f"[dim]{t('onboarding.status.not_started', state.language)}[/dim]"

        # Get localized step info
        name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
        desc_key = f"description_{state.language}" if state.language in ["en", "ko"] else "description_en"
        
        step_name = step_info.get(name_key, step_info["name_en"])
        step_desc = step_info.get(desc_key, step_info["description_en"])
        step_cmd = step_info["command"]
        
        # Create step node
        step_node = tree.add(f"{status_icon} {step_name} - {status_text}")
        
        # Add description and command as subnodes
        step_node.add(f"[dim]{step_desc}[/dim]")
        step_node.add(f"[cyan]→ {step_cmd}[/cyan]")

    console.print(tree)

    # Next action hint
    if state.current_step and state.current_step <= len(steps):
        current_step_info = steps[state.current_step - 1]
        desc_key = f"description_{state.language}" if state.language in ["en", "ko"] else "description_en"
        name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
        
        console.print()
        console.print(Panel(
            f"[bold]Next Step:[/bold]\n"
            f"{current_step_info.get(name_key, current_step_info['name_en'])}\n\n"
            f"[dim]{current_step_info.get(desc_key, current_step_info['description_en'])}[/dim]\n\n"
            f"[cyan]Run: {current_step_info['command']}[/cyan]",
            title="📍 Current Task",
            border_style="yellow",
        ))

    # Milestones
    if state.milestones_achieved:
        console.print()
        console.print("[bold yellow]🏆 Achievements:[/bold yellow]")
        for milestone in state.milestones_achieved:
            milestone_text = t(f"onboarding.milestones.{milestone.value.replace('-', '_')}", state.language)
            console.print(f"  {milestone_text}")
    
    # Tips
    console.print()
    console.print("[dim]💡 Tip: Use 'aep onboarding manage' to manually control step progress[/dim]")
    console.print()


@command_metadata(CommandCategory.ENHANCED, "Manage tutorial state")
@onboarding_app.command("manage")
def manage_steps() -> None:
    """Interactively manage tutorial steps - mark complete/incomplete.
    
    Allows manual control over which steps are marked as completed,
    useful for non-sequential workflows or correcting progress.
    
    Examples:
        aep onboarding manage
    """
    import time
    
    state = load_onboarding_state()
    
    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]aep onboarding start[/cyan]")
        return
    
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
    
    while True:
        # Clear screen (works in most terminals)
        console.print("\n" * 2)
        console.print("[bold cyan]═══ Step Management ═══[/bold cyan]\n")
        console.print(f"[dim]Scenario: {state.scenario.value}[/dim]\n")
        
        # Display steps with status
        for idx, step_info in enumerate(steps, start=1):
            status = "[green]✅[/green]" if idx in state.completed_steps else "[dim]⬜[/dim]"
            name = step_info.get(name_key, step_info["name_en"])
            console.print(f"{status} {idx}. {name}")
        
        console.print("\n[dim]Enter step number to toggle, 'q' to save and quit[/dim]")
        choice = Prompt.ask("[cyan]>[/cyan]", default="q")
        
        if choice.lower() == 'q':
            state.save()
            console.print("\n[green]✓ Progress saved![/green]")
            break
        
        try:
            step_num = int(choice)
            if 1 <= step_num <= len(steps):
                step_name = steps[step_num - 1].get(name_key, steps[step_num - 1]["name_en"])
                
                if step_num in state.completed_steps:
                    state.completed_steps.remove(step_num)
                    # Also remove from skipped if present
                    if step_num in state.skipped_steps:
                        state.skipped_steps.remove(step_num)
                    console.print(f"\n[yellow]○ Step {step_num} marked as incomplete[/yellow]")
                else:
                    if step_num not in state.completed_steps:
                        state.completed_steps.append(step_num)
                        state.completed_steps.sort()
                    # Remove from skipped if present
                    if step_num in state.skipped_steps:
                        state.skipped_steps.remove(step_num)
                    console.print(f"\n[green]✓ Step {step_num} marked as complete[/green]")
                
                time.sleep(0.8)
            else:
                console.print(f"\n[red]Invalid step number. Please enter 1-{len(steps)}[/red]")
                time.sleep(1)
        except ValueError:
            console.print("\n[red]Please enter a valid number or 'q' to quit[/red]")
            time.sleep(1)


@onboarding_app.command("complete", hidden=True)
def mark_step_complete(
    step: int = typer.Argument(..., help="Step number to mark as complete")
) -> None:
    """Mark a specific step as completed.
    
    Examples:
        aep onboarding complete 3
        aep onboarding complete 5
    """
    state = load_onboarding_state()
    
    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]aep onboarding start[/cyan]")
        return
    
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    
    if step < 1 or step > len(steps):
        console.print(f"[red]Invalid step number. Must be between 1 and {len(steps)}[/red]")
        raise typer.Exit(1)
    
    name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
    step_name = steps[step - 1].get(name_key, steps[step - 1]["name_en"])
    
    if step not in state.completed_steps:
        state.completed_steps.append(step)
        state.completed_steps.sort()
    
    # Remove from skipped if present
    if step in state.skipped_steps:
        state.skipped_steps.remove(step)
    
    state.save()
    console.print(f"[green]✓ Step {step} ({step_name}) marked as complete[/green]")


@onboarding_app.command("uncomplete", hidden=True)
def mark_step_uncomplete(
    step: int = typer.Argument(..., help="Step number to mark as incomplete")
) -> None:
    """Mark a specific step as incomplete.
    
    Examples:
        aep onboarding uncomplete 3
    """
    state = load_onboarding_state()
    
    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]aep onboarding start[/cyan]")
        return
    
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    
    if step < 1 or step > len(steps):
        console.print(f"[red]Invalid step number. Must be between 1 and {len(steps)}[/red]")
        raise typer.Exit(1)
    
    name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
    step_name = steps[step - 1].get(name_key, steps[step - 1]["name_en"])
    
    if step in state.completed_steps:
        state.completed_steps.remove(step)
    
    state.save()
    console.print(f"[yellow]○ Step {step} ({step_name}) marked as incomplete[/yellow]")


@onboarding_app.command("sync", hidden=True)
def sync_status() -> None:
    """Manually sync onboarding status with actual system state.
    
    Detects which steps are already completed (e.g., authentication configured,
    AI keys set) and updates the onboarding progress accordingly.
    
    Examples:
        adobe onboarding sync
    """
    state = load_onboarding_state()

    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]adobe onboarding start[/cyan]")
        return
    
    console.print("[cyan]🔍 Detecting completed steps...[/cyan]\n")
    
    # Detect completed steps
    detected_steps = detect_completed_steps(state.scenario)
    
    if not detected_steps:
        console.print("[yellow]No completed steps detected[/yellow]")
        console.print("[dim]Make sure you have:")
        console.print("  • Run 'aep init' to configure authentication")
        console.print("  • Run 'aep ai set-key' to configure AI provider[/dim]")
        return
    
    # Get steps for current scenario
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    
    # Update state
    synced_count = 0
    synced_items = []
    
    for step_key, milestone in detected_steps.items():
        # Find step number and info
        for idx, step_info in enumerate(steps, start=1):
            if step_info["key"] == step_key:
                if idx not in state.completed_steps:
                    state.completed_steps.append(idx)
                    synced_count += 1
                    synced_items.append(f"{step_info['name_en']} (Step {idx})")
                
                # Award milestone if not already achieved
                if milestone not in state.milestones_achieved:
                    state.milestones_achieved.append(milestone)
                break
    
    # Save state
    if synced_count > 0:
        state.completed_steps.sort()
        state.save()
        
        console.print(f"[green]✓ Synced {synced_count} step(s):[/green]")
        for item in synced_items:
            console.print(f"  • {item}")
        console.print(f"\n[dim]Run 'adobe onboarding status' to see updated progress[/dim]")
    else:
        console.print("[green]✓ All detected steps already marked as complete[/green]")


@onboarding_app.command("next", hidden=True)
def next_step(
    mark_complete: bool = typer.Option(
        True,
        "--complete/--no-complete",
        help="Mark current step as completed before moving to next",
    )
) -> None:
    """Move to the next tutorial step.
    
    By default, marks the current step as completed. Use --no-complete to skip without completing.

    Examples:
        adobe onboarding next
        adobe onboarding next --no-complete
    """
    state = load_onboarding_state()

    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]adobe onboarding start[/cyan]")
        return

    # Get tutorial steps
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    total_steps = len(steps)

    if state.current_step == 0:
        console.print("[yellow]Tutorial not started yet[/yellow]")
        console.print("Use: [cyan]adobe onboarding resume[/cyan]")
        return

    if state.current_step > total_steps:
        console.print("[green]✓ Tutorial already completed![/green]")
        console.print("\nStart a new tutorial with: [cyan]adobe onboarding reset[/cyan]")
        return

    # Mark current step as completed
    if mark_complete and state.current_step not in state.completed_steps:
        state.completed_steps.append(state.current_step)
        console.print(f"[green]✓ Step {state.current_step} marked as completed[/green]")
    elif not mark_complete and state.current_step not in state.skipped_steps:
        state.skipped_steps.append(state.current_step)
        console.print(f"[yellow]⚠ Step {state.current_step} marked as skipped[/yellow]")

    # Move to next step
    state.current_step += 1

    if state.current_step > total_steps:
        console.print("\n[bold green]🎉 Congratulations! Tutorial completed![/bold green]")
        
        # Add completion milestone
        from adobe_experience.core.config import TutorialMilestone
        if TutorialMilestone.FIRST_SCHEMA not in state.milestones_achieved:
            state.milestones_achieved.append(TutorialMilestone.FIRST_SCHEMA)
        
        save_onboarding_state(state)
        return

    # Save state
    save_onboarding_state(state)

    # Show next step info
    next_step_info = steps[state.current_step - 1]
    name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
    desc_key = f"description_{state.language}" if state.language in ["en", "ko"] else "description_en"
    
    step_name = next_step_info.get(name_key, next_step_info["name_en"])
    step_desc = next_step_info.get(desc_key, next_step_info["description_en"])
    step_cmd = next_step_info["command"]

    console.print()
    console.print(Panel(
        f"[bold cyan]{step_name}[/bold cyan]\n\n"
        f"{step_desc}\n\n"
        f"[cyan]→ {step_cmd}[/cyan]",
        title=f"📍 Step {state.current_step}/{total_steps}",
        border_style="cyan",
    ))


@onboarding_app.command("skip", hidden=True)
def skip_step() -> None:
    """Skip the current tutorial step without marking it as completed.

    Examples:
        adobe onboarding skip
    """
    state = load_onboarding_state()

    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]adobe onboarding start[/cyan]")
        return

    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    total_steps = len(steps)

    if state.current_step == 0:
        console.print("[yellow]Tutorial not started yet[/yellow]")
        console.print("Use: [cyan]adobe onboarding resume[/cyan]")
        return

    if state.current_step > total_steps:
        console.print("[green]✓ Tutorial already completed![/green]")
        return

    # Mark as skipped
    if state.current_step not in state.skipped_steps:
        state.skipped_steps.append(state.current_step)
    
    # Remove from completed if it was there
    if state.current_step in state.completed_steps:
        state.completed_steps.remove(state.current_step)

    console.print(f"[yellow]⚠ Step {state.current_step} skipped[/yellow]")

    # Move to next step
    state.current_step += 1

    if state.current_step > total_steps:
        console.print("\n[bold green]🎉 Tutorial completed (with skipped steps)[/bold green]")
        save_onboarding_state(state)
        return

    save_onboarding_state(state)

    # Show next step
    next_step_info = steps[state.current_step - 1]
    name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
    step_name = next_step_info.get(name_key, next_step_info["name_en"])
    
    console.print(f"\n[cyan]→ Moving to: {step_name}[/cyan]")
    console.print("Use [cyan]adobe onboarding status[/cyan] to see current progress")


@onboarding_app.command("back", hidden=True)
def back_step() -> None:
    """Go back to the previous tutorial step.

    Examples:
        adobe onboarding back
    """
    state = load_onboarding_state()

    if not state.scenario:
        console.print("[yellow]No onboarding in progress[/yellow]")
        console.print("Start with: [cyan]adobe onboarding start[/cyan]")
        return

    if state.current_step <= 1:
        console.print("[yellow]Already at the first step[/yellow]")
        return

    # Move back
    state.current_step -= 1

    # Remove from completed/skipped if going back
    if state.current_step in state.completed_steps:
        state.completed_steps.remove(state.current_step)
    if state.current_step in state.skipped_steps:
        state.skipped_steps.remove(state.current_step)

    save_onboarding_state(state)

    # Show current step
    steps = TUTORIAL_STEPS.get(state.scenario.value, TUTORIAL_STEPS["basic"])
    step_info = steps[state.current_step - 1]
    name_key = f"name_{state.language}" if state.language in ["en", "ko"] else "name_en"
    step_name = step_info.get(name_key, step_info["name_en"])

    console.print(f"[cyan]← Back to: {step_name}[/cyan]")
    console.print("Use [cyan]adobe onboarding status[/cyan] to see current progress")


@onboarding_app.command("resume", hidden=True)
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


@onboarding_app.command("achievements", hidden=True)
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


@onboarding_app.command("reset", hidden=True)
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


@onboarding_app.command("ask", hidden=True)
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

    # Detect language from question (한글이 있으면 한국어로 판단)
    detected_language = state.language or "en"
    if any('\uac00' <= char <= '\ud7a3' for char in question):
        detected_language = "ko"
    
    # Get i18n instance for language
    i18n = get_i18n()
    if detected_language:
        i18n.change_language(detected_language)

    # Display question
    console.print(Panel(
        f"[bold cyan]{t('ai_tutor.ask', detected_language)}[/bold cyan]\n\n{question}",
        border_style="cyan",
    ))

    # Check cache first
    qa_cache = load_qa_cache()
    cached_entry = qa_cache.get(question, detected_language)
    
    if cached_entry:
        console.print("[dim]💾 Found cached answer[/dim]\n")
        console.print(Panel(
            cached_entry.answer,
            title=f"[bold green]{t('ai_tutor.answer', detected_language)}[/bold green]",
            border_style="green",
        ))
        console.print(f"[dim]Used {cached_entry.hit_count} times | Last updated: {cached_entry.timestamp.strftime('%Y-%m-%d %H:%M')}[/dim]")
        
        # Save updated cache (hit_count was incremented)
        save_qa_cache(qa_cache)
        return

    # Prepare context
    context = {
        "scenario": state.scenario.value if state.scenario else "basic",
        "current_step": state.current_step or 0,
        "completed_steps": state.completed_steps or [],
        "language": detected_language,
        "milestones": [m.value for m in state.milestones_achieved] if state.milestones_achieved else [],
    }

    # Call AI tutor
    try:
        engine = AIInferenceEngine()

        with console.status(f"[bold blue]{t('ai_tutor.thinking', detected_language)}[/bold blue]"):
            answer = asyncio.run(
                engine.answer_tutorial_question(
                    question=question,
                    context=context,
                    language=detected_language,
                )
            )

        # Save to cache
        qa_cache.add(
            question=question,
            answer=answer,
            language=detected_language,
            context_scenario=context["scenario"],
        )
        save_qa_cache(qa_cache)

        # Display answer
        console.print()
        console.print(Panel(
            answer,
            title=f"[bold green]{t('ai_tutor.answer', detected_language)}[/bold green]",
            border_style="green",
        ))

    except ValueError as e:
        if "No AI provider configured" in str(e):
            console.print(f"\n[red]{t('errors.auth_failed', detected_language)}[/red]")
            console.print("[yellow]AI tutor requires an API key. Configure one with:[/yellow]")
            console.print("  [cyan]aep ai set-key anthropic[/cyan]")
            console.print("  [cyan]aep ai set-key openai[/cyan]")
        else:
            console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


@onboarding_app.command("clear-cache", hidden=True)
def clear_qa_cache(
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Clear AI tutor Q&A cache.

    This will remove all cached question-answer pairs, requiring
    fresh AI calls for all subsequent questions.

    Examples:
        adobe onboarding clear-cache
        adobe onboarding clear-cache --yes
    """
    qa_cache = load_qa_cache()
    
    if not qa_cache.entries:
        console.print("[yellow]Cache is already empty[/yellow]")
        return
    
    cache_size = len(qa_cache.entries)
    
    if not confirm:
        confirm = Confirm.ask(
            f"Clear {cache_size} cached Q&A entries?",
            default=False
        )
    
    if not confirm:
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    qa_cache.clear()
    save_qa_cache(qa_cache)
    
    console.print(f"[green]✓ Cleared {cache_size} cached entries[/green]")
    console.print("[dim]Future questions will require fresh AI calls[/dim]")


@onboarding_app.command("cache-stats", hidden=True)
def show_cache_stats() -> None:
    """Show AI tutor cache statistics.

    Examples:
        adobe onboarding cache-stats
    """
    qa_cache = load_qa_cache()
    
    if not qa_cache.entries:
        console.print("[yellow]Cache is empty[/yellow]")
        return
    
    # Calculate statistics
    total_entries = len(qa_cache.entries)
    total_hits = sum(entry.hit_count for entry in qa_cache.entries)
    
    # Language breakdown
    lang_counts = {}
    for entry in qa_cache.entries:
        lang_counts[entry.language] = lang_counts.get(entry.language, 0) + 1
    
    # Display statistics
    console.print(Panel.fit(
        f"[bold]Total Entries:[/bold] {total_entries}\n"
        f"[bold]Total Cache Hits:[/bold] {total_hits}\n"
        f"[bold]Average Hits per Entry:[/bold] {total_hits / total_entries:.1f}\n"
        f"[bold]Languages:[/bold] {', '.join(f'{k} ({v})' for k, v in lang_counts.items())}",
        title="Q&A Cache Statistics",
        border_style="cyan",
    ))
    
    # Show top 5 most used
    if qa_cache.entries:
        console.print("\n[bold]Top 5 Most Used:[/bold]")
        sorted_entries = sorted(qa_cache.entries, key=lambda e: e.hit_count, reverse=True)
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Question", style="white", max_width=50)
        table.add_column("Language", style="magenta", width=8)
        table.add_column("Hits", justify="right", style="green", width=6)
        
        for entry in sorted_entries[:5]:
            question_preview = entry.question[:47] + "..." if len(entry.question) > 50 else entry.question
            table.add_row(question_preview, entry.language, str(entry.hit_count))
        
        console.print(table)


__all__ = ["onboarding_app"]
