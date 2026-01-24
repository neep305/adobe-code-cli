# Adobe AEP CLI Agent - AI Coding Instructions

## Project Purpose
AI-powered CLI agent for automating Adobe Experience Platform (AEP) integration tasks. Goes beyond simple API calls by using inference at every step: schema design, data ingestion, validation, and post-processing. Think "Claude Code for Adobe services."

**Development Priority**: Schema management first (prerequisite for ingestion), then data ingestion pipelines.

Future expansion: Adobe Target, Adobe Analytics (after AEP is stable).

## Core Architecture

### Agent-Based Workflow (AI-Powered at Each Step)
- **Inference engine**: Analyzes user intent and AEP requirements; uses LLM tool calling for decision-making
- **CLI interface**: Natural language + structured commands for developers/data engineers
- **AEP connectors**: Handles authentication, API communication, batch operations
- **Schema analyzer**: AI-driven XDM schema generation from sample data or descriptions
- **Data pipeline**: AI validates, transforms, maps data to XDM before ingestion

### Key Components (Development Order)
```
adobe-code/
├── src/
│   ├── agent/          # AI inference engine (LLM integration, tool calling)
│   ├── schema/         # [PRIORITY 1] XDM schema analyzer & generator
│   ├── aep/            # Adobe Experience Platform API client
│   ├── ingestion/      # [PRIORITY 2] Data ingestion pipelines (after schema)
│   ├── processors/     # Data transformation and validation
│   └── cli/            # Typer CLI commands (wraps agent logic)
├── tests/
│   ├── fixtures/       # Sample XDM schemas and test datasets
│   └── integration/    # AEP sandbox integration tests
└── examples/           # Example workflows and use cases
```

## Adobe Experience Platform Context

### Critical AEP Concepts
- **XDM (Experience Data Model)**: Standard schema format - all data must conform to XDM
- **Datasets**: Collections of data with associated schemas
- **Batch ingestion**: Upload large datasets via API or streaming
- **Identity namespaces**: Critical for customer identity resolution
- **Sandboxes**: Isolated environments (prod/dev/staging)

### Authentication Flow
Use OAuth Server-to-Server credentials (not JWT - deprecated in 2024). Store credentials securely, never in code.
- Required: `client_id`, `client_secret`, `org_id`, `technical_account_id`, `scopes`
- Token endpoint: `https://ims-na1.adobelogin.com/ims/token/v3`

### Common API Patterns
- Base URL: `https://platform.adobe.io/data/foundation/...`
- Required headers: `Authorization`, `x-api-key`, `x-gw-ims-org-id`, `x-sandbox-name`
- Rate limiting: Implement exponential backoff for 429 responses
- Pagination: Use `_page` and `limit` parameters

## Development Patterns

### CLI Design
Use **Typer** or **Click** for CLI framework. Structure commands by domain:
```python
# adobe-aep ingest csv --file data.csv --dataset my-dataset --auto-schema
# adobe-aep schema create --from-sample data.json --name "Customer Events"
# adobe-aep analyze --dataset my-dataset --suggest-improvements
```

### AI Agent Integration (Tool-Using Pattern)
- **Schema generation**: LLM analyzes sample data/CSV headers → generates XDM-compliant schema
- **Data validation**: AI infers quality rules (nullability, data types, enum values)
- **Ingestion strategy**: AI suggests batch size, parallelization based on data volume
- **Identity resolution**: AI recommends identity namespaces from data patterns
- **Natural language interface**: "Create schema for this customer data and ingest with email as primary identity"

Use LLM tool calling (Anthropic/OpenAI function calling) to invoke AEP APIs, not direct code generation.

### Error Handling
- AEP returns detailed error objects - parse and present actionable messages
- Distinguish between retryable (503, 429) and non-retryable (400, 403) errors
- Log all API requests for debugging (sanitize credentials)

### Testing Strategy
- Unit tests: Mock AEP API responses
- Integration tests: Use AEP sandbox environment
- Include example datasets in `tests/fixtures/`
- Test schema validation extensively (XDM compliance is strict)

## Code Conventions

### Configuration Management
Store AEP credentials in:
1. Environment variables (preferred for CI/CD)
2. `~/.adobe/credentials.json` (local development)
3. CLI arguments (for automation scripts)

### Async Operations
Many AEP operations are async (batch ingestion). Implement polling with status checks:
- Return batch ID immediately
- Provide `--wait` flag to poll until completion
- Status check interval: start at 5s, increase to 30s

### Data Transformation
Support multiple input formats: CSV, JSON, Parquet, Avro
- Auto-detect format when possible
- Validate against target XDM schema before upload
- Provide data mapping DSL for complex transformations

## Key Files to Reference (once created)
- `src/schema/xdm.py` - [START HERE] XDM schema validator and AI-powered generator
- `src/agent/inference.py` - LLM integration and tool calling orchestration
- `src/aep/client.py` - AEP API client with retry logic and auth
- `src/cli/schema.py` - CLI commands for schema operations
- `examples/schema-generation.md` - Example: sample data → XDM schema workflow

## Dependencies
- **httpx** or **aiohttp**: Async HTTP client
- **pydantic**: Data validation and settings
- **typer**: CLI framework
- **anthropic/openai**: LLM integration
- **pandas**: Data manipulation (optional, for complex transforms)

## Resources

### Essential AEP Documentation
- **Main Docs**: https://experienceleague.adobe.com/en/docs/experience-platform
- **API Reference**: https://developer.adobe.com/experience-platform-apis/
- **API Authentication**: https://experienceleague.adobe.com/en/docs/platform-learn/tutorials/platform-api-authentication
- **XDM Schemas**: https://experienceleague.adobe.com/en/docs/experience-platform/xdm/home
- **Data Ingestion**: https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/home
- **Batch Ingestion**: https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/batch/overview.html
- **Identity Service**: https://experienceleague.adobe.com/en/docs/experience-platform/identity/home
- **Catalog Service**: https://experienceleague.adobe.com/en/docs/experience-platform/catalog/home
- **Datasets**: https://experienceleague.adobe.com/en/docs/experience-platform/catalog/datasets/overview
- **Sandboxes**: https://experienceleague.adobe.com/en/docs/experience-platform/sandbox/home

### Developer Tools
- **Postman Collections**: https://github.com/adobe/experience-platform-postman-samples
- **Adobe Developer Console**: https://developer.adobe.com/developer-console/
