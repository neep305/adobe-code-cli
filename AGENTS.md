# AGENTS.md

> AEP Schema Agents 전용 에이전트 개발 규칙.  
> 이 프로젝트는 LangGraph 기반 멀티 에이전트로 Adobe Experience Platform의 XDM 스키마 생성·검증·등록을 자동화합니다.

---

## Agent Architecture

- 모든 에이전트는 **LangGraph**로만 구현한다 (ReAct 패턴 단독 사용 금지).
- 멀티 에이전트 작업은 반드시 `src/adobe_experience/agent/supervisor_graph.py`를 통해 오케스트레이션한다.
- 개별 에이전트(`schema_mapping_agent`, `data_analysis_agent`)는 `agent/agents/` 디렉토리에 위치한다.
- 새 에이전트를 추가하기 전에 기존 에이전트를 확장할 수 있는지 먼저 검토한다.

## Tooling Rules

- AEP API 직접 호출은 `cli/llm_tools/executor.py`를 통해서만 허용한다.
- Tool 정의는 `cli/llm_tools/` 하위에 위치하며, `registry.py`에 등록한다.
- 에이전트는 외부 API를 직접 import하여 호출하지 않는다.
- 모든 AEP API 호출에는 `Authorization`, `x-api-key`, `x-gw-ims-org-id`, `x-sandbox-name` 헤더가 포함되어야 한다.

## State Management

- LangGraph 상태는 `TypedDict` 기반으로 정의한다.
- 상태 객체는 in-place 변경 금지 — 항상 새 dict를 반환한다.
- 에이전트 간 공유 상태 구조는 `agent/graph_state.py`에 정의한다.

## File Modification Rules

- 기존 에이전트를 수정하는 것이 새 에이전트를 생성하는 것보다 우선이다.
- `agent/contracts.py`의 인터페이스 계약(contract)은 하위 호환성을 유지하며 변경한다.
- `cli/llm_tools/schemas.py`의 Tool 스키마 변경 시 반드시 `safety.py` 검사를 업데이트한다.

---

## Backend Add-ons

- AEP API 클라이언트(`aep/client.py`)는 REST 방식으로만 통신하며, 엔드포인트 버전은 상수로 관리한다.
- 모든 엔드포인트 응답에 구조화된 로깅(structured logging)을 적용한다.
- 에러 처리 시 재시도 가능(429, 503)과 불가(400, 403) 에러를 반드시 구분한다.
- OAuth Server-to-Server 토큰은 만료 전 자동 갱신 로직을 포함한다.

## Data Engineering Add-ons

- **스키마 변경 시 Backward Compatibility를 반드시 검사한다**:
  - 기존 필드 삭제 또는 타입 변경은 금지.
  - 새 필수(required) 필드 추가 시 기존 데이터셋 호환성을 먼저 확인한다.
- 데이터 품질 검사(`processors/xdm_validator.py`)는 AEP 업로드 전 필수 단계다.
- Parquet 변환(`processors/csv_to_parquet.py`, `json_to_parquet.py`) 후 스키마 적합성을 재검증한다.
- 배치 수집 파이프라인은 SLA 기준: 업로드 완료 후 **30분 내** 상태 확인 완료.

## ML/AI Add-ons

- AI가 생성한 XDM 스키마는 **사람의 승인 후**에만 AEP Schema Registry에 등록한다.
- AI 추론 결과(필드 타입, Identity 제안)는 근거(confidence, reasoning)와 함께 로그에 기록한다.
- 프롬프트 변경 시 기존 스키마 생성 결과와 회귀 비교 테스트를 수행한다.
- LLM 모델 버전(`claude-sonnet-4-5` 등)은 `core/config.py`에서 중앙 관리한다.

---

## Schema Agent Pipeline

XDM 스키마 작업은 반드시 아래 3단계 파이프라인을 따른다:

```
1. aep-schema          → 샘플 데이터(CSV/JSON)에서 XDM 스키마 초안 생성
        ↓
2. aep-schema-validator → 5개 레이어 검증 (Critical/Warning 탐지)
        ↓
3. aep-schema-refactor  → 검증 결과 기반 오류 수정 및 최종 스키마 생성
        ↓
   아키텍트 승인 → AEP Registry 등록
```

- 단계를 건너뛰는 직접 등록은 금지한다.
- 각 단계의 출력은 다음 에이전트의 입력으로 전달한다.
- `aep-schema-refactor` 출력 후 `aep-schema-validator` 재검증을 통해 Critical 0건을 확인한 후에만 등록을 진행한다.

---

## AEP Schema 규칙

- **XDM 유효성 검사 통과 후에만 AEP API를 호출한다** — `processors/xdm_validator.py` 사용.
- **PII 필드(email, phone, 주민번호 등)는 반드시 Identity Namespace를 지정한다**:
  - Email → `Email` namespace
  - Phone → `Phone` namespace
  - 커스텀 ID → 조직 전용 namespace 사전 정의 필요
- AI가 생성한 스키마는 배포 전 아키텍트 검토를 거친다 (자동 배포 금지).
- **모든 XDM 스키마에는 Primary Identity 필드가 필수**로 정의되어야 한다.
- 스키마 등록 전 `_id`, `timestamp` 필드 존재 여부를 자동 확인한다.
