# Dataflow Query Examples

This guide demonstrates how to use the AEP dataflow query functionality to monitor and analyze data ingestion pipelines.

## Overview

The dataflow functionality allows you to:
- List all dataflows in your AEP organization
- Get detailed information about specific dataflows
- Monitor dataflow execution runs
- Analyze dataflow health and performance
- Inspect source and target connections
- Identify and troubleshoot failures

## CLI Commands

### 1. List Dataflows

List all dataflows in your organization:

```bash
# List 20 dataflows (default)
aep dataflow list

# List more dataflows
aep dataflow list --limit 50

# Filter by state
aep dataflow list --state enabled
aep dataflow list --state disabled

# Output as JSON for programmatic use
aep dataflow list --json
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Name                       ┃ ID                      ┃ State   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Customer Data Ingestion    │ d8a68c9e-1d5f-4b6c...  │ enabled │
│ Product Catalog Sync       │ a1b2c3d4-e5f6-7890...  │ enabled │
└────────────────────────────┴─────────────────────────┴─────────┘
```

### 2. Get Dataflow Details

View comprehensive information about a specific dataflow:

```bash
# Get dataflow details
aep dataflow get d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a

# Get as JSON
aep dataflow get d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --json
```

Output shows:
- Dataflow name, ID, and state
- Creation and update timestamps
- Flow specification
- Source and target connection IDs
- Schedule configuration (frequency, interval)
- Inherited connection details

### 3. View Dataflow Runs

List execution history for a dataflow:

```bash
# List recent runs
aep dataflow runs d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a

# List more runs
aep dataflow runs d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --limit 50

# Filter by date range (last 7 days)
aep dataflow runs d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --days 7

# Output as JSON
aep dataflow runs d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --json
```

Output includes:
- Run ID and status
- Creation timestamp
- Records read/written metrics
- Execution duration
- Color-coded status (green=success, red=failed, yellow=in progress)

### 4. Analyze Failed Runs

Focus on failed runs to troubleshoot issues:

```bash
# List only failed runs
aep dataflow failures d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a

# Output as JSON for analysis
aep dataflow failures d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --json
```

Output shows:
- Failed run details
- Error codes and messages
- Records processed before failure
- Detailed error information

### 5. Inspect Connections

View source and target connection details:

```bash
# Get all connection details
aep dataflow connections d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a

# Output as JSON
aep dataflow connections d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --json
```

Shows:
- Source connection type (S3, Salesforce, etc.)
- Source parameters (bucket name, folder path, etc.)
- Target connection (usually AEP Data Lake)
- Target dataset ID
- Base connection IDs

### 6. Health Analysis

Get comprehensive health metrics for a dataflow:

```bash
# Analyze health (last 7 days by default)
aep dataflow health d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a

# Analyze longer period
aep dataflow health d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --days 30

# Output as JSON
aep dataflow health d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a --json
```

Provides:
- Total runs in analysis period
- Success rate percentage
- Failed run count
- Average execution duration
- Common error patterns
- Health assessment (Excellent/Good/Poor/Critical)

## Python API Usage

You can also use the dataflow functionality programmatically:

```python
import asyncio
from adobe_experience.aep.client import AEPClient
from adobe_experience.core.config import get_config
from adobe_experience.flow.client import FlowServiceClient

async def main():
    # Initialize client
    async with AEPClient(get_config()) as aep_client:
        flow_client = FlowServiceClient(aep_client)
        
        # List dataflows
        dataflows = await flow_client.list_dataflows(
            limit=50,
            property_filter="state==enabled"
        )
        
        for flow in dataflows:
            print(f"{flow.name}: {flow.state.value}")
        
        # Get specific dataflow
        if dataflows:
            flow_id = dataflows[0].id
            flow = await flow_client.get_dataflow(flow_id)
            print(f"\nDataflow: {flow.name}")
            print(f"State: {flow.state}")
            
            # Get recent runs
            runs = await flow_client.list_runs(flow_id, limit=10)
            print(f"Recent runs: {len(runs)}")
            
            # Analyze health
            health = await flow_client.analyze_dataflow_health(
                flow_id,
                lookback_days=7
            )
            print(f"Success rate: {health['success_rate']:.1f}%")
            print(f"Failed runs: {health['failed_runs']}")

asyncio.run(main())
```

## Use Cases

### 1. Daily Monitoring

Create a daily monitoring script:

```bash
#!/bin/bash
# Monitor all enabled dataflows

echo "=== Dataflow Health Report ==="
date

# Get all enabled dataflows
FLOWS=$(aep dataflow list --state enabled --json | jq -r '.[].id')

for flow_id in $FLOWS; do
    echo "Checking $flow_id..."
    aep dataflow health "$flow_id" --days 1
done
```

### 2. Failure Investigation

When a dataflow fails:

```bash
# 1. Check current state
aep dataflow get <FLOW_ID>

# 2. View recent failures
aep dataflow failures <FLOW_ID> --limit 10

# 3. Inspect connections (verify credentials, paths)
aep dataflow connections <FLOW_ID>

# 4. Check overall health trend
aep dataflow health <FLOW_ID> --days 30
```

### 3. Performance Analysis

Analyze dataflow performance over time:

```python
from datetime import datetime, timedelta
from adobe_experience.flow.client import FlowServiceClient
from adobe_experience.aep.client import AEPClient

async def analyze_performance(flow_id: str):
    async with AEPClient() as client:
        flow_client = FlowServiceClient(client)
        
        # Get runs from last 30 days
        start_date = datetime.now() - timedelta(days=30)
        runs = await flow_client.list_runs_by_date_range(
            flow_id,
            start_date=start_date,
            limit=100
        )
        
        # Calculate metrics
        durations = []
        for run in runs:
            if run.metrics and run.metrics.duration_summary:
                ds = run.metrics.duration_summary
                if ds.started_at_utc and ds.completed_at_utc:
                    duration = (ds.completed_at_utc - ds.started_at_utc) / 1000.0
                    durations.append(duration)
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            print(f"Average duration: {avg_duration:.1f}s")
            print(f"Max duration: {max_duration:.1f}s")
            print(f"Min duration: {min_duration:.1f}s")
```

### 4. Alerting

Set up alerts for dataflow issues:

```python
async def check_and_alert(flow_id: str, threshold: float = 80.0):
    """Alert if success rate drops below threshold."""
    async with AEPClient() as client:
        flow_client = FlowServiceClient(client)
        
        health = await flow_client.analyze_dataflow_health(
            flow_id,
            lookback_days=7
        )
        
        if health['success_rate'] < threshold:
            # Send alert
            print(f"ALERT: Dataflow {flow_id} success rate is {health['success_rate']:.1f}%")
            print(f"Failed runs: {health['failed_runs']}")
            
            # Get error details
            if health['errors']:
                print("Recent errors:")
                for error in health['errors'][:5]:  # Top 5 errors
                    print(f"  - {error['code']}: {error['message']}")
```

## Tips and Best Practices

1. **Regular Monitoring**: Check dataflow health daily using the `health` command
2. **JSON Output**: Use `--json` flag for programmatic processing with tools like `jq`
3. **Date Filtering**: Use `--days` parameter to focus on recent activity
4. **Connection Verification**: Regularly inspect connections to catch credential expiration
5. **Error Analysis**: Group errors by code to identify patterns
6. **Performance Tracking**: Monitor average duration trends to detect degradation
7. **Pagination**: Use appropriate `--limit` values for large result sets

## Troubleshooting

### "No dataflows found"
- Verify you have the correct sandbox selected (check `.env` file)
- Ensure your credentials have permissions to access Flow Service
- Check if dataflows exist in your organization

### "Error: 404 Not Found"
- Verify the dataflow ID is correct
- Check if the dataflow was deleted
- Ensure you're in the correct sandbox

### "Rate limit exceeded (429)"
- The client automatically retries with exponential backoff
- Consider adding delays between bulk operations
- Contact Adobe if limits are consistently hit

### Authentication errors
- Run `aep onboarding status` to verify credentials
- Check that credentials haven't expired
- Ensure all required permissions are granted

## Reference

For more information:
- [Flow Service API Documentation](../src/adobe_experience/api-spec/flow-service/FLOW_SERVICE_API.md)
- [Adobe Flow Service Reference](https://developer.adobe.com/experience-platform-apis/references/flow-service/)
- [Sources Documentation](https://experienceleague.adobe.com/en/docs/experience-platform/sources/home)
