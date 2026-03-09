# Adobe Experience Cloud CLI

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/neep305/adobe-code-cli)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

Unified AI-powered CLI for Adobe Experience Cloud workflows, currently focused on Adobe Experience Platform (AEP).

Current version: 0.2.0

## Features

- Unified CLI for schema, dataset, ingestion, dataflow, and destination workflows
- AI-assisted schema generation and guidance (OpenAI or Anthropic)
- Interactive onboarding tutorials
- Web UI lifecycle commands for local full-stack workflows
- Type-safe implementation with Pydantic and rich terminal output

## Quick Install

Detailed installation, virtual environment setup, verification, and troubleshooting are in [docs/install.md](docs/install.md).

```bash
# 1) Create and activate virtual environment
python -m venv adobe-cli-env
source adobe-cli-env/bin/activate  # macOS/Linux

# 2) Install stable release
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0
```

Windows activation:

```bash
adobe-cli-env\Scripts\activate
```

## Quick Start

```bash
# Configure Adobe credentials interactively
aep init

# Validate authentication
aep auth test

# View available commands
aep --help
```

If you are new to Adobe Developer Console setup, follow [docs/ADOBE_SETUP.md](docs/ADOBE_SETUP.md) first.

## Command Highlights

```bash
# Schema
aep schema create --help
aep schema list

# Dataset
aep dataset list
aep dataset create --help

# AI provider keys
aep ai set-key openai
aep ai status

# Interactive assistant
aep llm chat

# Web UI management
aep web start --mode docker
aep web status
```

## Documentation

- Documentation index: [docs/README.md](docs/README.md)
- Installation and troubleshooting: [docs/install.md](docs/install.md)
- Adobe credential setup: [docs/ADOBE_SETUP.md](docs/ADOBE_SETUP.md)
- LLM mode and model settings: [docs/LLM_MODE.md](docs/LLM_MODE.md)
- Web UI guide: [web/README.md](web/README.md)

## Development Installation

```bash
git clone https://github.com/neep305/adobe-code-cli.git
cd adobe-code-cli

python -m venv adobe-cli-env
source adobe-cli-env/bin/activate  # macOS/Linux

pip install -e ".[dev]"
pytest
```

## License

MIT License. See [LICENSE](LICENSE).

This project is an unofficial tool and is not affiliated with or endorsed by Adobe Inc.