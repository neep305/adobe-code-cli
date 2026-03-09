# Adobe Experience Cloud CLI Installation Guide

Back to docs index: [README.md](README.md)

Use this guide as the single source of truth for installing and verifying the CLI.

## Requirements

- Python 3.10, 3.11, or 3.12
- Git
- macOS, Linux, or Windows

## Release Installation (Stable Version)

Use this flow when you want the stable release for regular usage.

1. Create a virtual environment:

```bash
python -m venv adobe-cli-env
```

2. Activate the virtual environment:

macOS/Linux:

```bash
source adobe-cli-env/bin/activate
```

Windows:

```bash
adobe-cli-env\Scripts\activate
```

3. Install the stable release:

```bash
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0
```

4. Optional: install data processing dependencies:

```bash
pip install "adobe-experience-cloud-cli[data] @ git+https://github.com/neep305/adobe-code-cli.git@v0.2.0"
```

## Local Development Installation

Use this flow when you are modifying code in this repository.

1. Clone and move into the repository:

```bash
git clone https://github.com/neep305/adobe-code-cli.git
cd adobe-code-cli
```

2. Create a virtual environment:

```bash
python -m venv adobe-cli-env
```

3. Activate the virtual environment:

macOS/Linux:

```bash
source adobe-cli-env/bin/activate
```

Windows:

```bash
adobe-cli-env\Scripts\activate
```

4. Install in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

What this command means:

- `-e`: editable mode. Local code changes are reflected immediately without reinstalling.
- `.[dev]`: installs the package from the current directory plus development tools such as tests, linting, and type-checking dependencies.

Optional: include data extras during development:

```bash
pip install -e ".[dev,data]"
```

## Post-Installation Setup

1. Configure Adobe credentials:

```bash
aep init
```

2. Optional AI key setup:

```bash
aep ai set-key openai
aep ai set-key anthropic
aep ai list-keys
```

If you need Adobe Developer Console credentials first, see [ADOBE_SETUP.md](ADOBE_SETUP.md).

## Verification

```bash
aep version
aep --help
aep auth test
aep schema create --help
aep dataset list --help
```

## Upgrade

```bash
pip install --upgrade git+https://github.com/neep305/adobe-code-cli.git
```

For local development installs, pull latest changes and reinstall editable dependencies:

```bash
git pull
pip install -e ".[dev]"
```

## Troubleshooting

### Command not found: aep

Your environment is not active or the package is not installed in that environment.

```bash
source adobe-cli-env/bin/activate  # macOS/Linux
adobe-cli-env\Scripts\activate    # Windows
pip show adobe-experience-cloud-cli
```

### ModuleNotFoundError

Re-activate your virtual environment and reinstall:

```bash
source adobe-cli-env/bin/activate  # macOS/Linux
pip install --force-reinstall git+https://github.com/neep305/adobe-code-cli.git@v0.2.0
```

### Wrong Python version

```bash
python --version
```

If needed, use a specific interpreter:

```bash
python3.11 -m venv adobe-cli-env
```

## Uninstall

```bash
pip uninstall adobe-experience-cloud-cli
```
