# Build script for Adobe AEP CLI - Standalone Mode
# This script builds the frontend and packages everything for distribution

Write-Host "`n╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Adobe Experience Platform CLI - Build Script        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found. Please install Node.js 18+ from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# Check npm
try {
    $npmVersion = npm --version
    Write-Host "✓ npm: v$npmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ npm not found." -ForegroundColor Red
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.10+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 1: Build Frontend
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Step 1/4: Building Frontend (Static Export)" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$frontendDir = "web\frontend"

if (-Not (Test-Path $frontendDir)) {
    Write-Host "✗ Frontend directory not found: $frontendDir" -ForegroundColor Red
    exit 1
}

Push-Location $frontendDir

try {
    # Install dependencies
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed"
    }
    Write-Host "✓ Dependencies installed" -ForegroundColor Green
    
    # Build static export
    Write-Host "`nBuilding static export..." -ForegroundColor Yellow
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "npm build failed"
    }
    Write-Host "✓ Frontend built successfully" -ForegroundColor Green
    
    # Verify output
    if (Test-Path "out") {
        $fileCount = (Get-ChildItem -Path "out" -Recurse -File).Count
        Write-Host "✓ Output directory created: $fileCount files" -ForegroundColor Green
    } else {
        throw "Output directory 'out' not found after build"
    }
    
} catch {
    Write-Host "✗ Frontend build failed: $_" -ForegroundColor Red
    Pop-Location
    exit 1
} finally {
    Pop-Location
}

Write-Host ""

# Step 2: Clean Old Builds
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Step 2/4: Cleaning Old Builds" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$dirsToClean = @("dist", "build")
$patterns = @("*.egg-info")

foreach ($dir in $dirsToClean) {
    if (Test-Path $dir) {
        Write-Host "Removing $dir..." -ForegroundColor Yellow
        Remove-Item -Path $dir -Recurse -Force
        Write-Host "✓ Removed $dir" -ForegroundColor Green
    }
}

foreach ($pattern in $patterns) {
    $items = Get-ChildItem -Path . -Filter $pattern -Recurse -Directory
    foreach ($item in $items) {
        Write-Host "Removing $($item.FullName)..." -ForegroundColor Yellow
        Remove-Item -Path $item.FullName -Recurse -Force
        Write-Host "✓ Removed $($item.Name)" -ForegroundColor Green
    }
}

Write-Host ""

# Step 3: Build Python Package
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Step 3/4: Building Python Package" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

try {
    Write-Host "Running python -m build..." -ForegroundColor Yellow
    python -m build
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed"
    }
    Write-Host "✓ Package built successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Python package build failed: $_" -ForegroundColor Red
    Write-Host "`nTip: Install build tools with: pip install build" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 4: Verify Build
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Step 4/4: Verifying Build" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "dist") {
    $wheels = Get-ChildItem -Path "dist" -Filter "*.whl"
    $tarballs = Get-ChildItem -Path "dist" -Filter "*.tar.gz"
    
    Write-Host "Build artifacts:" -ForegroundColor Green
    Write-Host ""
    
    foreach ($wheel in $wheels) {
        $sizeKB = [math]::Round($wheel.Length / 1KB, 2)
        Write-Host "  📦 $($wheel.Name) ($sizeKB KB)" -ForegroundColor Cyan
    }
    
    foreach ($tarball in $tarballs) {
        $sizeKB = [math]::Round($tarball.Length / 1KB, 2)
        Write-Host "  📦 $($tarball.Name) ($sizeKB KB)" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "✓ Build verification complete" -ForegroundColor Green
} else {
    Write-Host "✗ dist directory not found" -ForegroundColor Red
    exit 1
}

# Summary
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           BUILD SUCCESSFUL!                           ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test installation:" -ForegroundColor White
Write-Host "     pip install dist\*.whl[web]" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Test standalone mode:" -ForegroundColor White
Write-Host "     aep web start" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Publish to PyPI:" -ForegroundColor White
Write-Host "     python -m twine upload dist/*" -ForegroundColor Cyan
Write-Host ""
