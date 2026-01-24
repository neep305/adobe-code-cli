# Adobe AEP CLI Agent

AI-powered CLI agent for automating Adobe Experience Platform (AEP) integration tasks.

## Features

- 🧠 **AI-Driven**: Uses LLM inference for schema generation, data validation, and ingestion strategies
- 📊 **XDM Schema Management**: Automatically generate XDM-compliant schemas from sample data
- 🚀 **Batch Ingestion**: Smart data ingestion with automatic validation and transformation
- 🔍 **Identity Resolution**: AI-powered identity namespace recommendations
- 🛡️ **Type-Safe**: Built with Pydantic for robust data validation

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure Credentials

**Option A: Interactive Setup (Recommended)**
```bash
adobe-aep init
```

**Option B: Manual Setup**

Create `.env` file:
```bash
AEP_CLIENT_ID=your_client_id
AEP_CLIENT_SECRET=your_client_secret
AEP_ORG_ID=your_org_id@AdobeOrg
AEP_TECHNICAL_ACCOUNT_ID=your_tech_account_id@techacct.adobe.com
AEP_SANDBOX_NAME=prod
ANTHROPIC_API_KEY=your_anthropic_key
```

📖 **Need help?** See [Adobe Developer Console Setup Guide](docs/ADOBE_SETUP.md)

### 2. Test Your Connection

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
