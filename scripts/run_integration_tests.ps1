# Adobe AEP CLI - Integration Test Runner
param(
    [string]$DatasetId = $env:TEST_DATASET_ID,
    [switch]$SkipDataIngestion,
    [switch]$SkipCleanup,
    [switch]$Verbose
)

# Test tracking
$script:passed = 0
$script:failed = 0
$script:total = 0

function Test-CLI {
    param([string]$Name, [scriptblock]$Command)
    
    $script:total++
    Write-Host "`n[$script:total] $Name" -ForegroundColor Cyan
    
    try {
        $output = & $Command 2>&1 | Out-String
        
        if ($Verbose) {
            Write-Host $output.Substring(0, [Math]::Min(200, $output.Length)) -ForegroundColor Gray
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  PASS" -ForegroundColor Green
            $script:passed++
            return @{ Success = $true; Output = $output }
        } else {
            Write-Host "  FAIL (Exit: $LASTEXITCODE)" -ForegroundColor Red
            $script:failed++
            return @{ Success = $false; Output = $output }
        }
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        $script:failed++
        return @{ Success = $false; Error = $_ }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Adobe AEP CLI - Integration Tests" -ForegroundColor Cyan
Write-Host "Version: v0.2.0" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Phase 1: Authentication
Write-Host "`n=== Phase 1: Authentication ===" -ForegroundColor Yellow

Test-CLI "OAuth Token Acquisition" { adobe aep schema list --limit 1 }

# Phase 2: Schema Registry
Write-Host "`n=== Phase 2: Schema Registry ===" -ForegroundColor Yellow

Test-CLI "List Schemas" { adobe aep schema list --limit 5 }

# Create sample JSON for schema creation
$sampleJson = "sample_schema.json"
$jsonContent = @'
[{"id": 1, "name": "Test", "email": "test@example.com", "age": 30}]
'@
# Write UTF8 without BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($sampleJson, $jsonContent, $utf8NoBom)

$testSchemaName = "IntegrationTest_$(Get-Date -Format 'yyyyMMddHHmmss')"
$createResult = Test-CLI "Create Test Schema" { 
    adobe aep schema create --name $testSchemaName --from-sample $sampleJson --description "Integration Test Schema" 
}

if (Test-Path $sampleJson) { Remove-Item $sampleJson -Force }

if ($createResult.Success -and $createResult.Output -match 'https://ns\.adobe\.com/[^/]+/schemas/([a-f0-9]+)') {
    $script:testSchemaId = $matches[0]
    Write-Host "  Schema ID: $script:testSchemaId" -ForegroundColor Gray
    
    Test-CLI "Get Schema Details" { adobe aep schema get $script:testSchemaId }
}

# Phase 3: Catalog Service
Write-Host "`n=== Phase 3: Catalog Service ===" -ForegroundColor Yellow

Test-CLI "List Datasets" { adobe aep dataset list --limit 5 }

if ($DatasetId) {
    Write-Host "`nUsing dataset: $DatasetId" -ForegroundColor Gray
    Test-CLI "Get Dataset Details" { adobe aep dataset get $DatasetId }
} else {
    Write-Host "`nWarning: No TEST_DATASET_ID - skipping dataset tests" -ForegroundColor Yellow
}

# Phase 4: Data Processing
Write-Host "`n=== Phase 4: Data Processors ===" -ForegroundColor Yellow

# Create test CSV
$testCsv = "test_$(Get-Date -Format 'yyyyMMddHHmmss').csv"
$csvData = @"
id,name,email,age,created_at
1,Alice,alice@test.com,30,2026-02-01
2,Bob,bob@test.com,25,2026-02-01
3,Charlie,charlie@test.com,35,2026-02-01
"@
Set-Content -Path $testCsv -Value $csvData
Write-Host "Created test file: $testCsv" -ForegroundColor Gray

# Test CSV to Parquet
$testParquet = $testCsv -replace '\.csv$', '.parquet'
$convScript = "conv_test.py"
@"
from adobe_experience.processors import CSVToParquetConverter
converter = CSVToParquetConverter()
result = converter.convert('$testCsv', '$testParquet')
print(f'Rows: {result["rows_processed"]}')
exit(0 if result['success'] else 1)
"@ | Set-Content $convScript

Test-CLI "CSV to Parquet Conversion" { python $convScript }
if (Test-Path $convScript) { Remove-Item $convScript -Force }

if (Test-Path $testParquet) {
    Write-Host "  Parquet file created: $testParquet" -ForegroundColor Gray
    
    # Test XDM validation
    $valScript = "val_test.py"
    @"
from adobe_experience.processors.xdm_validator import *
schema = XDMSchema(
    name='Test',
    fields=[
        XDMField(name='id', type=XDMFieldType.INTEGER, required=True),
        XDMField(name='name', type=XDMFieldType.STRING, required=True),
        XDMField(name='email', type=XDMFieldType.STRING, format=XDMFieldFormat.EMAIL),
    ]
)
validator = XDMValidator(schema)
result = validator.validate_parquet('$testParquet')
print(f'Valid: {result.valid}, Errors: {len(result.errors)}')
exit(0 if result.valid else 1)
"@ | Set-Content $valScript
    
    Test-CLI "XDM Schema Validation" { python $valScript }
    if (Test-Path $valScript) { Remove-Item $valScript -Force }
}

# Phase 5: Data Ingestion
if (-not $SkipDataIngestion -and $DatasetId) {
    Write-Host "`n=== Phase 5: Data Ingestion ===" -ForegroundColor Yellow
    
    $batchResult = Test-CLI "Create Batch" { 
        adobe aep dataset create-batch --dataset $DatasetId --format parquet 
    }
    
    if ($batchResult.Success -and $batchResult.Output -match 'batch[_-]?[a-zA-Z0-9]+') {
        $batchId = $matches[0]
        Write-Host "  Batch ID: $batchId" -ForegroundColor Gray
        
        if (Test-Path $testParquet) {
            Test-CLI "Upload File" { adobe aep ingest upload-file $testParquet --batch $batchId }
            Test-CLI "Check Status" { adobe aep ingest status $batchId }
            Test-CLI "Complete Batch" { adobe aep dataset complete-batch $batchId }
            
            Write-Host "`n  Note: Batch processing takes 5-15 mins in AEP" -ForegroundColor Yellow
            Write-Host "  Check: adobe aep dataset batch-status $batchId" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "`n=== Phase 5: Data Ingestion (SKIPPED) ===" -ForegroundColor Yellow
}

# Cleanup
if (-not $SkipCleanup) {
    Write-Host "`n=== Cleanup ===" -ForegroundColor Yellow
    
    if (Test-Path $testCsv) {
        Remove-Item $testCsv -Force
        Write-Host "Removed: $testCsv" -ForegroundColor Gray
    }
    if (Test-Path $testParquet) {
        Remove-Item $testParquet -Force
        Write-Host "Removed: $testParquet" -ForegroundColor Gray
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total:  $script:total" -ForegroundColor White
Write-Host "Passed: $script:passed" -ForegroundColor Green
Write-Host "Failed: $script:failed" -ForegroundColor $(if ($script:failed -gt 0) { "Red" } else { "White" })

if ($script:failed -eq 0) {
    Write-Host "`nAll tests PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome tests FAILED" -ForegroundColor Red
    exit 1
}
