# Adobe Experience Cloud CLI - Installation Guide

## Prerequisites

### 1. Verify pip Installation

Before proceeding, ensure pip is installed on your system:

```bash
pip --version
```

**If pip is not found, install it first:**

<details>
<summary><strong>Windows Installation</strong></summary>

```powershell
# Method 1: Reinstall Python with pip
# Download from https://www.python.org/downloads/
# ✅ Check "Add Python to PATH"
# ✅ Check "Install pip"

# Method 2: If Python is already installed
python -m ensurepip --upgrade

# Method 3: Manual installation
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
rm get-pip.py

# Verify installation
pip --version
```
</details>

<details>
<summary><strong>macOS Installation</strong></summary>

```bash
# Method 1: Using Homebrew (recommended)
brew install python  # Automatically includes pip

# Method 2: Using system Python
python3 -m ensurepip --upgrade

# Method 3: Manual installation
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
rm get-pip.py

# Verify installation
pip3 --version
```
</details>

<details>
<summary><strong>Linux Installation</strong></summary>

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3-pip

# Verify
pip3 --version
```

**CentOS/RHEL/Fedora:**
```bash
# Fedora/RHEL 8+
sudo dnf install python3-pip

# CentOS/RHEL 7
sudo yum install python3-pip

# Verify
pip3 --version
```

**Arch Linux:**
```bash
sudo pacman -S python-pip
```
</details>

---

### 2. Verify Git Installation

Git is required for installing from GitHub:

```bash
git --version
```

**If git is not found:**

- **Windows**: Download from [git-scm.com](https://git-scm.com/download/win)
- **macOS**: `brew install git` or download from [git-scm.com](https://git-scm.com/download/mac)
- **Linux**: `sudo apt install git` (Ubuntu/Debian) or `sudo dnf install git` (Fedora/RHEL)

---

## Quick Start: Install from GitHub

```bash
# Install latest stable release (v0.2.0)
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0

# Or install from main branch (latest development)
pip install git+https://github.com/neep305/adobe-code-cli.git
```

## System Requirements

- **Python**: 3.10, 3.11, or 3.12
- **pip**: 21.0 or higher (installed with Python)
- **Git**: 2.0 or higher (for GitHub installation)
- **Operating System**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+, CentOS 8+, or equivalent)

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
