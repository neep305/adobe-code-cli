# Schema Registry Implementation Summary

## Completed Implementation (v0.3.0)

### 1. Core HTTP Methods ✅
- **Added PATCH method** to `AEPClient` for JSON Patch operations (RFC 6902)
- Supports `Content-Type: application/json-patch+json` header

### 2. Schema Management Improvements ✅

#### Fixed Issues:
- **`--class-id` option now works correctly**
  - Added `class_id` parameter to `XDMSchemaAnalyzer.from_sample_data()`
  - Dynamically sets `meta_class` and `allOf` based on provided class
  - Properly passes from CLI to schema generation
  - Removed duplicate parameter from `create_schema()` call

- **URL Encoding**
  - Added `urllib.parse.quote()` for schema IDs in URLs
  - Handles special characters like `https://` in identifiers
  - Applied to `get_schema()`, `update_schema()`, `delete_schema()`

- **Tenant ID handling**
  - Config loaded even when not uploading (needed for tenant_id)
  - Properly namespaces custom fields with tenant prefix

### 3. Field Groups API ✅
New methods in `XDMSchemaRegistry`:
- `list_field_groups(container_id, limit)` - List field groups
- `get_field_group(field_group_id, container_id)` - Get specific field group
- `create_field_group(field_group)` - Create custom field group
- `update_field_group(field_group_id, field_group)` - Full replacement update
- `patch_field_group(field_group_id, patch_operations)` - JSON Patch update
- `delete_field_group(field_group_id)` - Delete field group

### 4. Descriptors API ✅
New methods in `XDMSchemaRegistry`:
- `list_descriptors(container_id, limit)` - List descriptors
- `get_descriptor(descriptor_id, container_id)` - Get specific descriptor
- `create_descriptor(descriptor)` - Create identity/relationship descriptors
- `update_descriptor(descriptor_id, descriptor)` - Update descriptor
- `delete_descriptor(descriptor_id)` - Delete descriptor

**Use Cases**:
- Identity descriptors for Profile enablement
- Relationship descriptors for schema connections
- Friendly name descriptors for UI display

### 5. CLI Commands ✅
Added to `adobe aep schema`:
- `list-fieldgroups [--limit 10] [--container tenant]` - List field groups
- `get-fieldgroup <ID> [--output file.json]` - Get specific field group

### 6. Test Examples ✅
Created `examples/schema-registry-demo.py`:
- Demonstrates all new APIs
- Shows identity descriptor structure
- Shows field group structure
- Ready-to-run examples

## API Coverage

### Implemented Endpoints (11/46 = 24%)
- ✅ Schemas: GET list, GET by ID, POST, PUT, DELETE
- ✅ Field Groups: GET list, GET by ID, POST, PUT, PATCH, DELETE
- ✅ Descriptors: GET list, GET by ID, POST, PUT, DELETE

### Priority Missing Endpoints
- ⚠️ Classes API (custom class creation)
- ⚠️ Data Types API (reusable types)
- ⚠️ Stats API (tenant info)
- ⚠️ Unions API (profile unions)
- ⚠️ Export/Import (portability)
- ⚠️ Sample Data generation
- ⚠️ Audit Log

## Testing Commands

```bash
# Test schema creation with class_id
adobe aep schema create \
  --name "Test Events" \
  --from-sample test-data/ecommerce/events.json \
  --class-id "https://ns.adobe.com/xdm/context/experienceevent" \
  --output test-schema.json

# List field groups
adobe aep schema list-fieldgroups --limit 10

# Get specific field group
adobe aep schema get-fieldgroup <FIELD_GROUP_ID> --output fieldgroup.json

# Run demo script
python examples/schema-registry-demo.py
```

## Next Steps (Tier 2 Priority)

1. **Classes API** - Enable custom XDM class creation
2. **Data Types API** - Reusable type definitions
3. **Enhanced Query Support** - Filtering, ordering, pagination
4. **Accept Header Logic** - Dynamic selection based on operation
5. **Stats API** - Tenant information retrieval

## Breaking Changes

None - all changes are additive and backward compatible.

## Files Modified

- `src/adobe_experience/aep/client.py` - Added PATCH method
- `src/adobe_experience/schema/xdm.py` - Added Field Groups, Descriptors APIs, URL encoding
- `src/adobe_experience/cli/schema.py` - Fixed class_id handling, added CLI commands
- `examples/schema-registry-demo.py` - New demo file

---

## Week 0 MVP Implementation & API Integration Issues (2026-01-24)

### Overview
Week 0 MVP 구현 중 발생한 API 연동 오류와 해결 과정을 기록합니다.

### 1. Anthropic API 인증 오류 ❌→✅

**문제:**
```
Error: 401 - invalid x-api-key
```

**원인:**
- `~/.adobe/ai-credentials.json`에 Anthropic API 키가 테스트 값으로 설정됨
- `"api_key": "test-anthropic-key"` (실제 키가 아님)

**해결:**
1. Default AI provider를 OpenAI로 사용하도록 수정
2. OpenAI와 Anthropic 모두 지원하도록 `AIInferenceEngine` 개선
3. Config에서 `_default` provider 설정을 우선 로드하도록 변경

### 2. Multi-Provider AI Support 추가 ✅

**변경 사항:**

**`src/adobe_experience/agent/inference.py`:**
- OpenAI SDK import 추가
- `__init__()` 메서드 개선:
  - `self.anthropic` 및 `self.openai` 클라이언트 모두 초기화
  - `self.active_client` 변수로 현재 사용 중인 provider 추적
  - Provider 우선순위: config 설정 → 첫 번째 사용 가능한 client
  - 테스트 키(`test-` prefix) 필터링
- `generate_schema_with_ai()`:
  - Anthropic과 OpenAI 모두 지원하도록 분기 처리
  - API 응답 파싱 provider별로 처리
  - 인증 오류 메시지 개선
- `_generate_validation_summary()`:
  - 양쪽 provider 지원
  - AI 실패 시 graceful fallback (None 반환)

**`src/adobe_experience/core/config.py`:**
- `model_post_init()` 로직 변경:
  - `_default` provider를 먼저 로드
  - Active provider에 맞는 모델을 선택적으로 로드
  - OpenAI 사용 시 `gpt-4o`, Anthropic 사용 시 `claude-3-5-sonnet-20241022`

**Dependencies:**
- `openai==2.15.0` 설치

### 3. Tenant Namespace 규칙 적용 ❌→✅

**문제 1: Namespace Validation Error**
```
Error: 400 - All custom fields must be prefixed with the text acssandboxgdctwo
```

**시도 1 (실패):** 
- 필드명에 직접 prefix 추가: `acssandboxgdctwo:field_name`
- 결과: 여전히 오류 발생

**문제 2: Type Merge Conflict**
```
Error: 400 - Cannot merge incompatible data types. 
The path /_acssandboxgdctwo/properties/email/type has already been defined 
in schema (id=) using a different data type. Types: string, object
```

**원인:**
- XDM Profile class에 이미 `email` 필드가 object 타입으로 정의되어 있음
- Custom 필드로 string 타입의 `email`을 추가하려고 해서 충돌

**해결 1: Custom 필드 중첩 구조**

`src/adobe_experience/schema/xdm.py` - `from_sample_data()` 수정:
```python
# Before: 평평한 구조
properties = {
    "acssandboxgdctwo:email": {...},
    "acssandboxgdctwo:age": {...}
}

# After: 중첩 구조
properties = {
    "_acssandboxgdctwo": {
        "type": "object",
        "properties": {
            "email": {...},
            "age": {...}
        }
    }
}
```

**해결 2: XDM 표준 필드 필터링**

XDM Profile class와 충돌하는 표준 필드를 custom 필드에서 제외:
```python
XDM_PROFILE_STANDARD_FIELDS = {
    "email", "emailAddress", "personalEmail",
    "firstName", "first_name", "lastName", "last_name",
    "phone", "phoneNumber", "mobilePhone",
    ...
}
```

이 필드들은 Profile class의 표준 구조에 이미 정의되어 있으므로 tenant namespace에 추가하지 않음.

**문제 3: Schema Cannot Define Custom Fields**
```
Error: 400 - A schema resource cannot define its own custom fields. 
It must be defined with an 'allOf' attribute which references a single 
class and other fieldgroups
```

**원인:**
- AEP에서는 스키마가 직접 custom 필드를 정의할 수 없음
- Field Group을 통해서만 custom 필드를 정의해야 함

**최종 해결: Field Group 자동 생성**

`src/adobe_experience/cli/schema.py` - `upload_and_validate` 수정:
1. Custom 필드가 있으면 Field Group을 먼저 생성
2. Field Group 정의:
   ```json
   {
     "$id": "https://ns.adobe.com/<tenant>/mixins/<schema_name>_custom",
     "title": "<Schema Name> Custom Fields",
     "meta:intendedToExtend": ["<class_id>"],
     "definitions": {
       "customFields": {
         "properties": {
           "_<tenant_id>": { /* custom fields here */ }
         }
       }
     },
     "allOf": [{"$ref": "#/definitions/customFields"}]
   }
   ```
3. 스키마에서 inline properties 제거
4. 스키마의 `allOf`에 Field Group 참조 추가

### 4. 최종 작동 흐름 ✅

**Step 1: Schema Generation**
- AI (OpenAI/GPT-4o)가 샘플 데이터 분석
- XDM 표준 필드 필터링 (email, first_name, last_name 제외)
- Custom 필드만 `_<tenant_id>` 객체로 그룹화

**Step 2: Upload to AEP**
- Field Group 자동 생성: `<Schema Name> Custom Fields`
- Field Group에 custom 필드 정의
- 스키마 생성 시 Field Group 참조

**Step 3: Validation**
- 업로드된 스키마 구조로 실제 데이터 검증
- Type mismatch, format errors, extra fields 탐지

**Step 4: Report**
- Rich UI로 검증 결과 표시
- AI 분석 요약 제공
- Severity별 이슈 분류 (CRITICAL/WARNING/INFO)

### 성공 사례

**명령어:**
```bash
adobe aep schema upload-and-validate \
  --name "Customer Schema v2" \
  --from-sample examples/validation-demo/sample_customers.json \
  --validate-data examples/validation-demo/actual_customers.json \
  --use-ai
```

**결과:**
- ✅ Field Group 생성: `Customer Schema v2 Custom Fields`
- ✅ Schema 업로드: `https://ns.adobe.com/acssandboxgdctwo/schemas/customer_schema_v2`
- ✅ 3개 레코드 검증 완료
- ✅ AI 분석 리포트 생성
- ✅ Custom 필드: `customer_id`, `age`, `account_created`
- ✅ 제외된 표준 필드: `email`, `first_name`, `last_name`

### 핵심 교훈

1. **AEP Schema 구조 이해**
   - Custom 필드는 반드시 `_<tenant_id>` 객체로 중첩
   - Field Group을 통해서만 custom 필드 정의 가능
   - XDM 표준 필드는 base class에서 상속받음

2. **Multi-Provider AI 지원**
   - Provider별 API 응답 구조 차이 고려
   - Fallback 메커니즘 필수
   - Config에서 provider와 model을 함께 관리

3. **에러 메시지 개선**
   - API 오류 시 사용자에게 해결 방법 제시
   - Authentication 실패 시 `adobe ai set-key` 명령 안내
   - 구체적인 오류 컨텍스트 제공

### 파일 변경 이력

**수정된 파일:**
- `src/adobe_experience/agent/inference.py` - Multi-provider 지원, validation 로직
- `src/adobe_experience/core/config.py` - Provider별 모델 로딩
- `src/adobe_experience/schema/xdm.py` - Tenant namespace 구조, 표준 필드 필터링
- `src/adobe_experience/cli/schema.py` - Field Group 자동 생성

**추가된 파일:**
- `examples/validation-demo/sample_customers.json` - 샘플 데이터
- `examples/validation-demo/actual_customers.json` - 검증용 데이터
- `examples/validation-demo/README.md` - 사용 가이드
- `examples/validation-demo/TROUBLESHOOTING.md` - 문제 해결 가이드
