# Adobe Experience Cloud CLI

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/neep305/adobe-code-cli)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

Unified AI-powered CLI for Adobe Experience Cloud products - AEP, Target, Analytics, and more.

> **Current Version**: 0.2.0  
> **Status**: Alpha - Adobe Experience Platform support available, more products coming soon  
> **Migration**: `adobe-aep` commands are deprecated, use `adobe aep` instead

## ✨ Features

- 🔧 **Unified Interface**: Single CLI for all Adobe Experience Cloud products
- 🧠 **AI-Driven**: Uses LLM inference (OpenAI/Anthropic) for schema generation and validation
- 📊 **XDM Schema Management**: Automatically generate XDM-compliant schemas from sample data
- � **Dataset Management**: Create, list, and manage AEP datasets with full lifecycle control
- 🔄 **Batch Ingestion**: Create batches, monitor status, and manage data ingestion workflows
- �🔑 **Secure Key Management**: Separate AI API key storage with `adobe ai` commands
- 🔄 **Backward Compatible**: Legacy `adobe-aep` commands still supported (with deprecation warnings)
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
adobe init
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

# AI Provider (choose one or both)
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
```

**Option C: Separate AI Key Storage (Recommended)**

Store AI keys separately from `.env` for better security:

```bash
# Set AI provider keys
adobe ai set-key openai
# Enter key when prompted (paste with Ctrl+V works!)

adobe ai set-key anthropic

# List stored keys
adobe ai list-keys

# S📖 Command Reference

### Global Commands

```bash
adobe --help              # Show all available commands
adobe version             # Show version information
adobe init                # Interactive setup wizard
```

### Adobe Experience Platform (AEP)

```bash
adobe aep --help          # AEP-specific commands
adobe aep info            # Show AEP information

# Schema Management
adobe aep schema create   # Create XDM schema from sample data
adobe aep schema list     # List schemas from AEP
adobe aep schema get      # Get schema details

# Dataset Management
adobe aep dataset list    # List datasets
adobe aep dataset create  # Create new dataset
adobe aep dataset get     # Get dataset details
adobe aep dataset enable-profile  # Enable for Profile

# Batch Management
adobe aep dataset create-batch    # Create batch for ingestion
adobe aep dataset batch-status    # Check batch status
adobe aep dataset list-batches    # List batches
adobe aep dataset complete-batch  # Complete batch
```

### AI Provider Management

```bash
adobe ai set-key <provider>      # Set API key (openai/anthropic)
adobe ai list-keys                # List stored API keys
adobe ai remove-key <provider>    # Remove API key
adobe ai set-default <provider>   # Set default provider
```

### Authentication

```bash
adobe auth test           # Test AEP credentials
```

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
│   ├── legacy.py   # Backward compatibility (adobe-aep)
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

If you're upgrading from `adobe-aep` (v0.1.x):

### Command Changes

| Old (v0.1.x) | New (v0.2.0+) | Status |
|--------------|---------------|--------|
| `adobe-aep schema create` | `adobe aep schema create` | ✅ Both work |
| `adobe-aep auth test` | `adobe auth test` | ✅ Both work |
| - | `adobe ai set-key` | ✅ New feature |

### Breaking Changes

❌ **None in v0.2.0** - Full backward compatibility maintained

⚠️ **Deprecation Warnings**: `adobe-aep` commands show migration hints

### Future Breaking Changes (v1.0.0)

- `adobe-aep` command will be removed
- Only `adobe` command will be supported

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

# AI Provider (Optional - recommended to use adobe ai set-key instead)
ANTHROPIC_API_KEY=<your_key>
OPENAI_API_KEY=<your_key>
```

### AI Key Storage

Keys are stored separately in `~/.adobe/ai-credentials.json` with 600 permissions:

```json
{
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

### End-to-End: Generate and Upload Schema

```bash
# 1. Set up AI provider
adobe ai set-key openai

# 2. Generate schema from sample data with AI
adobe aep schema create \
  --from-sample customer_events.json \
  --name "Customer Interaction Events" \
  --description "Tracks customer interactions across channels" \
  --use-ai \
  --output schema.json

# 3. Review AI-generated schema
cat schema.json

# 4. Upload to AEP
adobe aep schema create \
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
adobe aep schema create \
  --from-sample data.json \
  --name "Customer Profile" \
  --upload \
  --class-id https://ns.adobe.com/xdm/context/profile
```

### 4. Manage Schemas

```bash
# List schemas
adobe aep schema list

# Get schema details
adobe aep schema get <schema-id>

# Save schema to file
adobe aep schema get <schema-id> --output schema.json
```bash
adobe-aep auth test
```

### Generate Schema from Sample Data

```bash
adobe-aep schema create --from-sample data.json --name "Customer Events"
```

### Ingest Data

```bash
adobe-aep ingest csv --file customers.csv --dataset my-dataset --auto-schema
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

## Resources

- [Adobe Experience Platform Docs](https://experienceleague.adobe.com/en/docs/experience-platform)
- [API Reference](https://developer.adobe.com/experience-platform-apis/)
- [Copilot Instructions](.github/copilot-instructions.md)

## License

MIT
