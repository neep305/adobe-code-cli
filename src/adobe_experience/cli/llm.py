"""LLM-powered interactive CLI mode."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from adobe_experience.cli.llm_tools import CommandExecutor, ToolRegistry, register_safe_tools
from adobe_experience.cli.llm_tools.schemas import LLMSession
from adobe_experience.core.config import get_config

logger = logging.getLogger(__name__)
console = Console()
llm_app = typer.Typer(help="🤖 LLM-powered interactive AEP assistant")


@llm_app.command()
def chat(
    query: Optional[str] = typer.Argument(None, help="One-shot query (omit for interactive mode)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider (openai or anthropic). Uses configured default if not specified."),
    tools: Optional[str] = typer.Option(None, "--tools", help="Comma-separated tool categories (schema,dataset,dataflow)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show tool calls and execution details"),
    max_turns: int = typer.Option(10, "--max-turns", help="Maximum conversation turns with tool calls"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use. Uses configured default if not specified."),
) -> None:
    """LLM-powered AEP assistant (interactive mode).
    
    Talk to Claude or ChatGPT to query and analyze AEP resources using natural language.
    Available tools include schema, dataset, and dataflow operations.
    
    Phase 1: Only read-only operations are supported for safety.
    
    Examples:
        # Interactive mode (uses default provider and model)
        aep llm chat
        
        # One-shot queries
        aep llm chat "list my schemas"
        aep llm chat "show failing dataflows from last 7 days"
        
        # Specify provider
        aep llm chat --provider openai "analyze my schemas"
        aep llm chat -p anthropic "check dataflow health"
        
        # Category filtering
        aep llm chat --tools schema,dataset "analyze my schemas"
        
        # Custom model
        aep llm chat --model gpt-4o "complex query"
    """
    try:
        # Load config
        config = get_config()
        
        # Determine provider (priority: CLI arg > config > auto-detect)
        if provider:
            provider = provider.lower()
            if provider not in ["openai", "anthropic"]:
                console.print(f"[red]Error: Unsupported provider '{provider}'[/red]")
                console.print("Supported providers: openai, anthropic")
                raise typer.Exit(1)
        else:
            # Use configured provider
            provider = config.ai_provider
            if provider == "auto":
                # Auto-detect based on available keys
                if config.anthropic_api_key:
                    provider = "anthropic"
                elif config.openai_api_key:
                    provider = "openai"
                else:
                    _show_setup_help()
                    raise typer.Exit(1)
        
        # Determine model (priority: CLI arg > config default)
        if not model:
            model = config.ai_model
        
        # Check for API key and initialize client based on provider
        if provider == "anthropic":
            if not config.anthropic_api_key:
                console.print("[red]Error: Anthropic API key not configured[/red]")
                console.print("\n[yellow]To use Anthropic:[/yellow]")
                console.print("  aep ai set-key anthropic")
                console.print("\nOr set the ANTHROPIC_API_KEY environment variable")
                raise typer.Exit(1)
            
            # Initialize Anthropic client
            try:
                from anthropic import Anthropic
                llm_client = Anthropic(api_key=config.anthropic_api_key.get_secret_value())
            except Exception as e:
                console.print(f"[red]Error initializing Anthropic client: {e}[/red]")
                raise typer.Exit(1)
        
        elif provider == "openai":
            if not config.openai_api_key:
                console.print("[red]Error: OpenAI API key not configured[/red]")
                console.print("\n[yellow]To use OpenAI:[/yellow]")
                console.print("  aep ai set-key openai")
                console.print("\nOr set the OPENAI_API_KEY environment variable")
                raise typer.Exit(1)
            
            # Initialize OpenAI client
            try:
                from openai import OpenAI
                llm_client = OpenAI(api_key=config.openai_api_key.get_secret_value())
            except ImportError:
                console.print("[red]Error: OpenAI package not installed[/red]")
                console.print("\n[yellow]Install OpenAI:[/yellow]")
                console.print("  pip install openai")
                raise typer.Exit(1)
            except Exception as e:
                console.print(f"[red]Error initializing OpenAI client: {e}[/red]")
                raise typer.Exit(1)
        
        # Initialize tool system
        registry = ToolRegistry()
        register_safe_tools(registry)
        executor = CommandExecutor(registry, config)
        
        # Filter tools by category if specified
        tool_categories = tools.split(",") if tools else None
        available_tools = registry.get_anthropic_tools(categories=tool_categories, safe_only=True)
        
        if not available_tools:
            console.print("[yellow]No tools available with the specified filters[/yellow]")
            return
        
        # System prompt
        system_prompt = _build_system_prompt(registry, tool_categories)
        
        # Create session
        session = LLMSession(
            session_id=str(uuid4()),
            max_turns=max_turns
        )
        
        # One-shot mode
        if query:
            console.print(f"[cyan]Query:[/cyan] {query}\n")
            
            if provider == "anthropic":
                asyncio.run(_handle_anthropic_turn(
                    llm_client, query, available_tools,
                    system_prompt, session, executor,
                    verbose, max_turns, model
                ))
            else:  # openai
                asyncio.run(_handle_openai_turn(
                    llm_client, query, available_tools,
                    system_prompt, session, executor,
                    verbose, max_turns, model
                ))
            return
        
        # Interactive mode
        _show_welcome(registry, tool_categories, model, provider)
        
        while True:
            try:
                user_input = Prompt.ask("\n[cyan]You[/cyan]")
                
                # Handle special commands
                if user_input.lower() in ["exit", "quit", "q"]:
                    console.print("\n[dim]👋 Goodbye![/dim]")
                    break
                
                if user_input == "/tools":
                    _show_available_tools(registry, tool_categories)
                    continue
                
                if user_input == "/clear":
                    session.clear_history()
                    console.print("[dim]💬 Conversation history cleared[/dim]")
                    continue
                
                if user_input == "/stats":
                    _show_session_stats(session)
                    continue
                
                if user_input == "/help":
                    _show_help()
                    continue
                
                if not user_input.strip():
                    continue
                
                # Handle user query
                if provider == "anthropic":
                    asyncio.run(_handle_anthropic_turn(
                        llm_client, user_input, available_tools,
                        system_prompt, session, executor,
                        verbose, max_turns, model
                    ))
                else:  # openai
                    asyncio.run(_handle_openai_turn(
                        llm_client, user_input, available_tools,
                        system_prompt, session, executor,
                        verbose, max_turns, model
                    ))
                
            except KeyboardInterrupt:
                console.print("\n\n[dim]👋 Goodbye![/dim]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                logger.exception("Error in interactive loop")
    
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        raise typer.Exit(1)


def _show_setup_help() -> None:
    """Show helpful setup instructions when no provider configured."""
    console.print("[red]Error: No AI provider configured[/red]\n")
    console.print("[bold]Quick Setup:[/bold]")
    console.print("  1. [cyan]aep ai set-key anthropic[/cyan]  - Setup Claude")
    console.print("     OR")
    console.print("  2. [cyan]aep ai set-key openai[/cyan]      - Setup ChatGPT\n")
    console.print("[bold]Or use environment variables:[/bold]")
    console.print("  [dim]export ANTHROPIC_API_KEY=sk-ant-...[/dim]")
    console.print("  [dim]export OPENAI_API_KEY=sk-...[/dim]\n")
    console.print("[bold]Check your configuration:[/bold]")
    console.print("  [cyan]aep ai status[/cyan]")


async def _handle_anthropic_turn(
    client,
    query: str,
    tools: List[Dict],
    system_prompt: str,
    session: LLMSession,
    executor: CommandExecutor,
    verbose: bool,
    max_turns: int,
    model: str
) -> None:
    """Handle one conversation turn with Anthropic tool calling loop.
    
    Args:
        client: Anthropic client
        query: User query
        tools: Available tools in Anthropic format
        system_prompt: System prompt
        session: LLM session
        executor: Command executor
        verbose: Show tool call details
        max_turns: Maximum tool calling iterations
        model: Model name to use
    """
    # Add user message to session
    session.add_turn("user", query)
    
    # Prepare messages for API
    messages = _prepare_messages(session)
    
    turn_count = 0
    
    try:
        # Initial LLM call
        with console.status("[bold blue]🤔 Thinking..."):
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tools
            )
        
        # Tool calling loop
        while response.stop_reason == "tool_use" and turn_count < max_turns:
            turn_count += 1
            tool_results = []
            tool_names = []
            
            # Execute each tool call
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_names.append(tool_name)
                    
                    if verbose:
                        params_str = _format_params(tool_input)
                        console.print(f"[dim]🔧 Calling: {tool_name}({params_str})[/dim]")
                    
                    # Execute tool
                    result = await executor.execute_tool(tool_name, tool_input)
                    
                    # Update metrics
                    session.update_tool_metrics(
                        tool_name,
                        result.success,
                        result.execution_time_seconds
                    )
                    
                    if not result.success:
                        console.print(f"[yellow]⚠️  Tool error: {result.error}[/yellow]")
                        if result.suggestion and verbose:
                            console.print(f"[dim]💡 Tip: {result.suggestion}[/dim]")
                    elif verbose:
                        console.print(f"[dim]✓ Completed in {result.execution_time_seconds:.2f}s[/dim]")
                    
                    # Add tool result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": result.output if result.success else f"Error: {result.error}\n\nSuggestion: {result.suggestion or 'N/A'}"
                    })
            
            # Add assistant's response with tool calls to session
            session.add_turn("assistant", response.content, tool_calls=tool_names)
            
            # Add tool results to session
            session.add_turn("user", tool_results)
            
            # Prepare updated messages
            messages = _prepare_messages(session)
            
            # Continue conversation
            with console.status("[bold blue]🤔 Analyzing results..."):
                response = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=tools
                )
        
        # Extract final response
        assistant_message = ""
        for block in response.content:
            if block.type == "text":
                assistant_message += block.text
        
        if not assistant_message:
            assistant_message = "No response generated"
        
        # Display response
        console.print(f"\n[green]Assistant:[/green]")
        console.print(Panel(assistant_message, border_style="green", padding=(1, 2)))
        
        # Add final response to session
        session.add_turn("assistant", response.content)
        
        # Show turn limit warning if reached
        if turn_count >= max_turns:
            console.print(f"\n[yellow]⚠️  Reached maximum turn limit ({max_turns})[/yellow]")
    
    except Exception as e:
        logger.exception("Error in LLM conversation")
        console.print(f"\n[red]Error: {e}[/red]")
        
        # Check for common issues
        if "api_key" in str(e).lower():
            console.print("[yellow]💡 Tip: Check your Anthropic API key configuration[/yellow]")
        elif "rate" in str(e).lower():
            console.print("[yellow]💡 Tip: Rate limit exceeded, wait a moment and try again[/yellow]")


async def _handle_openai_turn(
    client,
    query: str,
    tools: List[Dict],
    system_prompt: str,
    session: LLMSession,
    executor: CommandExecutor,
    verbose: bool,
    max_turns: int,
    model: str
) -> None:
    """Handle one conversation turn with OpenAI tool calling loop.
    
    Args:
        client: OpenAI client
        query: User query
        tools: Available tools
        system_prompt: System prompt
        session: LLM session
        executor: Command executor
        verbose: Show tool call details
        max_turns: Maximum tool calling iterations
        model: Model name to use
    """
    # Add user message to session
    session.add_turn("user", query)
    
    # Convert tools to OpenAI format
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        })
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    turn_count = 0
    
    try:
        # Initial LLM call
        with console.status("[bold blue]🤔 Thinking..."):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None
            )
        
        message = response.choices[0].message
        
        # Tool calling loop
        while message.tool_calls and turn_count < max_turns:
            turn_count += 1
            
            # Add assistant message to messages
            messages.append(message)
            
            # Execute each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)
                
                if verbose:
                    params_str = _format_params(tool_input)
                    console.print(f"[dim]🔧 Calling: {tool_name}({params_str})[/dim]")
                
                # Execute tool
                result = await executor.execute_tool(tool_name, tool_input)
                
                # Update metrics
                session.update_tool_metrics(
                    tool_name,
                    result.success,
                    result.execution_time_seconds
                )
                
                if not result.success:
                    console.print(f"[yellow]⚠️  Tool error: {result.error}[/yellow]")
                    if result.suggestion and verbose:
                        console.print(f"[dim]💡 Tip: {result.suggestion}[/dim]")
                elif verbose:
                    console.print(f"[dim]✓ Completed in {result.execution_time_seconds:.2f}s[/dim]")
                
                # Add tool result to messages
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_name,
                    "content": result.output if result.success else f"Error: {result.error}\n\nSuggestion: {result.suggestion or 'N/A'}"
                })
            
            # Continue conversation
            with console.status("[bold blue]🤔 Analyzing results..."):
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None
                )
            
            message = response.choices[0].message
        
        # Extract final response
        assistant_message = message.content or "No response generated"
        
        # Display response
        console.print(f"\n[green]Assistant:[/green]")
        console.print(Panel(assistant_message, border_style="green", padding=(1, 2)))
        
        # Add final response to session
        session.add_turn("assistant", assistant_message)
        
        # Show turn limit warning if reached
        if turn_count >= max_turns:
            console.print(f"\n[yellow]⚠️  Reached maximum turn limit ({max_turns})[/yellow]")
    
    except Exception as e:
        logger.exception("Error in OpenAI conversation")
        console.print(f"\n[red]Error: {e}[/red]")
        
        # Check for common issues
        if "api_key" in str(e).lower():
            console.print("[yellow]💡 Tip: Check your OpenAI API key configuration[/yellow]")
        elif "rate" in str(e).lower():
            console.print("[yellow]💡 Tip: Rate limit exceeded, wait a moment and try again[/yellow]")


def _prepare_messages(session: LLMSession) -> List[Dict]:
    """Prepare messages in Anthropic format from session history.
    
    Args:
        session: LLM session
        
    Returns:
        List of messages in Anthropic format
    """
    messages = []
    
    for turn in session.conversation_history:
        messages.append({
            "role": turn.role,
            "content": turn.content
        })
    
    return messages


def _build_system_prompt(registry: ToolRegistry, categories: Optional[List[str]] = None) -> str:
    """Build system prompt for LLM.
    
    Args:
        registry: Tool registry
        categories: Optional category filter
        
    Returns:
        System prompt string
    """
    tool_count = len(registry.get_anthropic_tools(categories=categories, safe_only=True))
    category_list = ", ".join(categories) if categories else "schema, dataset, dataflow"
    
    return f"""You are an expert Adobe Experience Platform (AEP) assistant with access to CLI tools.

Available tool categories: {category_list}
Total tools available: {tool_count} (read-only operations only)

Your role:
- Help users query and analyze AEP resources using natural language
- Use appropriate tools to gather information
- Synthesize results into clear, actionable insights
- Format data in readable tables when showing multiple items
- Ask clarifying questions when needed

Important constraints:
- Phase 1: Only read-only operations are supported for safety
- Cannot create, update, or delete AEP resources
- Cannot upload or ingest data
- All dataflow IDs can be referenced by their number from list commands (e.g., "dataflow 1" instead of full UUID)

When answering:
1. Determine which tool(s) would best answer the question
2. Call tools with appropriate parameters
3. Analyze the results carefully
4. Provide a natural language summary
5. Include relevant metrics and key findings
6. Suggest follow-up actions when appropriate

Response format:
- Be concise but informative
- Use bullet points for lists
- Highlight important metrics with emphasis
- Provide context for technical terms
- Always include actionable next steps when relevant

Remember: Users may use Korean or English - respond in the same language as the query."""


def _show_welcome(registry: ToolRegistry, categories: Optional[List[str]], model: str, provider: str) -> None:
    """Show welcome message for interactive mode.
    
    Args:
        registry: Tool registry
        categories: Optional category filter
        model: Model name
        provider: AI provider (openai or anthropic)
    """
    tool_count = registry.get_tool_count(safe_only=True)
    category_list = ", ".join(categories) if categories else "all"
    
    provider_emoji = "🤖" if provider == "anthropic" else "🧠"
    provider_name = "Claude" if provider == "anthropic" else "ChatGPT"
    
    welcome_text = f"""[bold cyan]{provider_emoji} AEP LLM Assistant[/bold cyan]

[green]Provider:[/green] {provider_name} ({provider})
[green]Model:[/green] {model}
[green]Available tools:[/green] {tool_count} (read-only)
[green]Categories:[/green] {category_list}

[yellow]Phase 1:[/yellow] Safety first - only read-only operations enabled

[dim]Commands:[/dim]
  [cyan]/tools[/cyan]  - Show available tools
  [cyan]/clear[/cyan]  - Reset conversation
  [cyan]/stats[/cyan]  - Show session statistics
  [cyan]/help[/cyan]   - Show this help
  [cyan]exit[/cyan]    - Exit assistant

[dim]Examples:[/dim]
  "list my schemas"
  "show failing dataflows from last 7 days"
  "what datasets are enabled for profile?"
  "analyze dataflow health for flow 1"

[dim]Tip: Change provider with --provider flag:[/dim]
  [cyan]aep llm chat --provider {"openai" if provider == "anthropic" else "anthropic"}[/cyan]
"""
    
    console.print(Panel(welcome_text, border_style="cyan", padding=(1, 2)))


def _show_available_tools(registry: ToolRegistry, categories: Optional[List[str]]) -> None:
    """Show table of available tools.
    
    Args:
        registry: Tool registry
        categories: Optional category filter
    """
    table = Table(title="Available Tools")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Category", style="yellow")
    table.add_column("Description", style="dim")
    
    tool_names = registry.list_tools(safe_only=True)
    
    if categories:
        # Filter by categories
        all_categories = categories
    else:
        all_categories = registry.get_categories()
    
    for category in sorted(all_categories):
        category_tools = [name for name in tool_names if f"aep_{category}_" in name]
        
        for tool_name in sorted(category_tools):
            tool_def = registry.get_tool(tool_name)
            if tool_def:
                # Shorten description for display
                desc = tool_def.description
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                
                table.add_row(
                    tool_name.replace(f"aep_{category}_", ""),
                    category,
                    desc
                )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(tool_names)} tools[/dim]")


def _show_session_stats(session: LLMSession) -> None:
    """Show session statistics.
    
    Args:
        session: LLM session
    """
    stats_text = f"""[bold cyan]Session Statistics[/bold cyan]

[green]Session ID:[/green] {session.session_id}
[green]Conversation turns:[/green] {len(session.conversation_history)}
[green]Tools used:[/green] {len(session.tool_metrics)}
[green]Total tool calls:[/green] {sum(m.call_count for m in session.tool_metrics.values())}
"""
    
    if session.tool_metrics:
        stats_text += "\n[bold cyan]Tool Usage:[/bold cyan]\n"
        
        # Sort by call count
        sorted_tools = sorted(
            session.tool_metrics.values(),
            key=lambda m: m.call_count,
            reverse=True
        )
        
        for metrics in sorted_tools[:10]:  # Top 10
            success_rate = (metrics.success_count / metrics.call_count * 100) if metrics.call_count > 0 else 0
            stats_text += f"\n  [cyan]{metrics.tool_name}[/cyan]"
            stats_text += f"\n    Calls: {metrics.call_count} | Success: {metrics.success_count} | Failed: {metrics.failure_count}"
            stats_text += f"\n    Success rate: {success_rate:.1f}% | Avg time: {metrics.average_execution_time:.2f}s"
    
    console.print(Panel(stats_text, border_style="blue", padding=(1, 2)))


def _show_help() -> None:
    """Show help information."""
    help_text = """[bold cyan]LLM Assistant Help[/bold cyan]

[yellow]Commands:[/yellow]
  [cyan]/tools[/cyan]   - Show all available tools and their descriptions
  [cyan]/clear[/cyan]   - Clear conversation history (fresh start)
  [cyan]/stats[/cyan]   - Show session statistics and tool usage
  [cyan]/help[/cyan]    - Show this help message
  [cyan]exit[/cyan]     - Exit the assistant

[yellow]Tips:[/yellow]
  • Be specific in your questions for better results
  • You can reference dataflows by number (e.g., "check dataflow 1")
  • Use verbose mode (--verbose) to see tool calls
  • Conversation history helps the AI understand context
  • Clear history if you want to start a new topic

[yellow]Examples:[/yellow]
  "list all schemas and show their classes"
  "what dataflows failed in the last week?"
  "show me datasets that are Profile-enabled"
  "analyze the health of dataflow number 3"
  "how many schemas do I have for ExperienceEvents?"

[yellow]Phase 1 Limitation:[/yellow]
  Only read-only operations are available. You cannot:
  • Create or modify schemas
  • Create datasets or batches
  • Upload or ingest data
  • Modify dataflows
"""
    
    console.print(Panel(help_text, border_style="yellow", padding=(1, 2)))


def _format_params(params: Dict[str, Any]) -> str:
    """Format parameters for display.
    
    Args:
        params: Parameter dictionary
        
    Returns:
        Formatted string
    """
    parts = []
    for key, value in params.items():
        if isinstance(value, str):
            parts.append(f'{key}="{value}"')
        else:
            parts.append(f'{key}={value}')
    
    result = ", ".join(parts)
    if len(result) > 60:
        return result[:57] + "..."
    return result


if __name__ == "__main__":
    llm_app()
