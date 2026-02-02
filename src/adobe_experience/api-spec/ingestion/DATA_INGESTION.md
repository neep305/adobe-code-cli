# Data Ingestion API - Implementation Guide

## Overview
The Data Ingestion module provides comprehensive file upload capabilities to Adobe Experience Platform (AEP) batches. It supports single file uploads, concurrent batch uploads, directory uploads with pattern matching, and chunked uploads with progress tracking.

**Module**: `adobe_experience.ingestion`  
**Status**: ✅ Complete (Phase 1)  
**Test Coverage**: 98% (bulk_upload.py), 0% (progress_upload.py - integration only)  
**CLI Commands**: 4 commands registered under `adobe aep ingest`

---

## Architecture

### Core Components

```
adobe_experience/ingestion/
├── __init__.py              # Module exports
├── bulk_upload.py           # File upload client (sync & async)
└── progress_upload.py       # Chunked upload with progress tracking
```

### Client Classes

#### 1. **BulkIngestClient** (`bulk_upload.py`)
Core file upload client for AEP batches.

**Key Features:**
- Single file upload with auto-detection of MIME types
- Concurrent multi-file uploads with semaphore control (max_concurrent=3)
- Directory uploads with glob pattern matching and recursion
- Upload status checking via Catalog Service integration

**Usage:**
```python
from adobe_experience.ingestion.bulk_upload import BulkIngestClient
from adobe_experience.aep.client import AEPClient

aep_client = AEPClient(client_id, client_secret, org_id, sandbox_name)
bulk = BulkIngestClient(aep_client)

# Upload single file
result = await bulk.upload_file(
    file_path="customers.json",
    batch_id="batch123",
    file_name="customers_data.json"  # Optional custom name
)

# Upload multiple files concurrently
results = await bulk.upload_multiple_files(
    file_paths=["file1.json", "file2.json", "file3.json"],
    batch_id="batch123",
    max_concurrent=5
)

# Upload entire directory
results = await bulk.upload_directory(
    directory="./data",
    batch_id="batch123",
    pattern="*.json",
    recursive=True,
    max_concurrent=3
)

# Check file upload status
status = await bulk.get_upload_status(
    batch_id="batch123",
    file_name="customers.json"
)
# Returns: {"exists": True, "file_name": "...", "size_bytes": 1024, "records": 100, "is_valid": True}
```

#### 2. **BulkIngestClientWithProgress** (`progress_upload.py`)
Enhanced client with chunked uploads and Rich progress bars for large files.

**Key Features:**
- Chunked uploads (10MB chunks) for large files
- Real-time progress tracking with Rich UI
- Content-Range header support for multipart uploads
- Same API as BulkIngestClient for drop-in replacement

**Usage:**
```python
from adobe_experience.ingestion.progress_upload import BulkIngestClientWithProgress

bulk = BulkIngestClientWithProgress(aep_client)

# Upload with progress bar (automatic for files > 10MB)
result = await bulk.upload_file(
    file_path="large_dataset.csv",
    batch_id="batch123"
)
```

**Internal Components:**
- `ChunkedUploader`: Handles 10MB chunked uploads with Content-Range headers
- `ProgressTracker`: Rich Progress UI with SpinnerColumn, BarColumn, TimeRemainingColumn

---

## API Methods

### BulkIngestClient.upload_file()

Upload a single file to an AEP batch.

**Signature:**
```python
async def upload_file(
    self,
    file_path: Union[str, Path],
    batch_id: str,
    file_name: Optional[str] = None,
) -> Dict[str, Any]
```

**Parameters:**
- `file_path`: Path to file to upload
- `batch_id`: Target batch ID in AEP
- `file_name`: Optional custom name in AEP (defaults to original filename)

**Returns:**
```python
{
    "success": True,
    "file_name": "customers.json",
    "size_bytes": 2048,
    "batch_id": "batch123",
    "content_type": "application/json"
}
# OR on error:
{
    "success": False,
    "file_name": "customers.json",
    "error": "File not found"
}
```

**HTTP Request:**
```
PUT /batches/{batchId}/datasets/{datasetId}/files/{fileName}
Host: platform.adobe.io
Authorization: Bearer {ACCESS_TOKEN}
x-api-key: {CLIENT_ID}
x-gw-ims-org-id: {ORG_ID}
x-sandbox-name: {SANDBOX_NAME}
Content-Type: application/json

[Binary file content]
```

**Validations:**
- File must exist and be readable
- File size must be <= 10GB (enforced by AEP)
- Empty files rejected (raises ValueError)
- MIME type auto-detected from extension (falls back to application/octet-stream)

---

### BulkIngestClient.upload_multiple_files()

Upload multiple files concurrently to an AEP batch.

**Signature:**
```python
async def upload_multiple_files(
    self,
    file_paths: List[Union[str, Path]],
    batch_id: str,
    max_concurrent: int = 3,
) -> List[Dict[str, Any]]
```

**Parameters:**
- `file_paths`: List of file paths to upload
- `batch_id`: Target batch ID
- `max_concurrent`: Maximum concurrent uploads (default: 3, recommended: 3-5)

**Returns:**
List of result dictionaries (one per file), same format as `upload_file()`.

**Concurrency Control:**
Uses `asyncio.Semaphore` to limit concurrent uploads and prevent API rate limiting (429 errors).

**Example:**
```python
results = await bulk.upload_multiple_files(
    file_paths=[
        "customers.json",
        "orders.json",
        "products.json",
        "events.json"
    ],
    batch_id="batch123",
    max_concurrent=3  # Upload 3 at a time
)

# Check results
for result in results:
    if result["success"]:
        print(f"✓ {result['file_name']}")
    else:
        print(f"✗ {result['file_name']}: {result['error']}")
```

---

### BulkIngestClient.upload_directory()

Upload all matching files from a directory to an AEP batch.

**Signature:**
```python
async def upload_directory(
    self,
    directory: Union[str, Path],
    batch_id: str,
    pattern: str = "*",
    recursive: bool = False,
    max_concurrent: int = 3,
) -> List[Dict[str, Any]]
```

**Parameters:**
- `directory`: Directory path to scan
- `batch_id`: Target batch ID
- `pattern`: Glob pattern (default: `*` = all files). Examples: `*.json`, `*.csv`, `data_*.parquet`
- `recursive`: Search subdirectories (default: False)
- `max_concurrent`: Max concurrent uploads

**Returns:**
List of result dictionaries for all uploaded files.

**Examples:**
```python
# Upload all JSON files in directory
results = await bulk.upload_directory(
    directory="./exports",
    batch_id="batch123",
    pattern="*.json"
)

# Upload all CSV files recursively
results = await bulk.upload_directory(
    directory="./data",
    batch_id="batch123",
    pattern="*.csv",
    recursive=True
)

# Upload everything (any file type)
results = await bulk.upload_directory(
    directory="./batch_data",
    batch_id="batch123",
    pattern="*",
    recursive=False
)
```

**File Discovery:**
- Non-recursive: Uses `Path.glob(pattern)` to find files in directory only
- Recursive: Uses `Path.rglob(pattern)` to search all subdirectories
- Skips directories (only uploads files)
- Returns empty list if no files match pattern

---

### BulkIngestClient.get_upload_status()

Check if a file exists in a batch and retrieve its metadata.

**Signature:**
```python
async def get_upload_status(
    self,
    batch_id: str,
    file_name: str
) -> Dict[str, Any]
```

**Parameters:**
- `batch_id`: Batch ID to check
- `file_name`: Name of file to search for

**Returns:**
```python
# If file exists:
{
    "exists": True,
    "file_name": "customers.json",
    "size_bytes": 2048,
    "records": 150,
    "is_valid": True
}

# If file not found:
{
    "exists": False,
    "file_name": "customers.json"
}
```

**Implementation:**
Queries Catalog Service `GET /datasets/{datasetId}/views/{batchId}/files` and searches for matching file name.

---

## CLI Commands

All commands available under `adobe aep ingest`:

### 1. `upload-file` - Upload Single File

```bash
adobe aep ingest upload-file <file_path> --batch <batch_id> [--name <custom_name>] [--progress/--no-progress]

# Examples:
adobe aep ingest upload-file customers.json --batch abc123
adobe aep ingest upload-file data.csv --batch abc123 --name customers_v2.csv
adobe aep ingest upload-file large.parquet --batch abc123 --no-progress
```

**Options:**
- `--batch, -b`: (Required) Batch ID to upload to
- `--name, -n`: Custom file name in AEP (optional)
- `--progress/--no-progress`: Show/hide progress bar (default: show)

**Output:**
```
✓ Successfully uploaded customers.json
Size: 2,048 bytes
Batch ID: abc123
```

---

### 2. `upload-batch` - Upload Multiple Files

```bash
adobe aep ingest upload-batch <file1> <file2> ... --batch <batch_id> [--concurrent <num>]

# Examples:
adobe aep ingest upload-batch file1.json file2.json file3.json --batch abc123
adobe aep ingest upload-batch *.json --batch abc123 --concurrent 5
```

**Options:**
- `--batch, -b`: (Required) Batch ID
- `--concurrent, -c`: Max concurrent uploads (default: 3)

**Output:**
Rich table showing upload results:
```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ File              ┃ Status     ┃ Size      ┃ Details             ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ file1.json        │ ✓ Success  │ 1,024 B   │ file1.json          │
│ file2.json        │ ✓ Success  │ 2,048 B   │ file2.json          │
│ file3.json        │ ✗ Failed   │ -         │ File too large      │
└───────────────────┴────────────┴───────────┴─────────────────────┘

Summary: 2/3 files uploaded successfully
```

---

### 3. `upload-directory` - Upload Directory

```bash
adobe aep ingest upload-directory <directory> --batch <batch_id> [--pattern <glob>] [--recursive] [--concurrent <num>]

# Examples:
adobe aep ingest upload-directory ./data --batch abc123 --pattern "*.json"
adobe aep ingest upload-directory ./exports --batch abc123 --recursive --concurrent 5
adobe aep ingest upload-directory ./batch_data --batch abc123 --pattern "*.csv"
```

**Options:**
- `--batch, -b`: (Required) Batch ID
- `--pattern, -p`: Glob pattern (default: `*`)
- `--recursive, -r`: Search subdirectories (default: false)
- `--concurrent, -c`: Max concurrent uploads (default: 3)

**Output:**
Same rich table as `upload-batch`, showing relative paths from directory.

---

### 4. `status` - Check Upload Status

```bash
adobe aep ingest status <batch_id> [--file <file_name>]

# Examples:
adobe aep ingest status abc123
adobe aep ingest status abc123 --file customers.json
```

**Options:**
- `--file, -f`: Check specific file (optional, shows all files if omitted)

**Output (batch overview):**
```
┌─────────────────────┐
│ Batch abc123        │
├─────────────────────┤
│ Status: success     │
│ Dataset: ds456      │
│ Created: 1234567890 │
│ Records: 500        │
└─────────────────────┘
```

**Output (specific file):**
```
┌─────────────────────┐
│ File Status         │
├─────────────────────┤
│ File: customers.json│
│ Size: 2,048 bytes   │
│ Records: 150        │
│ Valid: ✓            │
└─────────────────────┘
```

**Output (all files):**
```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┓
┃ File Name         ┃ Size      ┃ Records   ┃ Valid ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━┩
│ customers.json    │ 2,048 B   │ 150       │ ✓     │
│ orders.json       │ 4,096 B   │ 200       │ ✓     │
│ products.json     │ 1,024 B   │ 50        │ ✓     │
└───────────────────┴───────────┴───────────┴───────┘
```

---

## Implementation Details

### MIME Type Detection

Uses `mimetypes.guess_type()` with fallback:
- `.json` → `application/json`
- `.csv` → `text/csv`
- `.parquet` → `application/octet-stream`
- `.txt` → `text/plain`
- Unknown → `application/octet-stream`

### File Size Limits

- **Minimum**: 1 byte (empty files rejected)
- **Maximum**: 10GB (10,737,418,240 bytes) - enforced by AEP
- Files > 10MB automatically use chunked upload in `BulkIngestClientWithProgress`

### Error Handling

All methods return result dictionaries with `success` boolean:
- `FileNotFoundError` → `{"success": False, "error": "File not found"}`
- `ValueError` (empty file) → `{"success": False, "error": "File is empty"}`
- `httpx.HTTPError` → `{"success": False, "error": "HTTP 429: Rate limit exceeded"}`
- Generic exceptions → `{"success": False, "error": str(e)}`

CLI commands exit with code 1 on failure.

### Retry Logic

Inherits from `AEPClient.put()`:
- Retries on 429 (rate limit) and 5xx errors
- Exponential backoff: 1s → 2s → 4s → 8s → 16s
- Max retries: 5

---

## Testing

### Unit Tests (`tests/test_bulk_upload.py`)

**Coverage**: 98% (61/62 lines)  
**Tests**: 15 test cases

```bash
pytest tests/test_bulk_upload.py -v --cov=src/adobe_experience/ingestion/bulk_upload
```

**Test Categories:**
1. **Single file upload**: Success, custom name, not found, empty file, too large
2. **Multiple files**: Success, partial failures
3. **Directory upload**: Success, pattern matching, recursive, not found, no matches
4. **Status checking**: File exists, file not exists
5. **Utilities**: Content-type detection

**Key Test Patterns:**
- Mock `AEPClient.put()` with `AsyncMock`
- Use `tmp_path` fixture for file creation
- Mock `CatalogServiceClient` at `adobe_experience.catalog.client.CatalogServiceClient` (not module-level import)

---

## Integration Testing

### End-to-End Workflow

```python
from adobe_experience.aep.client import AEPClient
from adobe_experience.catalog.client import CatalogServiceClient
from adobe_experience.ingestion.bulk_upload import BulkIngestClient

# 1. Create batch
catalog = CatalogServiceClient(aep_client)
batch = await catalog.create_batch(dataset_id="dataset123")

# 2. Upload files
bulk = BulkIngestClient(aep_client)
results = await bulk.upload_directory(
    directory="./data",
    batch_id=batch.id,
    pattern="*.json"
)

# 3. Complete batch
await catalog.complete_batch(batch.id)

# 4. Wait for processing
final_batch = await catalog.wait_for_batch_completion(
    batch_id=batch.id,
    timeout=300
)

# 5. Verify results
assert final_batch.status == BatchStatus.SUCCESS
```

---

## Next Steps (Phase 2)

### Pending Implementation:
1. **Data Processors** (`processors/`)
   - CSV → Parquet converter
   - JSON → Parquet converter
   - Schema validation against XDM
   - Data transformation pipeline

2. **Streaming Ingestion** (`streaming/`)
   - HTTP streaming client
   - Kafka connector
   - Real-time event ingestion

3. **Data Validation** (`validation/`)
   - Pre-upload schema validation
   - Data quality checks (nullability, types, ranges)
   - Duplicate detection

4. **Integration Tests**
   - Live AEP sandbox tests
   - Large file upload tests (>1GB)
   - Concurrent upload stress tests

---

## References

- **AEP Data Ingestion**: https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/home
- **Batch Ingestion API**: https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/batch/api-overview
- **Catalog Service API**: https://developer.adobe.com/experience-platform-apis/references/catalog/
- **File Upload Limits**: https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/batch/overview#constraints
