# AEP XDM 스키마 아키텍처 설계 가이드

> 이 문서는 Adobe Experience Platform(AEP) 프로젝트에서 XDM 스키마를 설계할 때 반드시 사전에 검토해야 할 전략적 의사결정 사항을 정리한 기술 참조 문서입니다.
> 코드베이스의 실제 구현(`schema/models.py`, `schema/xdm.py`, `agent/inference.py`)과 연계하여 개발 근거로 활용합니다.

---

## 목차

1. [개요 — 왜 사전 스키마 설계가 중요한가](#1-개요)
2. [XDM 클래스 선택 전략](#2-xdm-클래스-선택-전략)
3. [Identity 전략](#3-identity-전략)
4. [Profile 통합 전략 (Merge Policy)](#4-profile-통합-전략-merge-policy)
5. [테넌트 네임스페이스 규칙](#5-테넌트-네임스페이스-규칙)
6. [Field Group 아키텍처](#6-field-group-아키텍처)
7. [데이터 모델링 패턴](#7-데이터-모델링-패턴)
8. [데이터 타입 & 포맷 매핑](#8-데이터-타입--포맷-매핑)
9. [유스케이스별 설계 가이드](#9-유스케이스별-설계-가이드)
10. [사전 검증 및 품질 관리](#10-사전-검증-및-품질-관리)
11. [구현 체크리스트](#11-구현-체크리스트)

---

## 1. 개요

### 1.1 스키마 설계가 프로젝트 성패를 결정하는 이유

AEP에서 XDM 스키마는 **한번 프로덕션에 배포되면 필드 삭제나 타입 변경이 불가능**합니다.
기존 데이터가 이미 그 구조에 맞춰 수집되기 때문에 스키마 수정은 파괴적 변경(breaking change)을 야기합니다.
따라서 데이터 수집 파이프라인을 구축하기 전에 스키마 전략을 수립하는 것이 필수입니다.

**사전 설계 없이 진행할 때 발생하는 문제:**

| 문제 | 원인 | 결과 |
|------|------|------|
| Profile Fragmentation | Primary Identity 오설계 | 동일 고객이 여러 Profile로 분열 |
| Identity Graph 오염 | 공유 식별자(예: 공용 이메일)를 Primary로 설정 | 수백만 프로파일이 하나로 합쳐지는 "identity collapse" |
| 데이터 손실 | 필드 타입 불일치 | 배치 ingestion 실패, 데이터 누락 |
| 재작업 비용 | 스키마 구조 변경 불가 | 스키마 재생성 + 전체 데이터 재수집 |
| 세분화 불가 | ExperienceEvent에 상태 데이터 혼재 | Real-Time CDP 세그먼트 정확도 저하 |

### 1.2 설계 단계별 의사결정 순서

```
1. 고객사 데이터 도메인 분석 (Entity 파악)
        ↓
2. XDM 클래스 선택 (Profile / ExperienceEvent / Custom)
        ↓
3. Identity 전략 수립 (Primary / Secondary / Graph 전략)
        ↓
4. Profile Merge Policy 결정
        ↓
5. Tenant Namespace & Field Group 설계
        ↓
6. 데이터 모델링 (ERD → XDM 변환)
        ↓
7. 타입/포맷 매핑 & 전처리 정의
        ↓
8. 사전 검증 후 스키마 업로드
```

---

## 2. XDM 클래스 선택 전략

### 2.1 핵심 판단 원칙: 상태(State) vs 이벤트(Event)

| 구분 | XDM Individual Profile | XDM ExperienceEvent |
|------|------------------------|---------------------|
| **의미** | 고객이 지금 어떤 사람인가 | 고객이 특정 시점에 무엇을 했는가 |
| **데이터 성격** | 반영구적 속성 (semi-static) | 시계열 이벤트 (time-series) |
| **예시** | 이름, 이메일, 구독 등급, 주소 | 페이지 조회, 구매, 클릭, 로그인 |
| **타임스탬프** | 불필요 | **필수** (`timestamp` 필드) |
| **Primary Identity** | **필수** (1개) | 선택 (Profile 스티칭용) |
| **Class URI** | `https://ns.adobe.com/xdm/context/profile` | `https://ns.adobe.com/xdm/context/experienceevent` |

### 2.2 결정 트리

```
데이터가 시간에 따라 변하는 "행동/사건"인가?
├── YES → ExperienceEvent
│   ├── timestamp 필드 존재 확인 (필수)
│   └── event_id 필드 추가 권장
└── NO → 고객/계정/상품의 "속성/상태"인가?
    ├── 사람(Person/Customer) → XDM Individual Profile
    ├── 계정/조직(B2B) → XDM Business Account Profile
    ├── 상품 → Custom Class (Product Catalog)
    ├── 자산(Asset) → Custom Class
    └── 금융 계좌 → XDM FSI Account Class
```

### 2.3 클래스별 URI 및 필수 구성 요소

```python
# schema/models.py 의 XDM class URI 참조
XDM_CLASSES = {
    "profile":          "https://ns.adobe.com/xdm/context/profile",
    "experienceevent":  "https://ns.adobe.com/xdm/context/experienceevent",
    "product":          "https://ns.adobe.com/xdm/context/product",
    "fsi_account":      "https://ns.adobe.com/xdm/classes/fsi/account",
    "b2b_account":      "https://ns.adobe.com/xdm/context/account",
}
```

| Class | 필수 필드 | Primary Identity 요구 |
|-------|-----------|----------------------|
| Profile | (없음, 하지만 identity 필수) | 필수 |
| ExperienceEvent | `timestamp` (date-time), `_id` | 선택 권장 |
| Custom | 없음 | 권장 |

### 2.4 혼동하기 쉬운 케이스

| 데이터 | 잘못된 선택 | 올바른 선택 | 이유 |
|--------|-------------|-------------|------|
| 주문 내역 | Profile 필드 | ExperienceEvent | 주문은 시점이 있는 사건 |
| 구독 등급 (현재) | ExperienceEvent | Profile 필드 | 현재 상태값 |
| 이메일 오픈 이벤트 | Profile 필드 | ExperienceEvent | 시점 기반 행동 |
| 마지막 구매 날짜 | ExperienceEvent | Profile 필드 (`lastPurchaseDate`) | 파생된 상태값 |

---

## 3. Identity 전략

### 3.1 Identity Namespace 종류 및 특성

`schema/models.py` → `XDMIdentityNamespace` enum 기준:

| Namespace | 타입 | 지속성 | 용도 | Primary 적합성 |
|-----------|------|--------|------|----------------|
| `Email` | People | 영구적 | B2C 주요 식별자 | B2C에서 최적 |
| `Phone` | People | 영구적 | 보조 식별자, SMS | 보조로만 사용 |
| `ECID` | Cookie | 세션~기기 | Adobe Web SDK 자동 생성 | 익명 이벤트에만 |
| `CRM_ID` | Cross-Device | 영구적 | 내부 CRM 고객 ID | B2B/엔터프라이즈 최적 |
| `Cookie_ID` | Cookie | 단기 | 브라우저 익명 추적 | 절대 Primary 사용 금지 |
| `Mobile_ID` | Device | 기기 수명 | iOS(IDFA) / Android(GAID) | 앱 전용 보조 식별자 |

### 3.2 Primary Identity 선정 기준

**규칙: 스키마 당 Primary Identity는 반드시 1개여야 합니다.**

```python
# schema/models.py → XDMIdentity 모델
class XDMIdentity(BaseModel):
    namespace: str       # Identity namespace 이름
    is_primary: bool     # True인 필드는 스키마 전체에서 1개만
```

**시나리오별 권장 Primary Identity:**

```
B2C (개인 소비자)
├── 이메일이 항상 수집되는 경우 → Email (가장 높은 매칭률)
├── 이메일 없이 앱 전용인 경우 → Mobile_ID (IDFA/GAID)
└── 익명 우선 시나리오 → ECID (인증 후 Email로 전환)

B2B (기업/계정 기반)
├── CRM 시스템 존재 → CRM_ID (내부 고객 ID)
├── 계정 기반 → Account ID (커스텀 네임스페이스 생성)
└── 연락처 기반 → Email (Contact 레벨)

주의: 절대 Primary로 사용하면 안 되는 것
├── Cookie_ID → 브라우저 세션 종료 시 소멸
├── IP 주소 → 공유 IP로 인한 identity collapse 위험
└── 공용 이메일(info@, support@) → 수백만 프로파일 병합 위험
```

### 3.3 Identity Graph 전략 4가지

`agent/inference.py` → `AIIdentityStrategy.identity_graph_strategy` 참조:

**① Email-Based (B2C 기본 전략)**
```
이메일 (Primary) ←→ ECID (익명 세션)
                ←→ Phone (보조)
장점: 높은 매칭률, 크로스 디바이스 연결
단점: 이메일 미수집 시 단절
```

**② CRM-Based (B2B / 엔터프라이즈)**
```
CRM_ID (Primary) ←→ Email (보조)
                 ←→ Phone (보조)
                 ←→ ECID (웹 익명 추적)
장점: 내부 시스템과 완벽 동기화
단점: CRM 도입 전 데이터 연결 불가
```

**③ Device-Graph (모바일/디바이스 중심)**
```
ECID (기본) ←→ Mobile_ID (앱)
            ←→ Cookie_ID (웹)
인증 후: Email / CRM_ID 추가 연결
장점: 인증 전 행동 데이터 보존
단점: 디바이스 교체 시 연결 단절
```

**④ Hybrid (복합 전략, 권장)**
```
알려진 고객:  Email/CRM_ID (Primary) + Phone + ECID
익명 고객:    ECID (Primary) + Cookie_ID
인증 이벤트:  Email ↔ ECID 스티칭 자동 처리 (Identity Graph)
장점: 모든 시나리오 커버
단점: 설계 복잡도 증가
```

### 3.4 Identity Descriptor API 등록

스키마에 Identity를 등록하려면 Schema Registry에 Descriptor를 별도로 POST해야 합니다:

```python
# aep/client.py → AEPClient.post() 사용
descriptor_payload = {
    "@type": "xdm:descriptorIdentity",
    "xdm:sourceSchema": schema_id,          # 스키마 $id URI
    "xdm:sourceVersion": 1,
    "xdm:sourceProperty": f"/_{tenant_id}/email_address",  # 필드 경로
    "xdm:namespace": "Email",               # Namespace 이름
    "xdm:property": "xdm:code",
    "xdm:isPrimary": True,                  # Primary 여부
}
await client.post(
    "/data/foundation/schemaregistry/tenant/descriptors",
    json=descriptor_payload
)
```

---

## 4. Profile 통합 전략 (Merge Policy)

### 4.1 Merge Policy란

여러 데이터셋에서 동일 고객의 데이터가 들어올 때, 충돌하는 속성값을 어떻게 합칠지 결정하는 규칙입니다.
스키마 자체에 저장되는 것이 아니라 AEP Real-Time Customer Profile 설정으로 관리되지만,
**스키마 설계 단계에서 어떤 Merge Policy를 사용할지 미리 결정해야** 데이터 모델이 이를 지원할 수 있습니다.

### 4.2 Merge Policy 유형별 비교

| 유형 | 동작 방식 | 최적 사용 시나리오 |
|------|-----------|-------------------|
| **Timestamp-based** | 가장 최근 업데이트 값 우선 | 실시간 이벤트 기반 속성 업데이트 |
| **Data Source Priority** | 순위가 높은 데이터 소스 우선 (예: CRM > Web) | 마스터 데이터 존재, B2B |
| **Last-Write-Wins** | 마지막 쓰기 타임스탬프 기준 전역 적용 | 단일 소스, 간단한 구조 |
| **Data Source Specific** | 필드별로 다른 소스 우선 규칙 | 복잡한 멀티소스 환경 |

### 4.3 시나리오별 권장 정책

```
B2C 이커머스
→ Timestamp-based: 웹/앱 행동이 실시간으로 업데이트되므로 최신값 우선

B2B 엔터프라이즈
→ Data Source Priority: CRM > Marketing Automation > Web
  (CRM 데이터가 가장 신뢰할 수 있는 마스터 소스)

미디어/콘텐츠 (익명 다수)
→ Timestamp-based + ECID 기반: 인증 이전 익명 데이터 보존 우선

금융/보험
→ Data Source Specific: 계약 데이터는 Core Banking 우선,
  행동 데이터는 Timestamp-based
```

### 4.4 데이터셋 활성화 플래그

스키마가 Profile/Identity와 연동되려면 데이터셋 생성 시 플래그를 설정해야 합니다:

```python
# catalog/client.py → CatalogServiceClient.create_dataset()
dataset_id = await catalog.create_dataset(
    name="Customer Profile Dataset",
    schema_id=schema_id,
    enable_profile=True,    # Real-Time Customer Profile 활성화
                            # tags: {"unifiedProfile": ["enabled:true"]}
    enable_identity=True,   # Identity Service 연동
                            # tags: {"unifiedIdentity": ["enabled:true"]}
)
```

**활성화 조건 체크리스트:**
- [ ] 스키마에 Primary Identity가 설정되어 있는가
- [ ] Identity Descriptor가 Schema Registry에 등록되어 있는가
- [ ] 데이터셋의 `enable_profile=True` 설정이 되어 있는가
- [ ] 배치 ingestion이 `SUCCESS` 상태로 완료되었는가

---

## 5. 테넌트 네임스페이스 규칙

### 5.1 원칙: 표준 vs 커스텀 필드 분리

AEP Schema Registry는 **표준 XDM 필드**와 **커스텀 필드**를 엄격히 구분합니다.
커스텀 필드를 root 레벨에 배치하면 Schema Registry 업로드 시 **400 오류**가 발생합니다.

```
Root 레벨 (표준 XDM 필드만 허용)
├── personalEmail.address
├── person.name.firstName
├── homePhone.number
└── homeAddress.street1

_{TENANT_ID} 네임스페이스 (커스텀 필드 전용)
├── _{myorg}.loyaltyTier
├── _{myorg}.crmSegment
└── _{myorg}.lastPurchaseDate
```

### 5.2 표준 XDM 필드 목록 (root 레벨 허용)

`schema/xdm.py` → `XDM_PROFILE_STANDARD_FIELDS` 참조:

```python
XDM_PROFILE_STANDARD_FIELDS = {
    "email", "emailAddress", "personalEmail",
    "firstName", "lastName", "phone", "mobilePhone",
    "birthDate", "gender",
    "homeAddress", "workAddress", "mailingAddress",
    "person", "personName",
}
```

### 5.3 커스텀 필드 구조 예시

```json
{
  "_{tenant_id}": {
    "type": "object",
    "title": "Custom Fields",
    "properties": {
      "loyaltyTier": {
        "type": "string",
        "title": "Loyalty Tier",
        "enum": ["bronze", "silver", "gold", "platinum"]
      },
      "crmCustomerId": {
        "type": "string",
        "title": "CRM Customer ID",
        "meta:descriptors": [{"@type": "xdm:descriptorIdentity"}]
      }
    }
  }
}
```

### 5.4 Field Group vs 직접 필드 배치 결정 기준

| 상황 | 권장 방식 |
|------|-----------|
| 여러 스키마에서 재사용할 필드 그룹 | Field Group 생성 후 allOf로 참조 |
| 단일 스키마 전용 커스텀 필드 | 스키마 직접 배치 (`_{tenant_id}` 하위) |
| Adobe 표준 필드 그룹과 유사한 구조 | 표준 Field Group 사용 (커스텀 생성 불필요) |
| 도메인별 독립적 속성 집합 | 도메인 단위 Field Group 분리 |

### 5.5 버저닝 전략

- 스키마 버전은 `meta:version`으로 관리 (기본값: `1.0`)
- **필드 추가는 가능, 필드 삭제/타입 변경은 불가**
- 기존 필드 변경 시 → 새 Field Group 버전 생성 후 스키마 패치
- 하위 호환성 유지: 기존 필드는 유지하고 새 필드 추가만 허용

```python
# 스키마에 새 Field Group 추가 (PATCH)
await client.patch(
    f"/data/foundation/schemaregistry/tenant/schemas/{encoded_schema_id}",
    json=[{"op": "add", "path": "/allOf/-", "value": {"$ref": new_fieldgroup_uri}}],
    headers={"Content-Type": "application/json-patch+json"}
)
```

---

## 6. Field Group 아키텍처

### 6.1 Adobe 표준 Field Group (우선 사용)

커스텀 Field Group을 만들기 전에 Adobe 표준을 먼저 검토합니다:

| Field Group | 용도 | 주요 필드 |
|-------------|------|-----------|
| Personal Contact Details | 연락처 | email, phone, address |
| Demographic Details | 인구통계 | birthDate, gender, nationality |
| Loyalty Details | 로열티 프로그램 | tier, points, joinDate |
| Commerce Details | 커머스 트랜잭션 | order, payment, fulfillment |
| Web Details | 웹 행동 | webPageDetails, webInteraction |
| Device Details | 디바이스 정보 | device, environment |
| Campaign Member Details | 마케팅 캠페인 | campaignMemberId, isDeleted |

### 6.2 커스텀 Field Group 설계 원칙

```
1. 도메인 단위 분리: 로열티, 구매 이력, 행동 데이터는 각각 별도 Field Group
2. 재사용 가능하게: 동일한 필드 구조가 2개 이상 스키마에 필요하면 Field Group화
3. Adobe 표준 우선: 표준 Field Group이 있으면 커스텀 생성 불필요
4. 이름 규칙: {tenant_id}/fieldgroups/{domain}_{purpose}_fieldgroup
```

### 6.3 Field Group 구조 패턴 (allOf 조합)

```json
{
  "$id": "https://ns.adobe.com/{tenant_id}/fieldgroups/loyalty_details_fieldgroup",
  "$schema": "http://json-schema.org/draft-06/schema#",
  "title": "Loyalty Program Details",
  "meta:intendedToExtend": [
    "https://ns.adobe.com/xdm/context/profile"
  ],
  "definitions": {
    "_{tenant_id}": {
      "type": "object",
      "properties": {
        "loyaltyTier": {"type": "string", "title": "Loyalty Tier"},
        "loyaltyPoints": {"type": "integer", "title": "Points Balance"},
        "memberSince": {"type": "string", "format": "date-time"}
      }
    }
  },
  "allOf": [
    {"$ref": "http://json-schema.org/draft-06/schema#"},
    {"$ref": "#/definitions/_{tenant_id}"}
  ]
}
```

### 6.4 meta:intendedToExtend 규칙

| Field Group 용도 | meta:intendedToExtend 값 |
|-----------------|--------------------------|
| Profile 전용 | `["https://ns.adobe.com/xdm/context/profile"]` |
| ExperienceEvent 전용 | `["https://ns.adobe.com/xdm/context/experienceevent"]` |
| 양쪽 모두 | 두 URI 모두 배열에 포함 |

---

## 7. 데이터 모델링 패턴

### 7.1 ERD → XDM 변환 원칙

`schema/knowledge/ERD_STANDARD.md` 참조. ERD의 각 엔티티를 XDM으로 변환하는 기본 규칙:

| ERD 관계 | XDM 변환 패턴 |
|----------|---------------|
| 1:1 (Person ↔ Address) | Profile 내 중첩 object |
| 1:N (Customer → Orders) | ExperienceEvent에 customerId FK 포함 |
| N:M (Product ↔ Category) | 각각 별도 스키마, 이벤트에서 양쪽 ID 참조 |
| 계층형 (Category tree) | 중첩 object 또는 배열로 경로 표현 |

### 7.2 정규화 vs 비정규화 판단 기준

```
비정규화 권장 (XDM 기본 접근):
→ 실시간 조회 성능이 중요한 경우
→ Profile 속성: 현재 상태값을 하나의 레코드에 집약
→ ExperienceEvent: 이벤트 발생 시점의 스냅샷 데이터 포함

정규화 권장:
→ 상품 정보처럼 자주 변경되는 참조 데이터
→ 별도 Custom Class 스키마로 분리, ID로 참조
→ 예: Product Catalog 스키마 + 이벤트에 productId만 포함
```

### 7.3 중첩 객체 vs Flat 구조

| 상황 | 권장 구조 |
|------|-----------|
| 주소 (street, city, country) | 중첩 object (`homeAddress.city`) |
| 단순 속성 5개 이하 | Flat 구조 |
| 반복 구조 (여러 주소, 여러 전화번호) | 배열 (`mobilePhone[]`) |
| 이벤트 내 구매 상품 목록 | 배열 of objects (`items[{productId, qty, price}]`) |

### 7.4 배열 필드 사용 시 주의사항

```python
# schema/models.py → XDMField items 설정
array_field = XDMField(
    title="Purchased Items",
    type=XDMDataType.ARRAY,
    items={
        "type": "object",
        "properties": {
            "productId": {"type": "string"},
            "quantity": {"type": "integer"},
            "price": {"type": "number"},
        }
    }
)
```

**주의사항:**
- 배열 내 항목 타입은 일관되게 유지 (혼합 타입 금지)
- 배열 내 identity 필드 설정 불가 (root 레벨 필드만 identity 가능)
- 배열 크기 제한 없으나 대용량 배열은 ingestion 성능 저하 유발

---

## 8. 데이터 타입 & 포맷 매핑

### 8.1 XDMDataType / XDMFieldFormat 전체 목록

`schema/models.py` → `XDMDataType`, `XDMFieldFormat` enum:

```python
class XDMDataType(str, Enum):
    STRING    = "string"
    NUMBER    = "number"     # float
    INTEGER   = "integer"
    BOOLEAN   = "boolean"
    OBJECT    = "object"
    ARRAY     = "array"
    DATE      = "date"       # YYYY-MM-DD
    DATE_TIME = "date-time"  # ISO 8601 with time

class XDMFieldFormat(str, Enum):
    EMAIL     = "email"
    URI       = "uri"
    DATE      = "date"
    DATE_TIME = "date-time"
    UUID      = "uuid"
```

### 8.2 자동 감지 패턴 (XDMSchemaAnalyzer 기반)

`schema/xdm.py` → `XDMSchemaAnalyzer` 자동 감지 로직:

| 입력값 패턴 | 감지 타입 | 감지 포맷 |
|-------------|-----------|-----------|
| 값에 `@` 포함 또는 필드명 `email*` | string | email |
| 필드명 `url`, `uri`, 값이 `http://`로 시작 | string | uri |
| ISO 8601 (`2024-01-01T00:00:00Z`) | string | date-time |
| 날짜만 (`2024-01-01`) | string | date |
| 필드명 `price`, `amount`, `cost`, `revenue` | number | — |
| 필드명 `phone`, `tel`, `mobile` | string | — |
| 값이 `0/1`, `yes/no`, `true/false` | boolean | — |
| 10자리 정수 (epoch seconds) | string | date-time |
| 13자리 정수 (epoch ms) | string | date-time |
| 중첩 dict | object | — |
| 리스트 | array | — |

### 8.3 엣지 케이스 처리

**Epoch Timestamp 변환 (전처리 필수):**
```python
# ingestion 전 pandas로 변환
import pandas as pd
df['created_at'] = pd.to_datetime(df['created_at'], unit='s')  # epoch seconds
df['event_time'] = pd.to_datetime(df['event_time'], unit='ms') # epoch ms
df['created_at'] = df['created_at'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
```

**Phone Number 정규화 (E.164 형식 필수):**
```python
# 국제 형식으로 정규화
# +82-10-1234-5678 → +821012345678
import phonenumbers
parsed = phonenumbers.parse(raw_phone, "KR")
normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
```

**Boolean Variant 처리:**
```
"yes"/"no" → True/False
"1"/"0"    → True/False
"on"/"off" → True/False
"enabled"/"disabled" → True/False
```

**Currency 필드:**
```
필드명: price, amount, cost, revenue, total → XDMDataType.NUMBER
통화 코드는 별도 string 필드로 분리: {"price": 9.99, "currency": "USD"}
```

---

## 9. 유스케이스별 설계 가이드

### 9.1 B2C 이커머스

```
스키마 구성:
├── Customer Profile (XDM Individual Profile)
│   ├── Primary Identity: Email (namespace: Email)
│   ├── Secondary: Phone, ECID
│   ├── Field Groups: Personal Contact, Demographic, Loyalty Details
│   └── Custom: _{tenant}.loyaltyTier, _{tenant}.preferredCategory
│
├── Purchase Event (XDM ExperienceEvent)
│   ├── Identity: Email (보조, Profile 스티칭용)
│   ├── Timestamp: 필수
│   ├── Field Groups: Commerce Details, Product List Items
│   └── Custom: _{tenant}.orderId, _{tenant}.discountCode
│
└── Product Catalog (Custom Class)
    ├── Primary Identity: SKU (CRM_ID 네임스페이스 또는 커스텀)
    ├── Field Groups: Product Catalog Details
    └── Custom: _{tenant}.brand, _{tenant}.category

Identity Graph 전략: email-based
Merge Policy: Timestamp-based
```

### 9.2 B2B 엔터프라이즈

```
스키마 구성:
├── Business Account (XDM Business Account Profile)
│   ├── Primary Identity: accountId (CRM_ID)
│   └── Custom: _{tenant}.industry, _{tenant}.annualRevenue
│
├── Contact Profile (XDM Individual Profile)
│   ├── Primary Identity: CRM_ID (Contact ID)
│   ├── Secondary: Email
│   └── Custom: _{tenant}.accountId (FK to Account)
│
└── Opportunity Event (XDM ExperienceEvent)
    ├── Identity: CRM_ID
    ├── Timestamp: 필수
    └── Custom: _{tenant}.opportunityId, _{tenant}.stage

Identity Graph 전략: crm-based
Merge Policy: Data Source Priority (CRM > Marketing Automation)
```

### 9.3 미디어/콘텐츠 (익명 → 인증 스티칭)

```
익명 브라우징 단계:
└── Page View Event (ExperienceEvent)
    ├── Primary Identity: ECID (자동 생성)
    └── Custom: _{tenant}.contentId, _{tenant}.sessionId

인증 후 단계:
└── Authenticated Profile
    ├── Primary Identity: Email
    ├── Secondary: ECID (이전 익명 행동 연결)
    └── Identity Graph가 자동으로 ECID ↔ Email 스티칭

핵심: 인증 이벤트 시 동일 레코드에 Email + ECID 모두 포함해야 Graph 연결됨
Identity Graph 전략: device-graph → hybrid 전환
```

### 9.4 금융/보험

```
스키마 구성:
├── Customer Profile (XDM Individual Profile)
│   ├── Primary Identity: CRM_ID
│   ├── Secondary: Email, Phone
│   └── Custom: _{tenant}.riskScore, _{tenant}.kycStatus
│
└── Financial Account (XDM FSI Account Class)
    ├── URI: https://ns.adobe.com/xdm/classes/fsi/account
    ├── Primary Identity: Account Number (커스텀 네임스페이스)
    └── Custom: _{tenant}.productType, _{tenant}.openDate

주의: 금융 데이터는 PII 규정 준수 필수
- 민감 필드에 `meta:isPII: true` 레이블 설정
- GDPR/CCPA 대응을 위한 데이터 거버넌스 레이블 적용
Identity Graph 전략: crm-based
Merge Policy: Data Source Priority (Core Banking 최우선)
```

---

## 10. 사전 검증 및 품질 관리

### 10.1 Pre-ingest Validation 체크리스트

`agent/inference.py` → `AIInferenceEngine.validate_schema_against_data()` 활용:

```python
from adobe_experience.agent.inference import AIInferenceEngine

engine = AIInferenceEngine()
report = await engine.validate_schema_against_data(schema, data_rows)

# 심각도별 처리
for issue in report.critical_issues:
    # ingestion 실패 확정 → 반드시 해결 후 진행
    print(f"CRITICAL: {issue.message}")

for issue in report.warning_issues:
    # 데이터 손실 가능 → 해결 권장
    print(f"WARNING: {issue.message}")

for issue in report.info_issues:
    # 최적화 제안 → 선택적 대응
    print(f"INFO: {issue.message}")
```

**자주 발생하는 CRITICAL 이슈:**

| 이슈 | 원인 | 해결 방법 |
|------|------|-----------|
| 타입 불일치 | 스키마는 `integer`, 데이터는 `"123"` (string) | 전처리에서 타입 변환 |
| 필수 필드 누락 | `required` 필드에 null/missing 값 | 기본값 설정 또는 스키마에서 required 제거 |
| 잘못된 이메일 포맷 | `format: email`인데 유효하지 않은 이메일 | 전처리에서 이메일 검증 |
| 날짜 포맷 오류 | `date-time`인데 `YYYY/MM/DD` 형식 | ISO 8601로 변환 |

### 10.2 배치 실패 진단

`catalog/client.py` → `CatalogServiceClient.get_batch()`:

```python
from adobe_experience.catalog.client import CatalogServiceClient

async with AEPClient(config) as aep:
    catalog = CatalogServiceClient(aep)
    batch = await catalog.get_batch(batch_id)

    print(f"Status: {batch.status}")  # BatchStatus enum
    if batch.status == BatchStatus.FAILED:
        print(f"Errors: {batch.errors}")
        # errors dict에 필드 레벨 실패 원인 포함
```

**BatchStatus 흐름:**
```
loading → staged → processing → success
                             → failed   (errors dict 확인)
                             → aborted  (수동 중단)
                             → retrying (자동 재시도 중)
```

### 10.3 스키마 변경 없이 필드 추가하는 안전한 방법

```python
# 1. 새 Field Group 생성
new_fg_id = await registry.create_field_group(new_field_group)

# 2. 기존 스키마에 Field Group 추가 (PATCH)
#    → 기존 데이터는 영향 없음, 신규 필드만 추가
await client.patch(
    f"/data/foundation/schemaregistry/tenant/schemas/{encoded_id}",
    json=[{"op": "add", "path": "/allOf/-", "value": {"$ref": new_fg_uri}}],
    headers={"Content-Type": "application/json-patch+json"}
)

# 3. 기존 데이터: 새 필드 없음 (null로 처리됨)
# 4. 신규 데이터: 새 필드 포함하여 ingestion
```

---

## 11. 구현 체크리스트

### 11.1 스키마 설계 단계별 체크리스트

**[ ] Phase 1: 데이터 도메인 분석**
- [ ] 고객사 데이터 엔티티 목록 파악 (ERD 작성)
- [ ] 각 엔티티의 성격 파악 (상태 데이터 vs 이벤트 데이터)
- [ ] 데이터 소스별 수집 주기 및 볼륨 파악
- [ ] PII/민감 데이터 필드 식별

**[ ] Phase 2: XDM 클래스 선택**
- [ ] Profile / ExperienceEvent / Custom 분류 완료
- [ ] 각 스키마의 class URI 결정
- [ ] ExperienceEvent 스키마에 timestamp 필드 포함 확인

**[ ] Phase 3: Identity 전략**
- [ ] Primary Identity 필드 및 Namespace 결정
- [ ] Secondary Identity 목록 결정
- [ ] Identity Graph 전략 선택 (email/crm/device/hybrid)
- [ ] 공유 식별자 사용 여부 검토 (identity collapse 위험)

**[ ] Phase 4: Merge Policy**
- [ ] 시나리오에 맞는 Merge Policy 유형 선택
- [ ] 데이터 소스 우선순위 정의 (Data Source Priority 선택 시)

**[ ] Phase 5: 테넌트 네임스페이스 & Field Group**
- [ ] 표준 XDM 필드와 커스텀 필드 분리
- [ ] 재사용 가능한 Field Group 식별
- [ ] Field Group ID 네이밍 규칙 결정

**[ ] Phase 6: 데이터 타입 & 전처리**
- [ ] 모든 필드의 XDMDataType / XDMFieldFormat 결정
- [ ] epoch timestamp → ISO 8601 변환 계획
- [ ] phone number → E.164 정규화 계획
- [ ] boolean variant 변환 규칙 정의

### 11.2 프로덕션 배포 전 검증 항목

**스키마 업로드 전:**
- [ ] `aep schema create --use-ai --from-sample sample.json` 로컬 검증
- [ ] Primary Identity가 정확히 1개인지 확인
- [ ] `_{TENANT_ID}` 하위에 커스텀 필드가 올바르게 배치되었는지 확인

**데이터셋 생성 시:**
- [ ] `--enable-profile`, `--enable-identity` 플래그 설정 확인
- [ ] 스키마 `$id` URI가 정확한지 확인 (URL 인코딩 포함)

**첫 번째 배치 ingestion:**
- [ ] 소규모 샘플(10-100건)로 테스트 배치 먼저 실행
- [ ] `batch.status == BatchStatus.SUCCESS` 확인
- [ ] `batch.errors` 없음 확인
- [ ] AEP UI에서 Profile 조회하여 데이터 정상 수집 확인

---

## 참조 문서

| 문서 | 위치 | 내용 |
|------|------|------|
| ERD 표준 규칙 | `schema/knowledge/ERD_STANDARD.md` | Mermaid ERD 작성 규칙, 엔티티→XDM 변환 |
| XDM Field Groups | `references/xdm-field-groups.md` | Adobe 표준 Field Group 카탈로그 및 URI |
| Identity Namespaces | `references/identity-namespaces.md` | Namespace 레퍼런스, Descriptor API |
| Ingestion Patterns | `references/ingestion-patterns.md` | 포맷별 ingestion, 에러 트러블슈팅 |
| 스키마 모델 | `src/adobe_experience/schema/models.py` | Pydantic 모델 전체 정의 |
| XDM 분석기 | `src/adobe_experience/schema/xdm.py` | 자동 타입 감지, 스키마 생성 로직 |
| AI 추론 엔진 | `src/adobe_experience/agent/inference.py` | AI 기반 스키마 분석, Identity 전략 생성 |
