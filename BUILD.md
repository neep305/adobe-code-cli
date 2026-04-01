# Adobe AEP Web UI - Build Instructions

## For Contributors/Developers

This document explains how to build the Web UI for distribution with standalone mode.

## Prerequisites

### Development
- Python 3.10+
- Node.js 18+ and npm
- Git

### Building for Distribution
- All development prerequisites
- Build tools (setuptools, wheel, hatch)

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/neep305/adobe-code-cli.git
cd adobe-code-cli
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev,web]"
```

### 3. Install Frontend Dependencies

```bash
cd web/frontend
npm install
cd ../..
```

### 4. Configure Environment

```bash
# Copy example .env
cp .env.example .env

# Edit .env with your credentials
# At minimum: AEP credentials and ANTHROPIC_API_KEY
```

## Development Workflow

### Run Backend Only

```bash
cd web/backend/app
uvicorn main:app --reload --port 8000
```

### Run Frontend Only (Dev Mode)

```bash
cd web/frontend
npm run dev
```

### Run Full Stack (Dev Mode)

```bash
aep web start --mode dev
```

### Run Standalone Mode (Testing)

```bash
# First build frontend
cd web/frontend
npm run export
cd ../..

# Then start standalone
aep web start --mode standalone
```

## Building for Release

### Step 1: Build Frontend Static Files

The frontend must be built before packaging the Python package.

```bash
cd web/frontend

# Install dependencies if not already
npm install

# Build static export
npm run export
```

This creates `web/frontend/out/` with all static files.

**Important:** The `out/` directory must exist before running `python -m build`.

### Step 2: Build Python Package

```bash
# From project root
cd ..

# Build wheel and sdist
python -m build

# This creates:
# - dist/adobe_experience_cloud_cli-X.Y.Z-py3-none-any.whl
# - dist/adobe-experience-cloud-cli-X.Y.Z.tar.gz
```

The wheel includes:
- Python source code
- Web backend
- **Frontend static files** (from `web/frontend/out/`)

### Step 3: Test Installation

```bash
# Create test environment
python -m venv test-env
source test-env/bin/activate

# Install from wheel
pip install dist/adobe_experience_cloud_cli-X.Y.Z-py3-none-any.whl[web]

# Test standalone mode
aep web start --no-browser --detach
curl http://localhost:8000/api/health
aep web stop
```

### Step 4: Publish (Maintainers Only)

```bash
# Test PyPI
python -m twine upload --repository testpypi dist/*

# Production PyPI
python -m twine upload dist/*
```

## CI/CD Automation

### GitHub Actions Workflow

Create `.github/workflows/build.yml`:

```yaml
name: Build and Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Python dependencies
        run: |
          pip install build twine
      
      - name: Build frontend
        run: |
          cd web/frontend
          npm install
          npm run export
          cd ../..
      
      - name: Build Python package
        run: |
          python -m build
      
      - name: Check package
        run: |
          twine check dist/*
      
      - name: Test installation
        run: |
          pip install dist/*.whl[web]
          aep --version
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
```

## Troubleshooting

### Frontend Build Fails

```bash
# Clear cache and rebuild
cd web/frontend
rm -rf .next out node_modules
npm install
npm run export
```

### Missing Frontend in Package

Check `MANIFEST.in` includes:

```
recursive-include web/frontend/out *
graft web/frontend/out
```

Verify frontend was built:

```bash
ls -la web/frontend/out/
```

### Import Errors

Make sure you're in project root when building:

```bash
# Should see:
# - src/
# - web/
# - pyproject.toml
# - MANIFEST.in
pwd
```

## File Structure After Build

```
dist/
├── adobe_experience_cloud_cli-X.Y.Z-py3-none-any.whl
│   ├── adobe_experience/          # Python code
│   │   ├── cli/
│   │   ├── aep/
│   │   ├── agent/
│   │   └── ...
│   └── web/
│       ├── backend/
│       │   └── app/
│       └── frontend/
│           └── out/               # Static build ✓
│               ├── _next/
│               ├── index.html
│               └── ...
└── adobe_experience_cloud_cli-X.Y.Z.tar.gz
```

## Testing Checklist

Before releasing:

- [ ] Frontend builds without errors
- [ ] Package installs cleanly
- [ ] `aep --help` works
- [ ] `aep web start` works in standalone mode
- [ ] Web UI loads at http://localhost:8000
- [ ] API endpoints respond (http://localhost:8000/api/health)
- [ ] Static files serve correctly
- [ ] All CLI commands work
- [ ] Tests pass (`pytest`)

## Build Scripts

### PowerShell (build.ps1)

```powershell
# Build script for Windows
Write-Host "Building Adobe AEP CLI..." -ForegroundColor Cyan

# Build frontend
Write-Host "`n[1/3] Building frontend..." -ForegroundColor Yellow
Set-Location web\frontend
npm install
npm run export
Set-Location ..\..

# Clean old builds
Write-Host "`n[2/3] Cleaning old builds..." -ForegroundColor Yellow
Remove-Item -Path dist -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path build -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path *.egg-info -Recurse -Force -ErrorAction SilentlyContinue

# Build package
Write-Host "`n[3/3] Building Python package..." -ForegroundColor Yellow
python -m build

Write-Host "`n✓ Build complete!" -ForegroundColor Green
Write-Host "`nArtifacts in dist/" -ForegroundColor Cyan
Get-ChildItem dist\
```

### Bash (build.sh)

```bash
#!/bin/bash
set -e

echo "Building Adobe AEP CLI..."

# Build frontend
echo ""
echo "[1/3] Building frontend..."
cd web/frontend
npm install
npm run export
cd ../..

# Clean old builds
echo ""
echo "[2/3] Cleaning old builds..."
rm -rf dist/ build/ *.egg-info

# Build package
echo ""
echo "[3/3] Building Python package..."
python -m build

echo ""
echo "✓ Build complete!"
echo ""
echo "Artifacts in dist/"
ls -lh dist/
```

## Release Checklist

1. **Update Version**
   - [ ] Update `pyproject.toml` version
   - [ ] Update `web/frontend/package.json` version
   - [ ] Update `CHANGELOG.md`

2. **Build**
   - [ ] Build frontend: `npm run export`
   - [ ] Build package: `python -m build`
   - [ ] Check package: `twine check dist/*`

3. **Test**
   - [ ] Install in clean environment
   - [ ] Run tests: `pytest`
   - [ ] Test standalone mode
   - [ ] Test Docker mode
   - [ ] Test CLI commands

4. **Documentation**
   - [ ] Update README.md
   - [ ] Update CLAUDE.md
   - [ ] Update `docs/` and `web/` guides if behavior changed

5. **Publish**
   - [ ] Create Git tag: `git tag v0.2.0`
   - [ ] Push tag: `git push origin v0.2.0`
   - [ ] Upload to PyPI: `twine upload dist/*`
   - [ ] Create GitHub release

## Questions?

- Documentation: [README.md](README.md)
- Issues: https://github.com/neep305/adobe-code-cli/issues
- Discussions: https://github.com/neep305/adobe-code-cli/discussions
