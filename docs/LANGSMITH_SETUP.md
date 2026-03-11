# LangSmith Integration Guide

## Overview

LangSmith is integrated into the Adobe AEP CLI for observability and debugging of AI-powered workflows. It provides:
- **Request/Response Tracing**: Track all LLM calls with inputs/outputs
- **Supervisor Flow Visualization**: See how the supervisor routes and executes agents
- **Performance Monitoring**: Measure latency and identify bottlenecks
- **Error Debugging**: Capture and analyze failures in agent execution

## Features

### 🔒 Security-First Design
- **Opt-in by default**: LangSmith is disabled unless explicitly enabled
- **Automatic sanitization**: Sensitive data (API keys, passwords, tokens) are masked
- **Graceful fallback**: If LangSmith is unavailable, the CLI continues without errors

### 📊 What's Traced

1. **Supervisor Routing** (`supervisor.run`)
   - Intent classification
   - Route selection (analysis/schema/mixed)
   - Confidence scores
   - Selected agents

2. **Agent Execution** (`supervisor.run_agent`)
   - Individual agent runs
   - Input context
   - Output results
   - Execution status

3. **Tool Calls** (`supervisor.execute_tool_calls`)
   - AEP API calls
   - Success/failure rates
   - Tool call payloads

## Setup

### 1. Create LangSmith Account

1. Go to https://smith.langchain.com
2. Sign up for a free account
3. Navigate to **Settings → API Keys**
4. Click **Create API Key**
5. Copy the generated key

### 2. Configure Environment Variables

Edit your `.env` file:

```dotenv
# LangSmith Tracing (optional, opt-in)
LANGSMITH_ENABLED=true  # Set to true to enable tracing
LANGSMITH_API_KEY=lsv2_pt_your_actual_key_here
LANGSMITH_PROJECT=adobe-aep-cli  # Optional: customize project name
```

**Important**: Never commit your `.env` file with real API keys to version control!

### 3. Verify Setup

Run a simple command to test tracing:

```bash
# Set environment variables (if not using .env)
export LANGSMITH_ENABLED=true
export LANGSMITH_API_KEY=lsv2_pt_your_key_here
export LANGSMITH_PROJECT=adobe-aep-test

# Run analysis with tracing enabled
aep analyze run \
  --intent "Analyze customer data quality" \
  --file test-data/ecommerce/customers.json \
  --output-dir output/test
```

### 4. View Traces

1. Open https://smith.langchain.com
2. Select your project (e.g., `adobe-aep-cli`)
3. Click on the latest run
4. Explore the trace tree:
   - `supervisor.run` (top-level)
     - `supervisor.execute_tool_calls` (if any)
     - `supervisor.run_agent` (for each agent)

## Usage Examples

### Example 1: Debug Analysis Route

```bash
export LANGSMITH_ENABLED=true

aep analyze run \
  --intent "analyze healthcare patient records" \
  --file test-data/healthcare/patient.json
```

**LangSmith View**: See how the supervisor classifies intent → selects `data-analysis-agent` → executes and returns structured results.

### Example 2: Mixed Route (Analysis + Schema)

```bash
aep analyze run \
  --intent "analyze ecommerce orders and generate XDM schema" \
  --file test-data/ecommerce/orders.json
```

**LangSmith View**: Two agent spans appear:
1. `data-analysis-agent` (first)
2. `schema-mapping-agent` (uses analysis results)

### Example 3: Multiple Projects

Use different projects for dev/prod environments:

```bash
# Development
export LANGSMITH_PROJECT=adobe-aep-dev
aep analyze run --intent "test analysis" --file sample.json

# Production
export LANGSMITH_PROJECT=adobe-aep-prod
aep analyze run --intent "production analysis" --file prod-data.json
```

## Architecture

### Trace Hierarchy

```
supervisor.run (chain)
├── supervisor.execute_tool_calls (tool)  # Optional
│   ├── aep_dataset_list
│   └── aep_schema_get
├── supervisor.run_agent (chain)  # data-analysis-agent
└── supervisor.run_agent (chain)  # schema-mapping-agent (if mixed)
```

### Metadata Captured

Each span includes:
- **Inputs**: Raw request payload (sanitized)
- **Outputs**: Results, confidence, warnings
- **Metadata**: Component name, request ID, timestamps
- **Tags**: Route type, agent names

### Sanitization Rules

The following keys are automatically masked:
- `api_key`, `apikey`
- `secret`, `client_secret`
- `password`, `token`
- `authorization`

Example:
```json
{
  "AEP_CLIENT_SECRET": "p8e-***-V",  // Masked
  "email": "user@example.com"        // Not masked
}
```

## Troubleshooting

### Traces Not Appearing

**Problem**: No traces visible in LangSmith dashboard

**Solutions**:
1. Verify `LANGSMITH_ENABLED=true` (not `false`, `0`, or empty)
2. Check API key is valid: `echo $LANGSMITH_API_KEY`
3. Confirm project name matches: `echo $LANGSMITH_PROJECT`
4. Check network connectivity to smith.langchain.com

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'langsmith'`

**Solution**: The `langsmith` package is already included in dependencies:
```bash
pip install -e .  # Reinstall with all dependencies
```

### Graceful Fallback

If LangSmith fails (network issues, invalid key), the CLI will:
- Continue executing normally
- Log no errors (silent fallback)
- Skip trace creation

This ensures production reliability even if observability is temporarily unavailable.

## Best Practices

### 1. Use Separate Projects

Organize traces by environment:
- `adobe-aep-dev` - Development testing
- `adobe-aep-staging` - Pre-production validation
- `adobe-aep-prod` - Production monitoring

### 2. Tag Important Runs

Add custom tags for filtering:
```python
# In code (for custom agents)
with tracer.span(
    "custom-analysis",
    inputs=data,
    tags=["production", "high-priority", "customer-facing"]
) as span:
    # ... execution
```

### 3. Monitor Confidence Scores

Use LangSmith to track agent confidence over time:
1. Export trace data
2. Filter by `confidence` in outputs
3. Identify low-confidence patterns

### 4. Disable in Performance-Critical Paths

For batch processing, consider disabling tracing:
```bash
export LANGSMITH_ENABLED=false
# Run large batch operations
```

## API Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGSMITH_ENABLED` | `false` | Enable/disable tracing |
| `LANGSMITH_API_KEY` | - | API key from smith.langchain.com |
| `LANGSMITH_PROJECT` | `adobe-aep-cli` | Project name in LangSmith |

### Python API

```python
from adobe_experience.agent.tracing import get_tracer

# Get tracer for a scope
tracer = get_tracer("my-component")

# Create a span
with tracer.span(
    "operation-name",
    inputs={"key": "value"},
    metadata={"version": "1.0"},
    run_type="chain",  # chain, tool, llm, retriever
    tags=["tag1", "tag2"]
) as span:
    # ... do work
    span.set_outputs({"result": "success"})
```

### Decorator Usage

```python
from adobe_experience.agent.tracing import trace_call

@trace_call(name="my_function", scope="processing")
def process_data(records):
    # Automatically traced
    return analyze(records)
```

## Resources

- **LangSmith Docs**: https://docs.smith.langchain.com
- **LangSmith Dashboard**: https://smith.langchain.com
- **Tracing Implementation**: [src/adobe_experience/agent/tracing.py](../src/adobe_experience/agent/tracing.py)
- **Supervisor Integration**: [src/adobe_experience/agent/supervisor_graph.py](../src/adobe_experience/agent/supervisor_graph.py)

## FAQ

**Q: Is LangSmith required to use the CLI?**  
A: No. It's completely optional and disabled by default.

**Q: Does tracing slow down execution?**  
A: Minimal overhead (~10-50ms per span). For production, test with/without tracing.

**Q: Can I trace custom agents?**  
A: Yes! Use `get_tracer()` in your agent code (see Python API above).

**Q: Are traces stored locally?**  
A: No. All traces are sent to LangSmith's cloud platform.

**Q: How long are traces retained?**  
A: Free tier: 14 days. Paid tiers: 1+ months (check LangSmith pricing).

**Q: Can I use a self-hosted LangSmith?**  
A: Yes. Set `LANGCHAIN_ENDPOINT` environment variable to your instance URL.
