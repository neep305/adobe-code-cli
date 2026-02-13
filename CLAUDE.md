# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered CLI agent for automating Adobe Experience Platform (AEP) integration tasks. Uses LLM inference at every step: schema design, data validation, identity resolution, and ingestion strategy recommendations.

**Current Priority**: Schema management (Priority 1) - prerequisite for data ingestion pipelines (Priority 2).

## Commands

```bash
# Installation
pip install -e .              # Standard install
pip install -e ".[dev]"       # With dev dependencies
pip install -e ".[data]"      # With pandas/pyarrow for data processing

# Testing
pytest                        # Run all tests
pytest tests/test_schema.py   # Run specific test file
pytest -v                     # Verbose output
pytest --cov=src              # With coverage

# Code Quality
black src/ tests/             # Format code
ruff check src/ tests/        # Lint
mypy src/                     # Type checking

# CLI Usage
aep init                # Interactive setup wizard
aep auth test           # Test AEP credentials
aep schema create       # Create XDM schema from sample data
aep schema list         # List schemas
aep schema get [id]     # Get schema details
```

## Architecture

```
src/adobe_aep/
├── agent/inference.py    # AI inference engine - LLM integration for schema analysis
├── schema/
│   ├── models.py         # Pydantic models for XDM schema definitions
│   └── xdm.py            # XDMSchemaAnalyzer (type inference, format detection)
├── aep/client.py         # AEP API client (authentication, HTTP)
├── cli/
│   ├── main.py           # Main CLI commands (schema operations)
│   ├── auth.py           # Authentication commands
│   └── init.py           # Interactive setup wizard
└── config.py             # Configuration and credential management
```

**Data Flow**: CLI commands → Config loading → AIInferenceEngine (Claude API) + XDMSchemaAnalyzer → AEP API

## Adobe Experience Platform Context

- **XDM (Experience Data Model)**: All data must conform to XDM schemas
- **Authentication**: OAuth Server-to-Server credentials (not JWT - deprecated)
- **Required Headers**: `Authorization`, `x-api-key`, `x-gw-ims-org-id`, `x-sandbox-name`
- **Base URL**: `https://platform.adobe.io/data/foundation/...`
- **Token Endpoint**: `https://ims-na1.adobelogin.com/ims/token/v3`

## Configuration

Credentials are loaded in priority order:
1. Environment variables (preferred for CI/CD)
2. `~/.adobe/credentials.json` (local development)
3. CLI arguments

Required environment variables (see `.env.example`):
- `AEP_CLIENT_ID`, `AEP_CLIENT_SECRET`, `AEP_ORG_ID`, `AEP_TECHNICAL_ACCOUNT_ID`
- `ANTHROPIC_API_KEY`
- `AEP_SANDBOX_NAME` (default: "prod")

## Code Conventions

- **Type hints**: Required throughout (`disallow_untyped_defs = true` in mypy)
- **Formatting**: Black with 100 char line length
- **Validation**: Pydantic models for all data structures
- **HTTP**: Use httpx for async operations
- **Error handling**: Distinguish retryable (429, 503) vs non-retryable (400, 403) AEP errors

## Key Pydantic Models

- `XDMSchema` - Complete schema definition
- `XDMField` - Individual field with type, format, constraints
- `XDMDataType` - Enum: string, number, boolean, object, array
- `XDMFieldFormat` - Enum: email, uri, date, date-time, uuid
- `AEPConfig` - Configuration and credentials
