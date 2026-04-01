#!/bin/bash
# Build script for Adobe AEP CLI - Standalone Mode
# This script builds the frontend and packages everything for distribution

set -e  # Exit on error

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Header
echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Adobe Experience Platform CLI - Build Script        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js: $NODE_VERSION${NC}"
else
    echo -e "${RED}✗ Node.js not found. Please install Node.js 18+ from https://nodejs.org/${NC}"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓ npm: v$NPM_VERSION${NC}"
else
    echo -e "${RED}✗ npm not found.${NC}"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python not found. Please install Python 3.10+ from https://www.python.org/${NC}"
    exit 1
fi

echo ""

# Step 1: Build Frontend
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Step 1/4: Building Frontend (Static Export)${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

FRONTEND_DIR="web/frontend"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}✗ Frontend directory not found: $FRONTEND_DIR${NC}"
    exit 1
fi

cd "$FRONTEND_DIR"

# Install dependencies
echo -e "${YELLOW}Installing npm dependencies...${NC}"
npm install
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Build static export
echo ""
echo -e "${YELLOW}Building static export...${NC}"
npm run build
echo -e "${GREEN}✓ Frontend built successfully${NC}"

# Verify output
if [ -d "out" ]; then
    FILE_COUNT=$(find out -type f | wc -l)
    echo -e "${GREEN}✓ Output directory created: $FILE_COUNT files${NC}"
else
    echo -e "${RED}✗ Output directory 'out' not found after build${NC}"
    exit 1
fi

cd ../..

echo ""

# Step 2: Clean Old Builds
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Step 2/4: Cleaning Old Builds${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

for dir in dist build; do
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}Removing $dir...${NC}"
        rm -rf "$dir"
        echo -e "${GREEN}✓ Removed $dir${NC}"
    fi
done

# Remove *.egg-info directories
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Cleaned *.egg-info directories${NC}"

echo ""

# Step 3: Build Python Package
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Step 3/4: Building Python Package${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Running python -m build...${NC}"

# Use python3 if available, otherwise python
if command -v python3 &> /dev/null; then
    python3 -m build
else
    python -m build
fi

echo -e "${GREEN}✓ Package built successfully${NC}"

echo ""

# Step 4: Verify Build
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Step 4/4: Verifying Build${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
echo ""

if [ -d "dist" ]; then
    echo -e "${GREEN}Build artifacts:${NC}"
    echo ""
    
    for file in dist/*; do
        if [ -f "$file" ]; then
            SIZE=$(du -h "$file" | cut -f1)
            BASENAME=$(basename "$file")
            echo -e "  ${CYAN}📦 $BASENAME ($SIZE)${NC}"
        fi
    done
    
    echo ""
    echo -e "${GREEN}✓ Build verification complete${NC}"
else
    echo -e "${RED}✗ dist directory not found${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           BUILD SUCCESSFUL!                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  ${NC}1. Test installation:${NC}"
echo -e "     ${CYAN}pip install dist/*.whl[web]${NC}"
echo ""
echo -e "  ${NC}2. Test standalone mode:${NC}"
echo -e "     ${CYAN}aep web start${NC}"
echo ""
echo -e "  ${NC}3. Publish to PyPI:${NC}"
echo -e "     ${CYAN}python -m twine upload dist/*${NC}"
echo ""
