# Adobe Experience Cloud CLI v0.2.0

First stable release with comprehensive onboarding system and AI-powered features.

## 🎉 New Features

### Interactive Onboarding System
- **3 Tutorial Scenarios**: Choose from basic, data-engineer, or marketer workflows
- **Step-by-Step Guidance**: Clear instructions with commands for each step
- **Progress Tracking**: Visual progress bar and status display
- **Dry-Run Mode**: Practice safely without making actual API calls (`--dry-run`)

### Tutorial Management
- `adobe onboarding start` - Start interactive tutorial
- `adobe onboarding status` - View current progress with detailed task panel
- `adobe onboarding next` - Advance to next step (with `--complete/--no-complete` flag)
- `adobe onboarding skip` - Skip current step
- `adobe onboarding back` - Return to previous step

### AI-Powered Features
- **Q&A Caching System**: Ask tutorial questions with automatic answer caching
  - `adobe onboarding ask` - Get context-aware answers
  - `adobe onboarding cache-stats` - View cache statistics
- **Schema Generation**: AI suggests appropriate fields based on domain and description
- **Bilingual Support**: Full English and Korean localization

### Schema Management
- **Template System**: Pre-built templates for common use cases
  - `adobe aep schema template list` - View available templates
  - `adobe aep schema template show` - View template details
- **Interactive Creation**: `--interactive` flag for guided schema building

## 🐛 Bug Fixes
- Fixed pyproject.toml metadata structure for proper pip installation from Git
- Corrected emoji encoding issues in README
- Added missing `openai` dependency

## 📦 Installation

```bash
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0
```

## 📚 Documentation
- [README](https://github.com/neep305/adobe-code-cli/blob/main/README.md)
- [Installation Guide](https://github.com/neep305/adobe-code-cli/blob/main/INSTALL.md)

## 🔄 What's Changed
Full commit history: https://github.com/neep305/adobe-code-cli/commits/v0.2.0

## 🙏 Acknowledgments
Built with Python 3.10+, Typer, Rich, Pydantic, and Anthropic/OpenAI APIs.
