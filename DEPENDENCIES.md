# Dependencies & Frameworks

Complete list of frameworks, libraries, and tools used in the Adobe Experience Cloud CLI project.

---

## 📦 Core Dependencies

### HTTP & API Communication
- **[httpx](https://www.python-httpx.org/)** `>=0.27.0`
  - Modern async HTTP client for Python
  - Used for Adobe API communication
  - Supports HTTP/2, connection pooling, timeout handling
  - **Why**: Superior to requests for async operations and modern API features

### Data Validation & Settings
- **[Pydantic](https://docs.pydantic.dev/)** `>=2.0.0`
  - Data validation using Python type annotations
  - Used for XDM schema validation, API response models
  - Ensures type safety across the codebase
  - **Why**: Industry-standard for data validation, excellent TypeScript-like experience

- **[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** `>=2.0.0`
  - Settings management from environment variables
  - Used for Adobe credentials, API configuration
  - **Why**: Seamless integration with Pydantic, environment-aware configuration

### CLI Framework
- **[Typer](https://typer.tiangolo.com/)** `>=0.12.0`
  - Modern CLI framework built on Click
  - Used for all CLI commands and subcommands
  - Type-hint based command definition
  - **Why**: Intuitive API, excellent documentation, automatic help generation

- **[Rich](https://rich.readthedocs.io/)** `>=13.0.0`
  - Terminal output formatting and styling
  - Used for colored output, tables, progress bars, panels
  - **Why**: Beautiful terminal UIs, extensive formatting options

### AI Provider SDKs
- **[Anthropic](https://docs.anthropic.com/en/api/client-sdks)** `>=0.21.0`
  - Official Anthropic Claude API client
  - Used for Claude-powered schema generation, AI assistance
  - **Why**: Official SDK, reliable, well-maintained

- **[OpenAI](https://platform.openai.com/docs/api-reference)** `>=1.0.0`
  - Official OpenAI API client
  - Used for GPT-powered features (alternative to Claude)
  - **Why**: Official SDK, supports latest GPT models

### Configuration Management
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** `>=1.0.0`
  - Load environment variables from .env files
  - Used for development and local credential management
  - **Why**: Standard practice for environment variable management

---

## 🛠️ Development Dependencies

### Testing Framework
- **[pytest](https://docs.pytest.org/)** `>=8.0.0`
  - Modern Python testing framework
  - Used for unit tests, integration tests
  - **Why**: Industry standard, extensive plugin ecosystem

- **[pytest-asyncio](https://pytest-asyncio.readthedocs.io/)** `>=0.23.0`
  - Pytest plugin for asyncio support
  - Used for testing async API calls
  - **Why**: Essential for async testing

- **[pytest-cov](https://pytest-cov.readthedocs.io/)** `>=4.1.0`
  - Coverage plugin for pytest
  - Used for test coverage reporting
  - **Why**: Track code coverage, identify untested code

### Code Quality Tools
- **[Black](https://black.readthedocs.io/)** `>=24.0.0`
  - Opinionated code formatter
  - Used for consistent code style (100 char line length)
  - **Why**: Zero-configuration, deterministic formatting

- **[Ruff](https://docs.astral.sh/ruff/)** `>=0.3.0`
  - Extremely fast Python linter (Rust-based)
  - Used for linting, import sorting, code quality checks
  - **Why**: 10-100x faster than Flake8, replaces multiple tools

- **[mypy](http://mypy-lang.org/)** `>=1.8.0`
  - Static type checker
  - Used for type safety validation
  - **Why**: Catch type errors before runtime

---

## 📊 Optional Data Processing Dependencies

### Data Analysis & Transformation
- **[pandas](https://pandas.pydata.org/)** `>=2.0.0` *(optional)*
  - Data manipulation and analysis library
  - Used for CSV processing, data transformation
  - **Why**: Industry standard for data processing in Python

- **[pyarrow](https://arrow.apache.org/docs/python/)** `>=15.0.0` *(optional)*
  - Python bindings for Apache Arrow
  - Used for Parquet file reading/writing
  - **Why**: Efficient columnar data format for AEP ingestion

---

## 🏗️ Build System & Packaging

### Build Backend
- **[Hatchling](https://hatch.pypa.io/latest/)**
  - Modern Python build backend (PEP 517)
  - Used for building wheels and source distributions
  - **Why**: Fast, standard-compliant, supports modern Python packaging

### Package Management
- **[pip](https://pip.pypa.io/)** `>=21.0`
  - Python package installer
  - Used for dependency installation
  - **Why**: Standard Python package manager

---

## 🌐 Runtime Environment

### Python Version
- **Python** `>=3.10, <4.0`
  - Supported versions: 3.10, 3.11, 3.12
  - **Why**: Modern Python features (match/case, improved type hints, performance)

### Operating Systems
- **Windows** 10/11
- **macOS** 10.15+ (Catalina and later)
- **Linux** Ubuntu 20.04+, CentOS 8+, Fedora, Arch

---

## 📚 Framework Choices & Rationale

### Why These Technologies?

**1. Modern Python (3.10+)**
- Pattern matching (match/case statements)
- Improved type hints (union types with `|`)
- Better error messages
- Performance improvements

**2. Async-First Architecture (httpx)**
- Non-blocking API calls to Adobe services
- Better performance for batch operations
- Concurrent request handling

**3. Type Safety (Pydantic + mypy)**
- Catch errors at development time
- Self-documenting code
- Automatic validation of Adobe API responses

**4. AI-Powered Features (Anthropic/OpenAI)**
- Intelligent schema generation from sample data
- Natural language Q&A during onboarding
- Context-aware error suggestions

**5. Developer Experience (Typer + Rich)**
- Intuitive CLI design
- Beautiful terminal output
- Auto-generated documentation
- Type-safe command definitions

**6. Fast Development Cycle (Ruff + Black)**
- Instant linting (Ruff is 10-100x faster)
- Consistent code style (Black)
- Quick feedback loop

---

## 🔧 Installation Commands

### Base Installation
```bash
pip install git+https://github.com/neep305/adobe-code-cli.git@v0.2.0
```

### With Data Processing
```bash
pip install "adobe-experience-cloud-cli[data] @ git+https://github.com/neep305/adobe-code-cli.git@v0.2.0"
```

### Development Setup
```bash
git clone https://github.com/neep305/adobe-code-cli.git
cd adobe-code-cli
pip install -e ".[dev]"
```

---

## 📊 Dependency Tree

```
adobe-experience-cloud-cli
├── Core Runtime
│   ├── httpx (API communication)
│   ├── pydantic (data validation)
│   ├── pydantic-settings (configuration)
│   └── python-dotenv (environment variables)
│
├── CLI Framework
│   ├── typer (command routing)
│   └── rich (terminal UI)
│
├── AI Providers
│   ├── anthropic (Claude API)
│   └── openai (GPT API)
│
├── Data Processing (optional)
│   ├── pandas (CSV/data manipulation)
│   └── pyarrow (Parquet format)
│
└── Development Tools
    ├── pytest + plugins (testing)
    ├── black (formatting)
    ├── ruff (linting)
    └── mypy (type checking)
```

---

## 🔄 Version Compatibility Matrix

| Package | Min Version | Tested Version | Python 3.10 | Python 3.11 | Python 3.12 |
|---------|-------------|----------------|-------------|-------------|-------------|
| httpx | 0.27.0 | 0.27.0 | ✅ | ✅ | ✅ |
| pydantic | 2.0.0 | 2.9.2 | ✅ | ✅ | ✅ |
| typer | 0.12.0 | 0.12.5 | ✅ | ✅ | ✅ |
| rich | 13.0.0 | 13.9.4 | ✅ | ✅ | ✅ |
| anthropic | 0.21.0 | 0.40.0 | ✅ | ✅ | ✅ |
| openai | 1.0.0 | 1.57.4 | ✅ | ✅ | ✅ |
| pandas* | 2.0.0 | 2.2.3 | ✅ | ✅ | ✅ |
| pyarrow* | 15.0.0 | 18.1.0 | ✅ | ✅ | ✅ |

*Optional dependencies (install with `[data]` extra)

---

## 🚀 Future Dependencies (Planned)

### Adobe Target Integration
- Additional API clients for Target-specific operations
- Campaign management libraries

### Adobe Analytics Integration
- Analytics API wrappers
- Report generation utilities

### Enhanced Data Processing
- **dask** - Parallel computing for large datasets
- **polars** - Faster DataFrame alternative to pandas

### Monitoring & Observability
- **structlog** - Structured logging
- **prometheus-client** - Metrics collection

---

## 📖 Related Documentation

- [README.md](README.md) - Project overview and quick start
- [INSTALL.md](INSTALL.md) - Detailed installation guide
- [CLI_COMMANDS.md](CLI_COMMANDS.md) - Complete command reference
- [pyproject.toml](pyproject.toml) - Package configuration

---

**Last Updated**: February 3, 2026  
**Project Version**: 0.2.0  
**Python Support**: 3.10, 3.11, 3.12
