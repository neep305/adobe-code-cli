# LLM Mode - AI-Powered Interactive Assistant

## Overview

LLM Mode enables natural language interaction with Adobe Experience Platform through Claude AI. Instead of memorizing CLI commands, you can simply ask questions in plain English (or Korean).

**Status**: Phase 1 - Safety First (Read-only operations only)

## Features

### Phase 1 (Current)
- ✅ Natural language queries for AEP resources
- ✅ Interactive conversation mode
- ✅ One-shot query mode
- ✅ 11 read-only tools (schema, dataset, dataflow operations)
- ✅ Tool calling with automatic parameter extraction
- ✅ Error categorization with helpful suggestions
- ✅ Session history management
- ✅ Tool usage statistics

### Future Phases
- ⏳ Phase 2: Write operations with confirmation prompts
- ⏳ Phase 3: Multi-step workflows and planning
- ⏳ Phase 4: Session persistence and analytics

## Quick Start

### Prerequisites

1. **AEP Credentials**: Configure AEP authentication
   ```bash
   aep init
   ```

2. **Anthropic API Key**: Set your Claude API key
   ```bash
   aep ai set-key anthropic
   # OR set environment variable:
   # export ANTHROPIC_API_KEY=sk-ant-...
   ```

### Usage

#### Interactive Mode

Start a conversation session with Claude:

```bash
aep llm chat
```

Example conversation:
```
You: list my schemas
Assistant: [Lists all XDM schemas with details]

You: show me the failing dataflows from last week
Assistant: [Analyzes dataflow health and shows failures]

You: how many datasets are Profile-enabled?
Assistant: [Queries datasets and provides count]

You: exit
```

#### One-Shot Mode

Execute a single query:

```bash
# Simple query
aep llm chat "list my schemas"

# Complex analysis
aep llm chat "show failing dataflows from last 7 days"

# Aggregation queries
aep llm chat "how many datasets are enabled for profile?"
```

#### Category Filtering

Restrict tools to specific categories:

```bash
# Only schema and dataset tools
aep llm chat --tools schema,dataset "analyze my data structure"

# Only dataflow tools
aep llm chat --tools dataflow "check all dataflow health"
```

#### Verbose Mode

See tool calls and execution details:

```bash
aep llm chat --verbose "check dataflow health"
```

## Available Tools

### Schema Tools (3)
- `aep_schema_list` - List all XDM schemas
- `aep_schema_get` - Get detailed schema definition
- `aep_schema_analyze_dataset` - Analyze multi-entity structure

### Dataset Tools (2)
- `aep_dataset_list` - List all datasets
- `aep_dataset_get` - Get detailed dataset information

### Dataflow Tools (6)
- `aep_dataflow_list` - List all dataflows
- `aep_dataflow_get` - Get dataflow details
- `aep_dataflow_runs` - List dataflow execution runs
- `aep_dataflow_failures` - Show failed runs only
- `aep_dataflow_health` - Analyze health metrics
- `aep_dataflow_connections` - Show connection details

## Interactive Commands

Within a chat session, use these commands:

- `/tools` - Show all available tools
- `/clear` - Clear conversation history (fresh start)
- `/stats` - Show session statistics and tool usage
- `/help` - Show help information
- `exit` or `quit` - Exit the assistant

## Example Queries

### Schema Queries
```
"list all schemas for Profile"
"show me the customer profile schema"
"what fields are in schema xyz?"
"how many schemas do I have?"
```

### Dataset Queries
```
"list datasets enabled for Profile"
"show me dataset 123abc details"
"what's the batch history for dataset xyz?"
"how many datasets do I have?"
```

### Dataflow Queries
```
"show all failing dataflows"
"analyze dataflow health for flow 1"
"what dataflows ran in the last 24 hours?"
"show me error details for failed dataflow runs"
"which dataflows have low success rates?"
```

### Complex Queries
```
"show me schemas with more than 100 fields"
"what datasets were created this week?"
"analyze the health of all my dataflows and show top 5 issues"
"compare success rates across dataflows"
```

## How It Works

### Architecture

```
User Query (Natural Language)
    ↓
[Anthropic Claude API]
    ↓ Decides which tools to call
[Tool Registry] - Converts CLI commands → Anthropic tools
    ↓
[Safety Check] - Blocks unsafe operations (Phase 1)
    ↓
[Parameter Validation] - Validates types and required fields
    ↓
[Command Executor] - Executes CLI function
    ↓ Captures output
[Tool Result] - Success/error with execution time
    ↓
[Claude API] - Synthesizes natural language response
    ↓
User sees final answer
```

### Safety Enforcement

**Phase 1**: Only SAFE_TOOLS are allowed (11 read-only operations)

**Blocked operations**:
- Creating, updating, or deleting schemas
- Creating datasets or batches
- Uploading or ingesting data
- Modifying dataflows
- All other write operations

Attempting unsafe operations returns:
```
Error: This tool is not allowed in Phase 1 (read-only mode).
Only safe, read-only operations are currently supported.
```

### Error Handling

The system categorizes errors into 7 types with actionable suggestions:

- **AUTH_ERROR**: "Run 'aep auth status' to check credentials"
- **NOT_FOUND**: "Verify the ID exists with list command"
- **PERMISSION_ERROR**: "Check your AEP role permissions"
- **RATE_LIMIT**: "Wait a moment and try again"
- **NETWORK_ERROR**: "Check internet connection"
- **VALIDATION_ERROR**: "Check parameter format in documentation"
- **EXECUTION_ERROR**: Generic error with details

## Configuration

### Model Selection

Use a different Claude model:

```bash
aep llm chat --model claude-3-opus-20240229 "complex query"
```

Available models:
- `claude-3-5-sonnet-20241022` (default, recommended)
- `claude-3-opus-20240229` (most capable, slower)
- `claude-3-haiku-20240307` (fastest, less capable)

### Turn Limits

Prevent infinite loops with tool calling:

```bash
aep llm chat --max-turns 20 "complex multi-step query"
```

Default: 10 turns

## Advanced Usage

### Session Management

Tool usage statistics are preserved throughout a session:

```
You: /stats

Session Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Session ID: 550e8400-e29b-41d4-a716-446655440000
Conversation turns: 12
Tools used: 5
Total tool calls: 18

Tool Usage:
  aep_schema_list
    Calls: 3 | Success: 3 | Failed: 0
    Success rate: 100.0% | Avg time: 0.45s
  
  aep_dataflow_health
    Calls: 2 | Success: 2 | Failed: 0
    Success rate: 100.0% | Avg time: 1.23s
```

### Clearing History

To start fresh without context:

```
You: /clear
💬 Conversation history cleared
```

Note: Tool metrics are preserved for session statistics.

## Troubleshooting

### "Anthropic API key not configured"

Set your API key:
```bash
aep ai set-key anthropic
# Enter key when prompted
```

Or set environment variable:
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

### "Rate limit exceeded"

Wait 30-60 seconds between requests. Consider using a lower-tier model:
```bash
aep llm chat --model claude-3-haiku-20240307 "query"
```

### "Tool execution failed"

Enable verbose mode to see details:
```bash
aep llm chat --verbose "query that failed"
```

### No response from Claude

Check:
1. Internet connection
2. API key validity: `aep ai status`
3. AEP credentials: `aep auth status`

## Best Practices

### Writing Effective Queries

**Good**:
- "list all schemas for Profile class"
- "show failing dataflows from last 7 days"
- "what's the success rate of dataflow 123?"

**Less Effective**:
- "schemas" (too vague)
- "fix my dataflow" (cannot modify in Phase 1)
- "show me everything" (too broad)

### Using Context

Claude remembers conversation context:

```
You: list my dataflows
Assistant: [Shows 10 dataflows]

You: show health for dataflow 3
Assistant: [Analyzes third dataflow from previous list]

You: what about dataflow 7?
Assistant: [Knows you mean health check]
```

### Performance Tips

1. **Category filtering**: Reduces tool count, faster responses
   ```bash
   aep llm chat --tools dataflow "dataflow queries only"
   ```

2. **One-shot mode**: Faster for single queries
   ```bash
   aep llm chat "single query here"
   ```

3. **Clear history**: Reduces context size for faster processing
   ```
   You: /clear
   ```

## Development

### Adding New Tools

1. **Create CLI command** in appropriate module
2. **Register tool** in `src/adobe_experience/cli/llm_tools/__init__.py`:
   ```python
   registry.register_from_typer_command(
       command_name="my_command",
       typer_command=module.my_function,
       category="category",
       description="Clear description of what this does"
   )
   ```
3. **Add to SAFE_TOOLS** or **DESTRUCTIVE_TOOLS** in `safety.py`
4. **Test** tool registration and execution

### Testing

Run LLM tools tests:
```bash
pytest tests/test_llm_tools.py -v
```

Test categories:
- `TestSafety`: Safety classification
- `TestToolRegistry`: Tool registration and Anthropic format
- `TestCommandExecutor`: Execution and error handling
- `TestLLMSession`: Session management

## Limitations (Phase 1)

- ❌ Cannot create, update, or delete resources
- ❌ Cannot upload or ingest data
- ❌ No multi-step workflow planning
- ❌ No session persistence across CLI invocations
- ❌ Limited to read-only operations

Future phases will address these limitations with appropriate safety controls.

## Roadmap

### Phase 2: Confirmation Prompts
- Write operations with user confirmation
- Preview changes before execution
- Rollback capabilities

### Phase 3: Multi-Step Workflows
- Complex task planning
- Sequential tool execution
- Dependency management

### Phase 4: Advanced Features
- Session persistence (save/load)
- Tool result caching
- Advanced analytics dashboard
- Custom tool definitions

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs: Enable `--verbose` mode
3. Test credentials: `aep auth status` and `aep ai status`
4. Check AEP API status: Visit Adobe Status page

## License

See [LICENSE](../LICENSE) file for details.
