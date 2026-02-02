# Setup Test Environment for AEP Integration Tests

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Adobe AEP CLI - Test Setup" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Step 1: Check credentials
Write-Host "[1/4] Checking Credentials..." -ForegroundColor Yellow

$credFile = "$env:USERPROFILE\.adobe\credentials.json"
$hasCredFile = Test-Path $credFile

if ($hasCredFile) {
    Write-Host "  OK: Credentials file found" -ForegroundColor Green
    try {
        $creds = Get-Content $credFile | ConvertFrom-Json
        Write-Host "  Client ID: $($creds.client_id.Substring(0,10))..." -ForegroundColor Gray
        Write-Host "  Sandbox: $($creds.sandbox_name)" -ForegroundColor Gray
    } catch {
        Write-Host "  Warning: Could not parse credentials" -ForegroundColor Yellow
    }
} elseif ($env:CLIENT_ID) {
    Write-Host "  OK: Environment variables found" -ForegroundColor Green
} else {
    Write-Host "  ERROR: No credentials found" -ForegroundColor Red
    Write-Host "`n  Please configure credentials:" -ForegroundColor Yellow
    Write-Host "  1. Create: $credFile" -ForegroundColor White
    Write-Host "  2. Or set: CLIENT_ID, CLIENT_SECRET, ORG_ID" -ForegroundColor White
    exit 1
}

# Step 2: Test connection
Write-Host "`n[2/4] Testing Connection..." -ForegroundColor Yellow

$testOutput = adobe aep schema list --limit 1 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Connected to AEP" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Connection failed" -ForegroundColor Red
    Write-Host "  $testOutput" -ForegroundColor Red
    exit 1
}

# Step 3: Check dataset
Write-Host "`n[3/4] Checking Test Dataset..." -ForegroundColor Yellow

if ($env:TEST_DATASET_ID) {
    Write-Host "  OK: Dataset ID configured: $env:TEST_DATASET_ID" -ForegroundColor Green
} else {
    Write-Host "  Warning: No TEST_DATASET_ID set" -ForegroundColor Yellow
    Write-Host "  Ingestion tests will be skipped" -ForegroundColor Gray
}

# Step 4: Check dependencies
Write-Host "`n[4/4] Checking Dependencies..." -ForegroundColor Yellow

$packages = @("pandas", "pyarrow", "pydantic", "httpx")
$allOk = $true

foreach ($pkg in $packages) {
    $check = python -c "import $pkg" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $pkg" -ForegroundColor Green
    } else {
        Write-Host "  Missing: $pkg" -ForegroundColor Red
        $allOk = $false
    }
}

if (-not $allOk) {
    Write-Host "`nInstalling missing packages..." -ForegroundColor Yellow
    pip install pandas pyarrow pydantic httpx typer rich
}

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan

Write-Host "`nRun integration tests:" -ForegroundColor White
Write-Host "  .\scripts\run_integration_tests.ps1" -ForegroundColor Cyan
Write-Host ""
