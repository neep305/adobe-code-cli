"""Custom Rich help formatter for categorized CLI commands."""

from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from adobe_experience.cli.command_metadata import (
    CommandCategory,
    get_category_icon,
    get_category_label,
    get_category_description,
    get_command_metadata,
)


console = Console()


def format_command_help_with_category(
    command_name: str,
    help_text: str,
    category: Optional[CommandCategory] = None,
) -> str:
    """Format command help text with category icon.
    
    Args:
        command_name: Name of the command
        help_text: Original help text
        category: Command category (auto-detected if None)
        
    Returns:
        Formatted help text with icon
    """
    if category is None:
        metadata = get_command_metadata(command_name)
        if metadata:
            category = metadata.category
    
    if category:
        icon = get_category_icon(category)
        return f"{icon} {help_text}"
    
    return help_text


def create_category_legend(lang: str = "en") -> Panel:
    """Create a Rich panel explaining command categories.
    
    Args:
        lang: Language code (en, ko)
        
    Returns:
        Rich Panel with category legend
    """
    legend_title = {
        "en": "Command Categories",
        "ko": "명령 카테고리",
    }
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Icon", style="bold")
    table.add_column("Category")
    table.add_column("Description", style="dim")
    
    for category in CommandCategory:
        icon = get_category_icon(category)
        label = get_category_label(category, lang)
        description = get_category_description(category, lang)
        table.add_row(icon, label, description)
    
    return Panel(
        table,
        title=legend_title.get(lang, legend_title["en"]),
        border_style="cyan",
        padding=(1, 2),
    )


def create_grouped_commands_help(
    commands: List[Tuple[str, str, CommandCategory]],
    lang: str = "en",
) -> str:
    """Create categorized help text for a list of commands.
    
    Args:
        commands: List of (command_name, help_text, category) tuples
        lang: Language code (en, ko)
        
    Returns:
        Formatted help text with grouped commands
    """
    # Group commands by category
    grouped: Dict[CommandCategory, List[Tuple[str, str]]] = {
        CommandCategory.API: [],
        CommandCategory.ENHANCED: [],
        CommandCategory.HYBRID: [],
    }
    
    for cmd_name, help_text, category in commands:
        grouped[category].append((cmd_name, help_text))
    
    # Build help sections
    sections = []
    
    # Order: API -> HYBRID -> ENHANCED
    for category in [CommandCategory.API, CommandCategory.HYBRID, CommandCategory.ENHANCED]:
        if not grouped[category]:
            continue
        
        icon = get_category_icon(category)
        label = get_category_label(category, lang)
        
        section = f"\n[bold cyan]{icon} {label}[/bold cyan]\n"
        
        for cmd_name, help_text in sorted(grouped[category]):
            section += f"  [green]{cmd_name:20}[/green]  {help_text}\n"
        
        sections.append(section)
    
    return "\n".join(sections)


def print_aep_help_header(lang: str = "en") -> None:
    """Print AEP command help header with category legend.
    
    Args:
        lang: Language code (en, ko)
    """
    intro_text = {
        "en": (
            "Adobe Experience Platform CLI with AI-powered enhancements.\n\n"
            "Commands are organized into three categories:"
        ),
        "ko": (
            "AI 기반 향상 기능이 포함된 Adobe Experience Platform CLI.\n\n"
            "명령은 세 가지 카테고리로 구성됩니다:"
        ),
    }
    
    console.print(intro_text.get(lang, intro_text["en"]))
    console.print()
    console.print(create_category_legend(lang))
    console.print()


def format_command_group_help(
    group_name: str,
    commands: Dict[str, str],
    subgroups: Dict[str, str],
    lang: str = "en",
) -> None:
    """Format and print help for a command group with categories.
    
    Args:
        group_name: Name of the command group
        commands: Dict of command_name -> help_text
        subgroups: Dict of subgroup_name -> help_text
        lang: Language code (en, ko)
    """
    # Collect command metadata
    categorized_commands = []
    
    for cmd_name, help_text in commands.items():
        metadata = get_command_metadata(cmd_name)
        category = metadata.category if metadata else CommandCategory.API
        categorized_commands.append((cmd_name, help_text, category))
    
    # Print legend if this is the main AEP group
    if group_name == "aep":
        print_aep_help_header(lang)
    
    # Print subgroups first (if any)
    if subgroups:
        subgroups_title = {
            "en": "Command Groups",
            "ko": "명령 그룹",
        }
        console.print(f"[bold cyan]{subgroups_title.get(lang, subgroups_title['en'])}[/bold cyan]")
        
        for subgroup_name, help_text in sorted(subgroups.items()):
            # Add icons to subgroups based on their primary category
            metadata = get_command_metadata(subgroup_name)
            if metadata:
                icon = get_category_icon(metadata.category)
                help_text = f"{icon} {help_text}"
            
            console.print(f"  [green]{subgroup_name:20}[/green]  {help_text}")
        console.print()
    
    # Print categorized commands
    if categorized_commands:
        commands_title = {
            "en": "Commands",
            "ko": "명령",
        }
        console.print(f"[bold cyan]{commands_title.get(lang, commands_title['en'])}[/bold cyan]")
        console.print(create_grouped_commands_help(categorized_commands, lang))


def create_workflow_examples(lang: str = "en") -> Panel:
    """Create panel with typical workflow examples.
    
    Args:
        lang: Language code (en, ko)
        
    Returns:
        Rich Panel with workflow examples
    """
    examples = {
        "en": [
            ("List schemas", "🔵", "aep schema list"),
            ("Generate schema with AI", "🟢", "aep schema create --use-ai --from-sample data.json"),
            ("Upload data with progress", "⚡", "aep ingest upload-file data.parquet --dataset-id <id>"),
            ("Analyze relationships", "🟢", "aep schema analyze-dataset --dataset-id <id>"),
        ],
        "ko": [
            ("스키마 목록 조회", "🔵", "aep schema list"),
            ("AI로 스키마 생성", "🟢", "aep schema create --use-ai --from-sample data.json"),
            ("진행 상황 표시 데이터 업로드", "⚡", "aep ingest upload-file data.parquet --dataset-id <id>"),
            ("관계 분석", "🟢", "aep schema analyze-dataset --dataset-id <id>"),
        ],
    }
    
    title = {
        "en": "Example Workflows",
        "ko": "예제 워크플로",
    }
    
    content = []
    for desc, icon, cmd in examples.get(lang, examples["en"]):
        content.append(f"{icon} [bold]{desc}[/bold]\n   [cyan]{cmd}[/cyan]\n")
    
    return Panel(
        "\n".join(content),
        title=title.get(lang, title["en"]),
        border_style="yellow",
        padding=(1, 2),
    )


def print_workflow_examples(lang: str = "en") -> None:
    """Print workflow examples panel.
    
    Args:
        lang: Language code (en, ko)
    """
    console.print()
    console.print(create_workflow_examples(lang))
    console.print()
    
    tip_text = {
        "en": "[dim]💡 Tip: Use --use-ai flag with hybrid commands to enable AI features[/dim]",
        "ko": "[dim]💡 팁: 하이브리드 명령에 --use-ai 플래그를 사용하여 AI 기능 활성화[/dim]",
    }
    console.print(tip_text.get(lang, tip_text["en"]))
