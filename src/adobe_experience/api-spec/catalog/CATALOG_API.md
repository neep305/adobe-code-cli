# Adobe Experience Platform - Catalog Service API

## Overview

The Catalog Service is Adobe Experience Platform's system of record for data location and lineage. It manages metadata for datasets, batches, and data files.

**Base URL**: `https://platform.adobe.io/data/foundation/catalog`

**API Reference**: https://developer.adobe.com/experience-platform-apis/references/catalog/

## Authentication

All Catalog Service requests require:
- `Authorization: Bearer {ACCESS_TOKEN}`
- `x-api-key: {CLIENT_ID}`
- `x-gw-ims-org-id: {ORG_ID}`
- `x-sandbox-name: {SANDBOX_NAME}`

## Implemented Endpoints

### Datasets API

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/dataSets` | List datasets | ✅ Implemented |
| GET | `/dataSets/{DATASET_ID}` | Get dataset details | ✅ Implemented |
| POST | `/dataSets` | Create dataset | ✅ Implemented |
| PATCH | `/dataSets/{DATASET_ID}` | Update dataset | ✅ Implemented |
| DELETE | `/dataSets/{DATASET_ID}` | Delete dataset | ✅ Implemented |

#### List Datasets

```http
GET /data/foundation/catalog/dataSets?limit=50&properties=name,schemaRef
```

**Query Parameters**:
- `limit` (int): Max results (default: 50, max: 100)
- `properties` (string): Comma-separated list of properties to return
- `schemaRef.id` (string): Filter by schema ID
- `state` (string): Filter by state (DRAFT or ENABLED)

**Response**:
```json
{
  "5c8c3c555033b814b69f947f": {
    "name": "Customer Events Dataset",
    "schemaRef": {
      "id": "https://ns.adobe.com/tenant/schemas/abc123",
      "contentType": "application/vnd.adobe.xed+json;version=1"
    },
    "state": "ENABLED",
    "created": 1234567890000,
    "updated": 1234567890000
  }
}
```

#### Create Dataset

```http
POST /data/foundation/catalog/dataSets
Content-Type: application/json

{
  "name": "Customer Events",
  "schemaRef": {
    "id": "https://ns.adobe.com/tenant/schemas/abc123",
    "contentType": "application/vnd.adobe.xed+json;version=1"
  },
  "description": "Customer behavioral events",
  "tags": {
    "unifiedProfile": ["enabled:true"],
    "unifiedIdentity": ["enabled:true"]
  }
}
```

**Response**:
```json
["@/dataSets/5c8c3c555033b814b69f947f"]
```

### Batches API

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/batches` | List batches | ✅ Implemented |
| GET | `/batches/{BATCH_ID}` | Get batch status | ✅ Implemented |
| POST | `/import/batches` | Create batch | ✅ Implemented |
| POST | `/import/batches/{BATCH_ID}?action=COMPLETE` | Complete batch | ✅ Implemented |
| POST | `/import/batches/{BATCH_ID}?action=ABORT` | Abort batch | ✅ Implemented |

#### Create Batch

```http
POST /data/foundation/import/batches
Content-Type: application/json

{
  "datasetId": "5c8c3c555033b814b69f947f",
  "inputFormat": {
    "format": "parquet"
  }
}
```

**Response**:
```json
{
  "id": "5d01230fc78a4e4f8c0c6b387b4b8d1c",
  "imsOrg": "org@AdobeOrg",
  "status": "loading",
  "created": 1552694873602,
  "updated": 1552694873602,
  "relatedObjects": [
    {"type": "dataSet", "id": "5c8c3c555033b814b69f947f"}
  ],
  "version": "1.0.0",
  "inputFormat": {"format": "parquet"}
}
```

#### Batch Status Values

- `loading`: Batch created, awaiting file uploads
- `staged`: Files uploaded, awaiting completion signal
- `processing`: Batch marked complete, processing in progress
- `success`: All data successfully ingested
- `failed`: Ingestion failed
- `aborted`: Batch aborted by user
- `retrying`: Automatic retry in progress

### DataSetFiles API

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/dataSetFiles` | List dataset files | ✅ Implemented |

#### List DataSet Files

```http
GET /data/foundation/catalog/dataSetFiles?batchId={BATCH_ID}
```

**Query Parameters**:
- `dataSetId` (string): Filter by dataset ID
- `batchId` (string): Filter by batch ID
- `limit` (int): Max results

**Response**:
```json
{
  "file1": {
    "@id": "file1",
    "dataSetId": "5c8c3c555033b814b69f947f",
    "batchId": "5d01230fc78a4e4f8c0c6b387b4b8d1c",
    "name": "customers.parquet",
    "sizeInBytes": 1048576,
    "records": 1000,
    "created": 1234567890000,
    "isValid": true
  }
}
```

## CLI Usage

### Dataset Management

```bash
# List datasets
aep dataset list
aep dataset list --limit 50
aep dataset list --schema "https://ns.adobe.com/tenant/schemas/abc123"
aep dataset list --state ENABLED

# Create dataset
aep dataset create \
  --name "Customer Events" \
  --schema "https://ns.adobe.com/tenant/schemas/abc123" \
  --enable-profile

# Get dataset details
aep dataset get 5c8c3c555033b814b69f947f
aep dataset get 5c8c3c555033b814b69f947f --output dataset.json

# Enable for Profile/Identity
aep dataset enable-profile 5c8c3c555033b814b69f947f
aep dataset enable-identity 5c8c3c555033b814b69f947f

# Delete dataset
aep dataset delete 5c8c3c555033b814b69f947f --yes
```

### Batch Management

```bash
# Create batch
aep dataset create-batch \
  --dataset 5c8c3c555033b814b69f947f \
  --format json

# List batches
aep dataset list-batches
aep dataset list-batches --dataset 5c8c3c555033b814b69f947f
aep dataset list-batches --status success

# Check batch status
aep dataset batch-status 5d01230fc78a4e4f8c0c6b387b4b8d1c
aep dataset batch-status 5d01230fc78a4e4f8c0c6b387b4b8d1c --watch

# Complete batch (after file upload)
aep dataset complete-batch 5d01230fc78a4e4f8c0c6b387b4b8d1c
aep dataset complete-batch 5d01230fc78a4e4f8c0c6b387b4b8d1c --wait

# Abort batch
aep dataset abort-batch 5d01230fc78a4e4f8c0c6b387b4b8d1c --yes
```

## Python Client Usage

### Dataset Operations

```python
import asyncio
from adobe_experience.aep.client import AEPClient
from adobe_experience.catalog.client import CatalogServiceClient
from adobe_experience.core.config import get_config

async def main():
    async with AEPClient(get_config()) as aep_client:
        catalog = CatalogServiceClient(aep_client)
        
        # Create dataset
        dataset_id = await catalog.create_dataset(
            name="Customer Events",
            schema_id="https://ns.adobe.com/tenant/schemas/abc123",
            enable_profile=True
        )
        print(f"Created dataset: {dataset_id}")
        
        # List datasets
        datasets = await catalog.list_datasets(limit=10)
        for ds in datasets:
            print(f"{ds.name}: {ds.state}")
        
        # Get dataset details
        dataset = await catalog.get_dataset(dataset_id)
        print(f"Dataset: {dataset.name}, State: {dataset.state}")

asyncio.run(main())
```

### Batch Operations

```python
async def batch_workflow():
    async with AEPClient(get_config()) as aep_client:
        catalog = CatalogServiceClient(aep_client)
        
        # Create batch
        batch_id = await catalog.create_batch(
            dataset_id="5c8c3c555033b814b69f947f",
            format="json"
        )
        print(f"Created batch: {batch_id}")
        
        # TODO: Upload files (not yet implemented)
        # await upload_files(batch_id, files)
        
        # Complete batch
        await catalog.complete_batch(batch_id)
        
        # Wait for processing
        batch = await catalog.wait_for_batch_completion(
            batch_id,
            timeout=300,
            poll_interval=5
        )
        
        print(f"Batch status: {batch.status}")
        if batch.metrics:
            print(f"Records written: {batch.metrics.records_written}")

asyncio.run(batch_workflow())
```

## Error Handling

### Common HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process response |
| 201 | Created | Extract ID from response |
| 204 | No Content | Return empty (DELETE success) |
| 400 | Bad Request | Check schema ref, dataset config |
| 404 | Not Found | Dataset/batch doesn't exist |
| 409 | Conflict | Dataset name already exists |
| 429 | Rate Limit | Retry with exponential backoff |
| 5xx | Server Error | Retry with backoff |

### Error Response Format

```json
{
  "reason": "Invalid schema reference",
  "message": "Schema with id 'https://...' does not exist"
}
```

## Data Ingestion Workflow

1. **Create Dataset**: Associate with an XDM schema
2. **Create Batch**: Specify input format (parquet, json, csv)
3. **Upload Files**: Upload data files to batch (not yet implemented in CLI)
4. **Complete Batch**: Signal all files uploaded
5. **Monitor Status**: Poll batch status until success/failure
6. **Verify Data**: Query dataset to confirm ingestion

## Not Yet Implemented

The following Catalog Service features are not yet implemented:

- **File Upload**: Binary file upload to batches
- **Streaming Ingestion**: Real-time data ingestion
- **Connections API**: Data source management
- **Account API**: Account credentials management

## API Coverage

**Catalog Service Coverage**: 16/40+ endpoints (40%)

- ✅ Datasets: 5/5 core operations
- ✅ Batches: 5/5 core operations
- ✅ DataSetFiles: 1/3 operations
- ❌ Connections: 0/6 operations
- ❌ Accounts: 0/5 operations
- ❌ Export/Import: 0/4 operations

## References

- [Catalog Service API Reference](https://developer.adobe.com/experience-platform-apis/references/catalog/)
- [Data Ingestion Overview](https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/home)
- [Batch Ingestion Guide](https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/batch/overview)
- [Dataset Guide](https://experienceleague.adobe.com/en/docs/experience-platform/catalog/datasets/overview)
