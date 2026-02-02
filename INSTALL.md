# Adobe Experience Cloud CLI - Installation Guide

## Quick Start: Install from GitHub

```bash
# Install latest stable release (v0.2.0)
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0

# Or install from main branch (latest development)
pip install git+https://github.com/neep305/adobe-code-cli.git
```

## Requirements

- **Python**: 3.10, 3.11, or 3.12
- **Git**: Must be installed and accessible from command line
- **Operating System**: Windows, macOS, or Linux

## Installation Methods

### Method 1: Direct Installation (Recommended)

No need to clone the repository. Install directly from GitHub:

```bash
# Create a virtual environment (recommended)
python -m venv adobe-cli-env

# Activate the environment
# Windows:
adobe-cli-env\Scripts\activate
# macOS/Linux:
source adobe-cli-env/bin/activate

# Install from GitHub
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0

# Verify installation
adobe version
```

### Method 2: With Optional Dependencies

Install with data processing capabilities (pandas, pyarrow):

```bash
pip install "adobe-experience-cloud-cli[data] @ git+https://github.com/neep305/adobe-code-cli.git@v0.2.0"
```

### Method 3: Development Installation

For contributors or local development:

```bash
# Clone the repository
git clone https://github.com/neep305/adobe-code-cli.git
cd adobe-code-cli

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Post-Installation Setup

### 1. Configure Adobe Experience Platform Credentials

Run the interactive setup wizard:

```bash
adobe init
```

This will guide you through:
- Adobe Developer Console credentials (OAuth Server-to-Server)
- Sandbox and tenant configuration
- AI provider setup (optional)

### 2. Set AI Provider Keys (Optional)

For AI-powered features (schema generation, recommendations):

```bash
# Set OpenAI key
adobe ai set-key openai

# Or set Anthropic key
adobe ai set-key anthropic

# Verify stored keys
adobe ai list-keys
```

### 3. Try the Onboarding Tutorial

Start with dry-run mode to learn without affecting your AEP environment:

```bash
# English tutorial
adobe onboarding start --scenario basic --dry-run

# Korean tutorial (한글)
adobe onboarding start --scenario basic --language ko --dry-run

# Check progress
adobe onboarding status
```

## Verification

Test that all commands work:

```bash
# Show version
adobe version

# Show help
adobe --help

# Test AEP commands
adobe aep schema create --help
adobe aep dataset list --help

# Test onboarding
adobe onboarding status
```

## Upgrading

Update to the latest version:

```bash
pip install --upgrade git+https://github.com/neep305/adobe-code-cli.git
```

Update to a specific version:

```bash
pip install --force-reinstall git+https://github.com/neep305/adobe-code-cli.git@v0.2.0
```

## Troubleshooting

### Import Error: ModuleNotFoundError

Make sure you activated your virtual environment:

```bash
# Windows
adobe-cli-env\Scripts\activate

# macOS/Linux
source adobe-cli-env/bin/activate
```

### Git Authentication Required

If your repository is private, configure Git credentials:

```bash
# Use personal access token
git config --global credential.helper store
```

### Python Version Issue

Check your Python version:

```bash
python --version  # Should be 3.10+
```

If you have multiple Python versions:

```bash
python3.11 -m venv adobe-cli-env
```

## Uninstalling

```bash
pip uninstall adobe-experience-cloud-cli
```

## Support

- **Documentation**: [README.md](README.md)
- **Issues**: https://github.com/neep305/adobe-code-cli/issues
- **Repository**: https://github.com/neep305/adobe-code-cli

## Next Steps

1. Complete setup: `adobe init`
2. Try tutorials: `adobe onboarding start --dry-run`
3. Read docs: [README.md](README.md)
4. Create schemas: `adobe aep schema create --interactive`
