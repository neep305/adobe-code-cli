# Adobe Experience Cloud CLI

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/neep305/adobe-code-cli)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

Unified AI-powered CLI for Adobe Experience Cloud products - AEP, Target, Analytics, and more.

> **Current Version**: 0.2.0  
> **Status**: Alpha - Adobe Experience Platform support available, more products coming soon  
> **Migration**: `aep` commands are deprecated, use `aep` instead

## ✨ Features

- 🔧 **Unified Interface**: Single CLI for all Adobe Experience Cloud products
- 🧠 **AI-Driven**: Uses LLM inference (OpenAI/Anthropic) for schema generation and validation
- 📊 **XDM Schema Management**: Automatically generate XDM-compliant schemas from sample data
- 📦 **Dataset Management**: Create, list, and manage AEP datasets with full lifecycle control
- 🔄 **Batch Ingestion**: Create batches, monitor status, and manage data ingestion workflows
- 🔑 **Secure Key Management**: Separate AI API key storage with `aep ai` commands
- ♻️ **Backward Compatible**: Legacy `aep` commands still supported (with deprecation warnings)
- 🎯 **Multi-Product Ready**: Designed for AEP, Target, Analytics integration
- 🛡️ **Type-Safe**: Built with Pydantic for robust data validation
- 🎨 **Rich UI**: Beautiful terminal output with colors, tables, and progress indicators

## 📦 Installation

### From Git Repository (Recommended)

Install directly from GitHub - no need to clone the repository:

```bash
# Install latest version from main branch
pip install git+https://github.com/neep305/adobe-code-cli.git

# Install specific release version
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0

# With optional data processing dependencies
pip install "adobe-experience-cloud-cli[data] @ git+https://github.com/neep305/adobe-code-cli.git"
```

### Development Installation

For contributors or local development:

```bash
# Clone the repository
git clone https://github.com/neep305/adobe-code-cli.git
cd adobe-code-cli

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Requirements

- **Python**: 3.10 or higher
- **Git**: Required for repository installation
- **Network**: Internet access for Adobe API calls

### Upgrading

Update to the latest version:

```bash
pip install --upgrade git+https://github.com/neep305/adobe-code-cli.git
```
🚀 Quick Start

### 1. Configure Credentials

**Option A: Interactive Setup (Recommended)**
```bash
aep init
```

**Option B: Environment Variables**

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Adobe Experience Platform Credentials
AEP_CLIENT_ID=your_client_id
AEP_CLIENT_SECRET=your_client_secret
AEP_ORG_ID=your_org_id@AdobeOrg
AEP_TECHNICAL_ACCOUNT_ID=your_tech_account_id@techacct.adobe.com
AEP_SANDBOX_NAME=jason-sandbox
AEP_TENANT_ID=your_tenant_id

# AI Provider Configuration
AI_PROVIDER=auto              # auto, openai, or anthropic
AI_MODEL=gpt-4o               # Default model
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
```

**Option C: Separate AI Key Storage (Recommended)**

Store AI keys separately from `.env` for better security:

```bash
# Set AI provider keys (hidden input mode)
aep ai set-key openai
# Enter key when prompted (paste with Ctrl+V/Right-click works!)

aep ai set-key anthropic

# Verify configuration
aep ai status

# Test API connectivity
aep ai test

# Set default provider (optional)
aep ai set-default openai

# List stored keys
aep ai list-keys
```📖 Command Reference

### Global Commands

```bash
aep --help              # Show all available commands
adobe version             # Show version information
aep init                # Interactive setup wizard
```

### Adobe Experience Platform (AEP)

```bash
aep --help          # AEP-specific commands
aep info            # Show AEP information

# Schema Management
aep schema create   # Create XDM schema from sample data
aep schema list     # List schemas from AEP
aep schema get      # Get schema details

# Dataset Management
aep dataset list    # List datasets
aep dataset create  # Create new dataset
aep dataset get     # Get dataset details
aep dataset enable-profile  # Enable for Profile

# Batch Management
aep dataset create-batch    # Create batch for ingestion
aep dataset batch-status    # Check batch status
aep dataset list-batches    # List batches
aep dataset complete-batch  # Complete batch
```

### AI Provider Management

```bash
# Configuration and Status
aep ai status                   # Show current AI provider configuration
aep ai status --verbose         # Show detailed configuration with file paths
aep ai test                     # Test API connectivity for configured providers
aep ai test <provider>          # Test specific provider (openai/anthropic)

# Key Management
aep ai set-key <provider>       # Set API key with hidden input (openai/anthropic)
aep ai list-keys                # List stored API keys
aep ai remove-key <provider>    # Remove API key
aep ai set-default <provider>   # Set default provider

# LLM Assistant (AI-powered)
aep llm chat                    # Interactive mode with default provider
aep llm chat --provider openai  # Use OpenAI (ChatGPT)
aep llm chat --provider anthropic  # Use Anthropic (Claude)
aep llm chat "query"            # One-shot query with default provider
aep llm chat --model gpt-4o "query"  # Use specific model
```

### Authentication

```bash
aep auth test           # Test AEP credentials
```

### Web UI Server Management

Manage the full-stack web UI (FastAPI + Next.js + PostgreSQL + Redis) directly from the CLI.

**Start web services**

```bash
# Docker mode (recommended - includes all services)
aep web start                       # Start full stack with docker-compose
aep web start --mode docker         # Same as above

# Local development mode (requires Node.js/npm)
aep web start --mode dev            # Start backend + frontend locally

# Individual services
aep web start --mode backend        # Start only backend (port 8000)
aep web start --mode frontend       # Start only frontend (port 3000)

# Custom ports
aep web start --backend-port 8080 --frontend-port 3001

# Run in background without opening browser
aep web start --detach --no-browser
```

**Check service status**

```bash
aep web status                      # Show running services with ports and PIDs
```

**View logs**

```bash
aep web logs backend                # View backend logs
aep web logs frontend               # View frontend logs
aep web logs backend --follow       # Follow logs in real-time
aep web logs frontend --tail 50     # Show last 50 lines
```

**Stop services**

```bash
aep web stop                        # Stop all services
aep web stop --mode docker          # Stop Docker services
aep web stop --mode backend         # Stop only backend
aep web stop --mode frontend        # Stop only frontend
```

**Open in browser**

```bash
aep web open                        # Open frontend (http://localhost:3000)
aep web open app                    # Same as above
aep web open api-docs               # Open API docs (http://localhost:8000/api/docs)
```

**Deployment modes:**
- **docker** (default): Best for production-like environment, includes PostgreSQL + Redis
- **dev**: Local development with hot reload
- **backend**: API server only (good for testing API endpoints)
- **frontend**: Frontend only (requires backend running separately)

### Legacy Commands (Deprecated)

```bash
# These commands still work but show deprecation warnings
ado📚 Resources

### Documentation
- [Adobe Experience Platform Docs](https://experienceleague.adobe.com/en/docs/experience-platform)
- [API Reference](https://developer.adobe.com/experience-platform-apis/)
- [XDM Schema Guide](https://experienceleague.adobe.com/en/docs/experience-platform/xdm/home)
- [API Authentication](https://experienceleague.adobe.com/en/docs/platform-learn/tutorials/platform-api-authentication)

### Project
- [Copilot Instructions](.github/copilot-instructions.md)
- [Contributing Guidelines](CONTRIBUTING.md) (coming soon)
- [Changelog](CHANGELOG.md) (coming soon)

### Adobe Developer Tools
- [Adobe Developer Console](https://developer.adobe.com/developer-console/)
- [Postman Collections](https://github.com/adobe/experience-platform-postman-samples)

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for the CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [Anthropic](https://www.anthropic.com/) and [OpenAI](https://openai.com/) for AI capabilities

---

**Note**: This is an unofficial tool and is not affiliated with or endorsed by Adobe Inc. core/           # Shared authentication, config, utilities
│   ├── auth.py     # Adobe IMS authentication client
│   ├── config.py   # Configuration management
│   └── __init__.py
├── aep/            # Adobe Experience Platform
│   ├── cli.py      # AEP CLI commands
│   └── client.py   # AEP API client
├── agent/          # AI inference engine
│   └── inference.py # OpenAI/Anthropic integration
├── schema/         # XDM schema tools
│   ├── xdm.py      # Schema analyzer and generator
│   └── models.py   # Pydantic models
├── cli/            # CLI entry points
│   ├── main.py     # Unified CLI (adobe)
│   ├── legacy.py   # Backward compatibility (aep)
│   ├── schema.py   # Schema commands
│   ├── auth.py     # Auth commands
│   ├── ai.py       # AI key management
│   └── init.py     # Interactive setup
└── (future)
    ├── target/     # Adobe Target integration (planned)
    └── analytics/  # Adobe Analytics integration (planned)
```

### Design Principles

- **Modular**: Each Adobe product is a separate module
- **Extensible**: Easy to add new products (Target, Analytics, etc.)
- **AI-Powered**: LLM inference for schema generation and validation
- **Type-Safe**: Pydantic models throughout
- **User-Friendly**: Rich terminal UI with colors and tables

## 🔄 Migration from v0.1.x

If you're upgrading from `aep` (v0.1.x):

### Command Changes

| Old (v0.1.x) | New (v0.2.0+) | Status |
|--------------|---------------|--------|
| `aep schema create` | `aep schema create` | ✅ Both work |
| `aep auth test` | `aep auth test` | ✅ Both work |
| - | `aep ai set-key` | ✅ New feature |

### Breaking Changes

❌ **None in v0.2.0** - Full backward compatibility maintained

⚠️ **Deprecation Warnings**: `aep` commands show migration hints

### Future Breaking Changes (v1.0.0)

- `aep` command will be removed
- Only `aep` command will be supported

## ⚙️ Configuration

### Environment Variables

All configuration can be done via `.env` file or environment variables:

```bash
# Adobe Experience Platform (Required)
AEP_CLIENT_ID=<your_client_id>
AEP_CLIENT_SECRET=<your_client_secret>
AEP_ORG_ID=<your_org_id>@AdobeOrg
AEP_TECHNICAL_ACCOUNT_ID=<your_account_id>@techacct.adobe.com
AEP_SANDBOX_NAME=jason-sandbox  # or "prod"
AEP_TENANT_ID=<your_tenant_id>
AEP_CONTAINER_ID=tenant

# AI Provider Configuration (Optional)
AI_PROVIDER=auto              # auto (default), openai, or anthropic
AI_MODEL=gpt-4o               # Default model for LLM assistant

# AI Provider API Keys (Optional - recommended to use aep ai set-key instead)
ANTHROPIC_API_KEY=<your_key>
OPENAI_API_KEY=<your_key>
```

**Provider Selection Priority:**
1. CLI `--provider` flag (highest)
2. `AI_PROVIDER` environment variable / config
3. Auto-detection (uses first available API key)

**Model Selection Priority:**
1. CLI `--model` flag (highest)
2. `AI_MODEL` environment variable / config
3. Provider-specific default

### AI Key Storage

Keys are stored separately in `~/.adobe/ai-credentials.json` with 600 permissions:

```json
{
  "default_provider": "openai",
  "openai": {
    "api_key": "sk-...",
    "model": "gpt-4o"
  },
  "anthropic": {
    "api_key": "sk-ant-...",
    "model": "claude-3-5-sonnet-20241022"
  },
  "_default": "openai"
}
```

**🔒 Security**: Never commit `.env` or `~/.adobe/` to version control!

## 💡 Examples

### AI-Powered LLM Assistant

Use natural language to query and analyze your AEP environment:

```bash
# Interactive mode with default provider
aep llm chat

# Use specific provider (OpenAI or Anthropic)
aep llm chat --provider openai
aep llm chat --provider anthropic

# One-shot queries
aep llm chat "list all schemas"
aep llm chat "show failing dataflows from last 7 days"
aep llm chat "what datasets are enabled for profile?"
aep llm chat --provider anthropic "analyze dataflow health"

# Use specific model
aep llm chat --model gpt-4o "list schemas"
aep llm chat --model claude-3-5-sonnet-20241022 "show datasets"

# Check provider status
aep ai status

# Test connectivity
aep ai test
aep ai test openai
aep ai test anthropic
```

### End-to-End: Generate and Upload Schema

```bash
# 1. Set up AI provider
aep ai set-key openai
aep ai status  # Verify configuration

# 2. Generate schema from sample data with AI
aep schema create \
  --from-sample customer_events.json \
  --name "Customer Interaction Events" \
  --description "Tracks customer interactions across channels" \
  --use-ai \
  --output schema.json

# 3. Review AI-generated schema
cat schema.json

# 4. Upload to AEP
aep schema create \
  --from-sample customer_events.json \
  --name "Customer Interaction Events" \
  --upload \
  --class-id https://ns.adobe.com/xdm/context/experienceevent
```

### AI-Powered Schema Analysis

When you use `--use-ai`, the CLI provides:
- ✅ Optimal XDM field types and formats
- ✅ Identity namespace recommendations
- ✅ Data quality issue detection
- ✅ Best practice suggestions

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=adobe_experience --cov-report=html

# Run specific test file
pytest tests/test_schema.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Project Status

**Current Implementation:**

- ✅ **Core Module**: Authentication, configuration
- ✅ **AEP Module**: Schema management, API client
- ✅ **AI Module**: OpenAI/Anthropic integration, key management
- ✅ **CLI**: Unified interface with backward compatibility
- 🚧 **Target Module**: Planned for v0.3.0
- 🚧 **Analytics Module**: Planned for v0.4.0

### Adding a New Adobe Product

```python
# 1. Create module: src/adobe_experience/target/
# 2. Implement CLI: src/adobe_experience/target/cli.py

import typer
target_app = typer.Typer(name="target", help="Adobe Target commands")

@target_app.command("info")
def target_info():
    """Show Target information."""
    pass

# 3. Register in src/adobe_experience/cli/main.py
from adobe_experience.target.cli import target_app
app.add_typer(target_app, name="at")

# 4. Use: adobe at infoents" \
  --use-ai

# Generate and upload to AEP
aep schema create \
  --from-sample data.json \
  --name "Customer Profile" \
  --upload \
  --class-id https://ns.adobe.com/xdm/context/profile
```

### 4. Manage Schemas

```bash
# List schemas
aep schema list

# Get schema details
aep schema get <schema-id>

# Save schema to file
aep schema get <schema-id> --output schema.json
```bash
aep auth test
```

### Generate Schema from Sample Data

```bash
aep schema create --from-sample data.json --name "Customer Events"
```

### Ingest Data

```bash
aep ingest csv --file customers.csv --dataset my-dataset --auto-schema
```

## Development

**Priority 1: Schema Management** - Start here for implementation

```bash
# Run tests
pytest

# Format code
black src/ tests/

# Type checking
mypy src/
```

## Architecture

```
src/adobe_aep/
├── agent/          # AI inference engine
├── schema/         # [PRIORITY 1] XDM schema tools
├── aep/            # AEP API client
├── ingestion/      # Data ingestion pipelines
├── processors/     # Data transformation
└── cli/            # Typer CLI commands
```

## 🏗️ Technology Stack

### Core Framework & CLI

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **Python** | 3.10+ | Core language | [python.org](https://www.python.org/) |
| **Typer** | 0.9+ | CLI framework with type hints | [typer.tiangolo.com](https://typer.tiangolo.com/) |
| **Pydantic** | 2.0+ | Data validation and settings management | [docs.pydantic.dev](https://docs.pydantic.dev/) |
| **Rich** | 13.0+ | Terminal UI (tables, progress bars, colors) | [rich.readthedocs.io](https://rich.readthedocs.io/) |

### HTTP & API Integration

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **httpx** | 0.24+ | Async HTTP client for API calls | [www.python-httpx.org](https://www.python-httpx.org/) |
| **Adobe IMS API** | - | OAuth Server-to-Server authentication | [Adobe Auth Guide](https://experienceleague.adobe.com/en/docs/platform-learn/tutorials/platform-api-authentication) |
| **Adobe Platform API** | - | AEP REST API integration | [Adobe API Reference](https://developer.adobe.com/experience-platform-apis/) |

### AI & LLM Integration

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **Anthropic Claude** | - | AI inference for schema analysis | [docs.anthropic.com](https://docs.anthropic.com/) |
| **OpenAI GPT** | - | AI inference alternative | [platform.openai.com](https://platform.openai.com/) |
| **Tool Calling** | - | LLM function calling for structured output | - |

### Data Processing

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **Pandas** | 2.0+ | Data frame processing (optional) | [pandas.pydata.org](https://pandas.pydata.org/) |
| **PyArrow** | 12.0+ | Parquet file handling (optional) | [arrow.apache.org](https://arrow.apache.org/docs/python/) |
| **Faker** | 18.0+ | Test data generation | [faker.readthedocs.io](https://faker.readthedocs.io/) |

### Schema & ERD

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **Mermaid** | - | ERD diagram parsing | [mermaid.js.org](https://mermaid.js.org/) |
| **XDM** | - | Adobe Experience Data Model | [XDM Schema Guide](https://experienceleague.adobe.com/en/docs/experience-platform/xdm/home) |

### Testing

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **pytest** | 7.4+ | Test framework | [docs.pytest.org](https://docs.pytest.org/) |
| **pytest-asyncio** | 0.21+ | Async test support | [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) |
| **pytest-mock** | 3.11+ | Mocking utilities | [pytest-mock](https://pytest-mock.readthedocs.io/) |
| **pytest-cov** | 4.1+ | Code coverage reporting | [pytest-cov](https://pytest-cov.readthedocs.io/) |

### Code Quality

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **Black** | 23.0+ | Code formatter | [black.readthedocs.io](https://black.readthedocs.io/) |
| **Ruff** | 0.0.285+ | Fast Python linter | [docs.astral.sh/ruff](https://docs.astral.sh/ruff/) |
| **mypy** | 1.4+ | Static type checker | [mypy-lang.org](https://mypy-lang.org/) |

### Web UI (Optional)

| Technology | Version | Purpose | Documentation |
|------------|---------|---------|---------------|
| **FastAPI** | 0.100+ | Backend REST API | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| **Next.js** | 14.0+ | React frontend framework | [nextjs.org](https://nextjs.org/) |
| **PostgreSQL** | 15.0+ | Relational database | [postgresql.org](https://www.postgresql.org/) |
| **Redis** | 7.0+ | Caching layer | [redis.io](https://redis.io/) |
| **shadcn/ui** | - | UI component library | [ui.shadcn.com](https://ui.shadcn.com/) |
| **Tailwind CSS** | 3.0+ | CSS framework | [tailwindcss.com](https://tailwindcss.com/) |

### Development Tools

| Technology | Purpose |
|------------|---------|
| **Git** | Version control |
| **Docker** | Container runtime (for web UI) |
| **Docker Compose** | Multi-container orchestration |
| **pip** | Python package manager |
| **venv** | Python virtual environments |

### Key Architecture Decisions

**1. Typer for CLI Framework**
- Type-safe command definitions with Python type hints
- Automatic help generation and validation
- Sub-command architecture for multi-product support
- Rich integration for beautiful terminal output

**2. Pydantic for Data Validation**
- XDM schema modeling with strict type checking
- Configuration management with settings validation
- API response parsing and validation
- Model serialization for API requests

**3. Async HTTP with httpx**
- Non-blocking API calls for better performance
- Connection pooling and retry logic
- Streaming support for large file uploads
- Type-safe request/response handling

**4. Multi-Provider AI (OpenAI + Anthropic)**
- Provider abstraction layer for flexibility
- Tool calling for structured schema generation
- Automatic fallback and provider selection
- Secure credential storage

**5. Modular Architecture**
- Separation of concerns (auth, API clients, CLI)
- Easy extensibility for new Adobe products
- Shared core utilities across modules
- Backward compatibility layer for migrations

## Resources

- [Adobe Experience Platform Docs](https://experienceleague.adobe.com/en/docs/experience-platform)
- [API Reference](https://developer.adobe.com/experience-platform-apis/)
- [Copilot Instructions](.github/copilot-instructions.md)

## License

MIT
