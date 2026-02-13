# Adobe Experience Platform Flow Service API

Flow Service는 Adobe Experience Platform에서 데이터 수집을 자동화하는 데이터 플로우(dataflow)를 관리하는 서비스입니다. 다양한 소스(클라우드 스토리지, CRM, 데이터베이스 등)에서 AEP로 데이터를 가져오는 파이프라인을 설정하고 모니터링할 수 있습니다.

## Base URL
```
https://platform.adobe.io/data/foundation/flowservice
```

## Authentication
Flow Service는 다른 AEP 서비스와 동일한 OAuth Server-to-Server 인증을 사용합니다.

**Required Headers:**
- `Authorization: Bearer {ACCESS_TOKEN}`
- `x-api-key: {API_KEY}`
- `x-gw-ims-org-id: {ORG_ID}`
- `x-sandbox-name: {SANDBOX_NAME}`
- `Content-Type: application/json` (POST/PATCH requests)

## Key Concepts

### Dataflow (Flow)
데이터 수집 파이프라인의 전체 구성. Source connection, target connection, schedule, transformation 정보를 포함합니다.

### Connection
소스 또는 타겟 시스템에 대한 인증 정보와 연결 설정.

### Source Connection
데이터를 가져올 소스 시스템 연결 (예: S3 bucket, Salesforce).

### Target Connection
데이터를 저장할 AEP 타겟 (일반적으로 데이터셋).

### Flow Run
Dataflow의 개별 실행 인스턴스. Schedule에 따라 또는 수동으로 트리거됩니다.

### Flow Spec
Dataflow의 템플릿 또는 정의. 소스 유형에 따라 다른 스펙 사용.

## API Endpoints

### Dataflows

#### List Dataflows
```http
GET /flows
```

**Query Parameters:**
- `limit` (integer): 반환할 최대 결과 수 (default: 20, max: 100)
- `start` (string): 페이지네이션 시작 포인터
- `property` (string): 필터링 속성 (예: `flowSpec.id==some-id`)
- `orderby` (string): 정렬 기준 (예: `createdAt:desc`)

**Response:**
```json
{
  "items": [
    {
      "id": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
      "name": "Customer Data Ingestion",
      "description": "Daily customer data sync from S3",
      "flowSpec": {
        "id": "9753525b-82c7-4dce-8a9b-5ccfce2b9876",
        "version": "1.0"
      },
      "sourceConnectionIds": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
      "targetConnectionIds": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"],
      "scheduleParams": {
        "startTime": 1617235200,
        "interval": 86400,
        "frequency": "day"
      },
      "state": "enabled",
      "createdAt": 1617235200000,
      "updatedAt": 1617321600000,
      "createdBy": "USER_ID",
      "etag": "\"1a2b3c4d\""
    }
  ],
  "_page": {
    "orderby": "createdAt:desc",
    "start": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
    "count": 1,
    "next": "nextPageToken"
  },
  "_links": {
    "next": {
      "href": "https://platform.adobe.io/data/foundation/flowservice/flows?start=nextPageToken"
    }
  }
}
```

#### Get Dataflow Details
```http
GET /flows/{id}
```

**Path Parameters:**
- `id` (string, required): Dataflow ID

**Response:**
```json
{
  "id": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
  "name": "Customer Data Ingestion",
  "description": "Daily customer data sync from S3",
  "flowSpec": {
    "id": "9753525b-82c7-4dce-8a9b-5ccfce2b9876",
    "version": "1.0"
  },
  "sourceConnectionIds": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
  "targetConnectionIds": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"],
  "transformations": [
    {
      "name": "Mapping",
      "params": {
        "mappingId": "mapping123",
        "mappingVersion": 0
      }
    }
  ],
  "scheduleParams": {
    "startTime": 1617235200,
    "interval": 86400,
    "frequency": "day"
  },
  "state": "enabled",
  "inheritedAttributes": {
    "sourceConnections": [
      {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "connectionSpec": {
          "id": "ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a",
          "name": "Amazon S3"
        }
      }
    ],
    "targetConnections": [
      {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "connectionSpec": {
          "id": "c604ff05-7f1a-43c0-8e18-33bf874cb11c",
          "name": "Data Lake"
        }
      }
    ]
  },
  "createdAt": 1617235200000,
  "updatedAt": 1617321600000,
  "createdBy": "USER_ID",
  "etag": "\"1a2b3c4d\""
}
```

#### Update Dataflow (Enable/Disable)
```http
PATCH /flows/{id}
Content-Type: application/json
If-Match: {etag}
```

**Request Body:**
```json
{
  "op": "replace",
  "path": "/state",
  "value": "disabled"
}
```

**Response:** Updated dataflow object

### Flow Runs

#### List Flow Runs
```http
GET /runs
```

**Query Parameters:**
- `property` (string): 필터링 (예: `flowId==d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a`)
- `limit` (integer): 반환할 최대 결과 수
- `orderby` (string): 정렬 (예: `createdAt:desc`)

**Response:**
```json
{
  "items": [
    {
      "id": "run-12345678-abcd-ef01-2345-6789abcdef01",
      "flowId": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
      "status": {
        "value": "success",
        "errors": []
      },
      "metrics": {
        "recordsRead": 10000,
        "recordsWritten": 10000,
        "filesRead": 1,
        "recordsFailed": 0,
        "durationSummary": {
          "startedAtUTC": 1617235200000,
          "completedAtUTC": 1617235500000
        }
      },
      "activities": [
        {
          "id": "activity-1",
          "activityType": "ingestion",
          "status": "success",
          "durationSummary": {
            "startedAtUTC": 1617235200000,
            "completedAtUTC": 1617235500000
          }
        }
      ],
      "createdAt": 1617235200000,
      "updatedAt": 1617235500000,
      "etag": "\"abc123\""
    }
  ],
  "_page": {
    "count": 1
  }
}
```

#### Get Run Details
```http
GET /runs/{id}
```

**Response:** Single run object with detailed metrics and error information.

**Error Object Structure (when status.value is "failed"):**
```json
{
  "status": {
    "value": "failed",
    "errors": [
      {
        "code": "CONNECTOR-400",
        "message": "Invalid credentials for source connection",
        "details": {
          "connector": "s3",
          "errorType": "AuthenticationError"
        }
      }
    ]
  }
}
```

### Connections

#### Get Source Connection
```http
GET /sourceConnections/{id}
```

**Response:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "S3 Source",
  "baseConnectionId": "base-conn-123",
  "connectionSpec": {
    "id": "ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a",
    "version": "1.0"
  },
  "params": {
    "s3": {
      "bucketName": "customer-data",
      "folderPath": "/daily-exports"
    }
  },
  "createdAt": 1617235200000,
  "updatedAt": 1617235200000,
  "etag": "\"xyz789\""
}
```

#### Get Target Connection
```http
GET /targetConnections/{id}
```

**Response:**
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "name": "Data Lake Target",
  "baseConnectionId": "base-conn-456",
  "connectionSpec": {
    "id": "c604ff05-7f1a-43c0-8e18-33bf874cb11c",
    "version": "1.0"
  },
  "params": {
    "dataSetId": "5e8c8c8e8c8c8c8c8c8c8c8c"
  },
  "createdAt": 1617235200000,
  "updatedAt": 1617235200000,
  "etag": "\"def456\""
}
```

#### Get Connection (Base)
```http
GET /connections/{id}
```

**Response:**
```json
{
  "id": "base-conn-123",
  "name": "AWS S3 Connection",
  "auth": {
    "specName": "S3 Access Key",
    "params": {
      "s3AccessKey": "***",
      "s3SecretKey": "***"
    }
  },
  "connectionSpec": {
    "id": "ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a",
    "version": "1.0",
    "name": "Amazon S3"
  },
  "state": "enabled",
  "createdAt": 1617235200000,
  "updatedAt": 1617235200000,
  "etag": "\"ghi789\""
}
```

### Flow Specs

#### Get Flow Spec
```http
GET /flowSpecs/{id}
```

**Response:**
```json
{
  "id": "9753525b-82c7-4dce-8a9b-5ccfce2b9876",
  "name": "Cloud Storage to Data Lake",
  "version": "1.0",
  "attributes": {
    "category": "Cloud Storage"
  },
  "createdAt": 1617235200000,
  "updatedAt": 1617235200000
}
```

## Common HTTP Status Codes

- `200 OK`: Successful GET request
- `201 Created`: Successful POST request
- `204 No Content`: Successful DELETE request
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Invalid or expired access token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

## Error Response Format

```json
{
  "type": "http://ns.adobe.com/aep/errors/FLOW-400",
  "status": 400,
  "title": "Bad Request",
  "detail": "Invalid flow specification ID",
  "report": {
    "flowId": "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
  }
}
```

## Rate Limiting

- Flow Service follows standard AEP rate limits
- Typical limit: 50 requests per minute per organization
- 429 errors include `Retry-After` header (seconds)
- Exponential backoff recommended for retries

## Pagination

List endpoints return paginated results:
- Use `limit` parameter (max: 100)
- Use `start` parameter from `_page.next` for next page
- Use `_links.next.href` for convenience

## Query String Filtering

Use `property` parameter for filtering:
- `property=state==enabled` - Filter by state
- `property=flowSpec.id==abc123` - Filter by flow spec
- `property=createdAt>1617235200000` - Filter by timestamp
- Multiple filters: `property=state==enabled&property=flowSpec.id==abc123`

**Supported Operators:**
- `==` - Equals
- `!=` - Not equals
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal

## Best Practices

1. **Always include etag in PATCH requests** to prevent concurrent modification conflicts
2. **Use property filters** to reduce payload size and improve performance
3. **Implement exponential backoff** for 429/503 errors
4. **Cache connection IDs** to reduce redundant API calls
5. **Monitor run status** periodically for long-running dataflows
6. **Use orderby=createdAt:desc** to get most recent items first
7. **Set appropriate limit** based on your use case (smaller = faster response)

## Implementation Notes

- All timestamps are Unix milliseconds (not seconds)
- Connection credentials are masked in responses (show `***`)
- `etag` values are required for update operations
- Dataflow state: `enabled` or `disabled`
- Run status: `pending`, `inProgress`, `success`, `failed`, `cancelled`
- Source/target connection IDs are arrays (support multiple connections)

## Reference

- [Flow Service API Reference](https://developer.adobe.com/experience-platform-apis/references/flow-service/)
- [Sources Documentation](https://experienceleague.adobe.com/en/docs/experience-platform/sources/home)
- [Monitoring Dataflows](https://experienceleague.adobe.com/docs/experience-platform/dataflows/ui/monitor-sources.html)
