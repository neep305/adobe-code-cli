# aep CLI - Integration Test Plan

**Date**: 2026-02-02  
**Version**: v0.2.0 (Alpha)  
**Environment**: Adobe Experience Platform Sandbox

---

## 📋 Test Overview

### Test Objectives
1. ✅ Verify Schema Registry API integration
2. ✅ Validate Catalog Service (Dataset/Batch) operations
3. ✅ Test end-to-end data ingestion workflow
4. ✅ Validate data processors (CSV/JSON → Parquet)
5. ✅ Test XDM schema validation
6. ✅ Verify error handling and retry logic

### Prerequisites Checklist

#### 1. aep Credentials
- [ ] Adobe Developer Console project created
- [ ] OAuth Server-to-Server credentials generated
- [ ] Required API scopes granted:
  - `openid`
  - `AdobeID`
  - `read_pc.dma_aep`
  - `additional_info.projectedProductContext`
  - `session`
- [ ] Credentials stored in `~/.adobe/credentials.json` or environment variables

#### 2. AEP Sandbox Access
- [ ] Sandbox name identified (e.g., `prod`, `dev`, `test`)
- [ ] Test sandbox with write permissions
- [ ] Sufficient API quota available

#### 3. Test Data Preparation
- [ ] Sample CSV file (customers, orders, etc.)
- [ ] Sample JSON file (events, profiles, etc.)
- [ ] Test dataset created or permission to create datasets

#### 4. Development Environment
- [ ] Python 3.10+ installed
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -e .`)
- [ ] CLI accessible (`adobe --version`)

---

## 🧪 Test Scenarios

### Phase 1: Authentication & Connection (Priority: CRITICAL)

#### Test 1.1: Verify OAuth Token Acquisition
**Purpose**: Ensure credentials are valid and access token can be obtained

```powershell
# Test OAuth authentication
$env:ADOBE_LOG_LEVEL="DEBUG"
aep schema list --limit 1
```

**Expected Result**:
- ✅ Access token acquired successfully
- ✅ API request returns 200 OK
- ✅ At least one schema listed

**Validation Points**:
- Token cached for reuse
- Token refresh works after expiry
- Error messages are clear if credentials invalid

**Troubleshooting**:
- Check `CLIENT_ID`, `CLIENT_SECRET`, `ORG_ID` in config
- Verify scopes in Adobe Developer Console
- Check network connectivity to `ims-na1.adobelogin.com`

---

### Phase 2: Schema Registry Operations (Priority: HIGH)

#### Test 2.1: List Existing Schemas
```powershell
# List all schemas in tenant
aep schema list --limit 10

# List with filtering
aep schema list --property "title==Customer*"
```

**Expected Result**:
- ✅ Schemas listed with ID, title, version
- ✅ Filtering works correctly
- ✅ Pagination handled properly

#### Test 2.2: Create New XDM Schema
```powershell
# Create schema manually
aep schema create `
  --name "IntegrationTestSchema" `
  --title "Integration Test Schema" `
  --description "Schema for integration testing"

# Create schema with AI assistance
aep schema create `
  --name "CustomerEventSchema" `
  --use-ai `
  --description "Schema for customer interaction events"
```

**Expected Result**:
- ✅ Schema created successfully
- ✅ Schema ID returned
- ✅ Schema appears in list
- ✅ AI-generated schema has valid XDM structure

**Validation Points**:
- Schema has valid `$id` and `meta:altId`
- Schema includes required XDM base classes
- Field types are correct

#### Test 2.3: Retrieve Schema Details
```powershell
# Get schema by ID (use ID from previous test)
aep schema get <schema_id>

# Export schema to file
aep schema export <schema_id> --output integration_test_schema.json
```

**Expected Result**:
- ✅ Full schema definition retrieved
- ✅ JSON file created with valid schema
- ✅ File can be parsed as valid JSON

#### Test 2.4: Update Schema
```powershell
# Update schema title
aep schema update <schema_id> --title "Updated Integration Test Schema"
```

**Expected Result**:
- ✅ Schema updated successfully
- ✅ Changes reflected in GET request

---

### Phase 3: Catalog Service - Dataset Management (Priority: HIGH)

#### Test 3.1: Create Dataset
```powershell
# Create dataset linked to schema
aep dataset create `
  --name "integration_test_dataset" `
  --schema-id "<schema_id_from_phase2>" `
  --description "Dataset for integration testing"
```

**Expected Result**:
- ✅ Dataset created successfully
- ✅ Dataset ID returned
- ✅ Dataset linked to schema

**Save dataset ID for next tests**: `$DATASET_ID = "dataset123abc"`

#### Test 3.2: List Datasets
```powershell
# List all datasets
aep dataset list --limit 10

# Filter by name
aep dataset list --property "name==integration*"
```

**Expected Result**:
- ✅ Datasets listed with ID, name, schema reference
- ✅ Created dataset appears in list

#### Test 3.3: Get Dataset Details
```powershell
aep dataset get $DATASET_ID
```

**Expected Result**:
- ✅ Full dataset metadata retrieved
- ✅ Schema reference is correct
- ✅ Tags and state are present

#### Test 3.4: Enable Dataset for Profile (Optional)
```powershell
# Enable for Real-Time Customer Profile
aep dataset enable-profile $DATASET_ID

# Enable for Identity Service
aep dataset enable-identity $DATASET_ID
```

**Expected Result**:
- ✅ Dataset enabled for Profile service
- ✅ Changes reflected in dataset metadata

---

### Phase 4: Data Ingestion - Batch Upload (Priority: CRITICAL)

#### Test 4.1: Create Batch
```powershell
# Create batch for dataset
aep dataset create-batch `
  --dataset $DATASET_ID `
  --format parquet
```

**Expected Result**:
- ✅ Batch created with status "loading"
- ✅ Batch ID returned

**Save batch ID**: `$BATCH_ID = "batch456def"`

#### Test 4.2: Prepare Test Data

**Create test CSV file** (`test_customers.csv`):
```csv
id,first_name,last_name,email,age,created_at
1,Alice,Smith,alice@example.com,30,2026-01-15
2,Bob,Johnson,bob@example.com,25,2026-01-16
3,Charlie,Williams,charlie@example.com,35,2026-01-17
```

**Create test JSON file** (`test_events.json`):
```json
[
  {
    "event_id": "evt001",
    "user_id": "user001",
    "event_type": "page_view",
    "timestamp": "2026-02-01T10:00:00Z",
    "properties": {
      "page_url": "https://example.com/products",
      "referrer": "https://google.com"
    }
  },
  {
    "event_id": "evt002",
    "user_id": "user002",
    "event_type": "purchase",
    "timestamp": "2026-02-01T10:05:00Z",
    "properties": {
      "product_id": "prod123",
      "amount": 99.99,
      "currency": "USD"
    }
  }
]
```

#### Test 4.3: Convert CSV to Parquet
```powershell
# Test in Python REPL
python
```

```python
from adobe_experience.processors import CSVToParquetConverter

converter = CSVToParquetConverter()
result = converter.convert(
    csv_path="test_customers.csv",
    output_path="test_customers.parquet"
)

print(f"Success: {result['success']}")
print(f"Rows: {result['rows_processed']}")
print(f"Size: {result['output_size_bytes']} bytes")
exit()
```

**Expected Result**:
- ✅ Parquet file created successfully
- ✅ All 3 rows converted
- ✅ File size > 0 bytes

#### Test 4.4: Validate with XDM Schema (Optional)
```python
from adobe_experience.processors.xdm_validator import XDMValidator, XDMSchema, XDMField, XDMFieldType, XDMFieldFormat

# Define XDM schema for validation
schema = XDMSchema(
    name="CustomerSchema",
    fields=[
        XDMField(name="id", type=XDMFieldType.INTEGER, required=True),
        XDMField(name="first_name", type=XDMFieldType.STRING, required=True, min_length=2),
        XDMField(name="email", type=XDMFieldType.STRING, format=XDMFieldFormat.EMAIL),
        XDMField(name="age", type=XDMFieldType.INTEGER, minimum=0, maximum=150),
    ]
)

validator = XDMValidator(schema)
validation = validator.validate_parquet("test_customers.parquet")

print(f"Valid: {validation.valid}")
print(f"Errors: {len(validation.errors)}")
for error in validation.errors:
    print(f"  - {error.field}: {error.message}")
exit()
```

**Expected Result**:
- ✅ Validation passes
- ✅ No errors reported

#### Test 4.5: Upload File to Batch
```powershell
# Upload single file
aep ingest upload-file `
  test_customers.parquet `
  --batch $BATCH_ID `
  --progress
```

**Expected Result**:
- ✅ File uploaded successfully
- ✅ Progress bar displayed
- ✅ Size matches local file

#### Test 4.6: Verify Upload Status
```powershell
# Check file in batch
aep ingest status $BATCH_ID --file test_customers.parquet
```

**Expected Result**:
- ✅ File exists in batch
- ✅ Size matches
- ✅ Valid flag is true

#### Test 4.7: Complete Batch
```powershell
# Mark batch as complete
aep dataset complete-batch $BATCH_ID
```

**Expected Result**:
- ✅ Batch status changes to "processing"
- ✅ No errors returned

#### Test 4.8: Monitor Batch Processing
```powershell
# Check batch status
aep dataset batch-status $BATCH_ID

# Wait for completion (polls every 5 seconds)
# Note: This may take 5-15 minutes in AEP
```

**Expected Result**:
- ✅ Batch progresses through: loading → processing → success
- ✅ Records read/written counts match
- ✅ No failures or errors

**Validation Points**:
- Check `recordsRead` matches uploaded data
- Check `recordsWritten` matches expected count
- Check `failedRecords` is 0

---

### Phase 5: Advanced Workflows (Priority: MEDIUM)

#### Test 5.1: Batch Upload Multiple Files
```powershell
# Upload multiple files concurrently
aep ingest upload-batch `
  test_customers.parquet `
  test_events.parquet `
  --batch $BATCH_ID `
  --concurrent 3
```

**Expected Result**:
- ✅ All files uploaded
- ✅ Concurrency handled properly
- ✅ No rate limit errors (429)

#### Test 5.2: Directory Upload
```powershell
# Create directory with test files
New-Item -ItemType Directory -Path test_data
Copy-Item test_customers.parquet test_data/
Copy-Item test_events.parquet test_data/

# Upload entire directory
aep ingest upload-directory `
  ./test_data `
  --batch $BATCH_ID `
  --pattern "*.parquet" `
  --concurrent 5
```

**Expected Result**:
- ✅ All .parquet files uploaded
- ✅ Progress displayed for each file
- ✅ Summary shows success count

#### Test 5.3: Batch Abort Workflow
```powershell
# Create new batch
$TEST_BATCH = aep dataset create-batch --dataset $DATASET_ID --format parquet

# Upload test file
aep ingest upload-file test_customers.parquet --batch $TEST_BATCH

# Abort batch instead of completing
aep dataset abort-batch $TEST_BATCH

# Verify status
aep dataset batch-status $TEST_BATCH
```

**Expected Result**:
- ✅ Batch status changes to "aborted"
- ✅ Data not ingested to dataset

#### Test 5.4: Large File Upload (Optional)
```powershell
# Create 50MB test file
python -c "import pandas as pd; df = pd.DataFrame({'id': range(1000000), 'data': ['x'*100]*1000000}); df.to_parquet('large_test.parquet')"

# Upload with progress tracking
aep ingest upload-file `
  large_test.parquet `
  --batch $BATCH_ID `
  --progress
```

**Expected Result**:
- ✅ Large file uploaded successfully
- ✅ Chunked upload used (if >10MB)
- ✅ Progress bar updates smoothly

---

### Phase 6: Error Handling & Edge Cases (Priority: MEDIUM)

#### Test 6.1: Invalid Credentials
```powershell
# Temporarily break credentials
$env:CLIENT_ID="invalid"
aep schema list

# Restore credentials
Remove-Item Env:CLIENT_ID
```

**Expected Result**:
- ✅ Clear error message about authentication
- ✅ No stack trace exposed to user

#### Test 6.2: Network Timeout
```powershell
# Test retry logic (simulate by disconnecting network briefly)
aep schema list
```

**Expected Result**:
- ✅ Automatic retry with exponential backoff
- ✅ Eventually succeeds or fails gracefully

#### Test 6.3: Invalid Dataset ID
```powershell
aep dataset get "invalid_dataset_id"
```

**Expected Result**:
- ✅ 404 error handled gracefully
- ✅ Clear message: "Dataset not found"

#### Test 6.4: File Upload Failures
```powershell
# Upload non-existent file
aep ingest upload-file nonexistent.parquet --batch $BATCH_ID

# Upload to non-existent batch
aep ingest upload-file test_customers.parquet --batch "invalid_batch"
```

**Expected Result**:
- ✅ Clear error messages
- ✅ No crashes or stack traces

#### Test 6.5: Rate Limiting (429 Errors)
```powershell
# Make many rapid requests
for ($i=1; $i -le 100; $i++) {
    aep schema list --limit 1
}
```

**Expected Result**:
- ✅ Automatic retry with backoff
- ✅ Eventually succeeds
- ✅ Warning logged about rate limits

---

## 📊 Test Execution Tracking

### Test Run Log Template

```
Test Date: 2026-02-02
Tester: [Your Name]
Environment: AEP Sandbox (dev/test)
CLI Version: v0.2.0

Phase 1: Authentication
[✅] Test 1.1: OAuth Token - PASS
Notes: Token acquired in 1.2s

Phase 2: Schema Registry
[✅] Test 2.1: List Schemas - PASS
[✅] Test 2.2: Create Schema - PASS
    Schema ID: https://ns.adobe.com/[org]/schemas/abc123
[✅] Test 2.3: Get Schema - PASS
[❌] Test 2.4: Update Schema - FAIL
    Error: HTTP 403 - Insufficient permissions
    Action: Contact admin for write access

Phase 3: Catalog Service
[✅] Test 3.1: Create Dataset - PASS
    Dataset ID: 67890abcdef1234567890abc
[✅] Test 3.2: List Datasets - PASS
[✅] Test 3.3: Get Dataset - PASS
[⚠️] Test 3.4: Enable Profile - SKIP
    Reason: Profile service not needed for test

Phase 4: Data Ingestion
[✅] Test 4.1: Create Batch - PASS
    Batch ID: batch_test_20260202_001
[✅] Test 4.3: CSV to Parquet - PASS
    3 rows converted, 2.1 KB file
[✅] Test 4.4: XDM Validation - PASS
    No validation errors
[✅] Test 4.5: Upload File - PASS
    Uploaded in 3.5s
[✅] Test 4.7: Complete Batch - PASS
[🔄] Test 4.8: Monitor Batch - IN PROGRESS
    Waiting for AEP processing (ETA: 10 mins)

Phase 5: Advanced Workflows
[⏸️] Test 5.1-5.4: PENDING
    Waiting for Phase 4 completion

Phase 6: Error Handling
[⏸️] Test 6.1-6.5: PENDING

Summary:
Total Tests: 20
Passed: 12
Failed: 1
Skipped: 1
Pending: 6
In Progress: 1
```

---

## 🐛 Known Issues & Workarounds

### Issue 1: Token Expiry During Long Operations
**Symptom**: "401 Unauthorized" after 24 hours  
**Workaround**: Re-run command; token auto-refreshes

### Issue 2: Batch Processing Delays
**Symptom**: Batch stuck in "processing" for >30 minutes  
**Workaround**: Check AEP UI, may be system-wide delay

### Issue 3: Large File Timeouts
**Symptom**: Upload fails for files >100MB  
**Workaround**: Use chunked upload, increase timeout in config

---

## 📈 Success Criteria

### Minimum Viable Integration (MUST PASS)
- ✅ Authentication works
- ✅ Can list schemas/datasets
- ✅ Can create dataset
- ✅ Can upload file to batch
- ✅ Batch completes successfully
- ✅ Data appears in AEP UI

### Full Integration Success (SHOULD PASS)
- ✅ All CRUD operations work
- ✅ CSV/JSON converters work
- ✅ XDM validation catches errors
- ✅ Concurrent uploads succeed
- ✅ Error handling is robust
- ✅ Retry logic prevents transient failures

### Performance Benchmarks
- Token acquisition: < 2 seconds
- Schema list: < 3 seconds
- File upload (10MB): < 10 seconds
- Batch creation: < 2 seconds

---

## 🔧 Debugging Tools

### Enable Debug Logging
```powershell
$env:ADOBE_LOG_LEVEL="DEBUG"
aep schema list > debug.log 2>&1
```

### Inspect HTTP Traffic
```powershell
# Use httpx debug mode
python -c "
import httpx
import os
os.environ['HTTPX_LOG_LEVEL'] = 'DEBUG'
from adobe_experience.aep.client import AEPClient
# ... test code
"
```

### Check AEP UI
- Datasets: `https://experience.adobe.com/#/@[org]/platform/dataset/browse`
- Batches: Check dataset → "Batches" tab
- Schemas: `https://experience.adobe.com/#/@[org]/platform/schema/browse`

---

## 📝 Test Report Template

After completing tests, generate report:

```markdown
# AEP CLI Integration Test Report

**Date**: 2026-02-02
**Environment**: AEP Sandbox (dev)
**CLI Version**: v0.2.0
**Tester**: [Name]

## Summary
- Total Tests: 20
- Passed: 18 (90%)
- Failed: 1 (5%)
- Skipped: 1 (5%)

## Critical Issues
None

## Minor Issues
1. Schema update requires additional permissions

## Performance
- Average API response time: 1.2s
- File upload speed: ~3 MB/s
- Batch processing time: 8 minutes (typical)

## Recommendations
1. Document permission requirements
2. Add progress estimate for batch processing
3. Consider bulk schema operations

## Sign-off
- [ ] Core functionality verified
- [ ] Ready for beta testing
- [ ] Documentation updated
```

---

## 🚀 Next Steps After Integration Test

1. **Fix Critical Bugs**: Address any test failures
2. **Performance Optimization**: Improve slow operations
3. **Documentation**: Update based on real-world usage
4. **Beta Testing**: Share with select users
5. **Monitoring**: Set up error tracking (Sentry, etc.)
6. **CI/CD**: Automate integration tests in pipeline
