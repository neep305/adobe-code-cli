# Schema UX 개선 백로그

AEP 마인드맵 / 슈퍼바이저 에이전트 비전과 연계하여,
`aep schema` 커맨드의 사용자 경험을 단계적으로 향상시키기 위한 아이디어 모음입니다.

---

## 1. Schema Creation Mindmap (핵심 아이디어)

### 개요
스키마 생성 과정을 단순한 텍스트 출력이 아닌, 리소스 간 관계와 진행 상태를 시각화한 "진행 마인드맵"으로 표현합니다.

### 두 가지 형태

#### A. CLI 인라인 마인드맵 (TUI)
`aep schema create` 실행 시 각 단계를 Rich Tree로 실시간 렌더링합니다.

```
Schema Creation Plan
├── [○] 1. 데이터 프로파일링
│         sample.json → 12 fields detected
├── [○] 2. XDM Class 결정
│         Profile / ExperienceEvent / Custom
├── [○] 3. Field Group 생성
│         (tenant 네임스페이스 자동 적용)
├── [○] 4. Schema 생성
│         Class + Field Group 조합
└── [○] 5. AEP 업로드
          Field Group → Schema 순서 보장
```

각 단계 완료 시 `[○]` → `[✓]` 로 상태 전환 (Rich Live 활용).

#### B. Web UI 마인드맵 (React Flow)
`aep schema create --mindmap` 또는 `aep mindmap schema` 실행 시
기존 `AEP_MINDMAP_WEB_UI.md`에서 설계한 React Flow 기반 캔버스를 브라우저로 열어,
생성된 Schema → Field Group → Dataset 노드 간 연결 관계를 인터랙티브하게 시각화.

**노드 구성:**
- `SchemaNode` (indigo): 생성된 XDM 스키마
- `FieldGroupNode` (purple): 연결된 Field Group
- `DatasetNode` (emerald): 연결 가능한 Dataset (점선 = 미연결)
- `ProposedStepNode` (amber): 다음 추천 단계 (AI 제안)

**구현 포인트:**
- CLI Python 레이어: 스키마 생성 결과를 JSON으로 직렬화하여 `~/.adobe/workspace/mindmap_state.json`에 저장
- Web API: `GET /api/mindmap/schema` → 상태 파일 읽어 React Flow 데이터 반환
- 기존 `web/frontend/app/schemas/page.tsx` 확장

---

## 2. Schema Onboarding Checklist

### 개요
"스키마를 처음 만드는 사람"이 알아야 할 모든 단계를 체크리스트로 제공합니다.
기존 `Milestone` enum과 `OnboardingState`를 활용하여 진행 상태를 추적합니다.

### 새 커맨드: `aep schema checklist`

```
$ aep schema checklist

┌─ Schema 생성 체크리스트 ─────────────────────────────────────┐
│                                                              │
│  [✓] 1. AEP 인증 설정          aep auth test                │
│  [✓] 2. 테넌트 ID 확인         aep auth whoami              │
│  [ ] 3. 샘플 데이터 준비        sample.json (10~50 records)  │
│  [ ] 4. XDM 클래스 선택        Profile / ExperienceEvent    │
│  [ ] 5. 스키마 생성 (로컬)      aep schema create --dry-run  │
│  [ ] 6. 스키마 검증            aep schema validate          │
│  [ ] 7. AEP 업로드             aep schema create --upload   │
│  [ ] 8. 데이터셋 연결          aep dataset create           │
│                                                              │
│  진행률: ██████░░░░░░░░░░  2 / 8 완료                        │
└──────────────────────────────────────────────────────────────┘

다음 추천 작업: [3] 샘플 데이터 준비 → aep schema create --interactive
```

### 체크리스트 상태 자동 감지
- 인증 완료 여부: `.env` 파일 존재 + `AEP_CLIENT_ID` 값 확인
- 스키마 생성 여부: `Milestone.FIRST_SCHEMA` 체크
- 업로드 여부: AEP API `list schemas` 응답 기반

### 마인드맵 연동
`aep schema checklist --mindmap` 실행 시 Web UI에서 체크리스트 진행 상태를
마인드맵 위에 오버레이 표시 (완료된 노드는 초록, 미완료는 회색).

---

## 3. 추가 UX 개선 아이디어

### 3-A. `aep schema diff` — 스키마 변경 전/후 비교

```bash
aep schema diff --local schema_v2.json --remote <schema-id>
```

- 로컬 수정 파일과 AEP에 업로드된 현재 버전을 field 단위로 비교
- 추가/삭제/변경된 필드를 색상으로 구분 (green/red/yellow)
- 슈퍼바이저 에이전트의 "임팩트 분석" 기능 전신(前身)

---

### 3-B. `aep schema suggest` — 필드명 기반 AI 자동 완성

```bash
aep schema suggest --fields "email,purchase_date,total_amount,product_sku"
```

- 필드명만 입력하면 AI가 XDM 타입, 포맷, Identity 여부, 표준 Field Group 매칭을 추천
- 샘플 데이터 없이도 빠른 스키마 프로토타이핑 가능
- 기존 `AIInferenceEngine.suggest_schema_fields()` 활용

---

### 3-C. `aep schema clone` — 기존 스키마 복제

```bash
aep schema clone --from <schema-id> --name "Customer Profile v2"
```

- AEP의 기존 스키마를 로컬로 내려받아 수정 후 새 이름으로 재업로드
- 유사한 스키마를 반복 작성하는 수고 제거

---

### 3-D. 스키마 생성 결과의 Mermaid ERD 자동 출력

`aep schema create` 완료 후 선택적으로 Mermaid ERD를 stdout 또는 파일로 출력합니다.

```bash
aep schema create --name "Orders" --from-sample orders.json --output-erd orders.mmd
```

- 기존 `_generate_mermaid_erd()` 함수 재활용
- 기술 문서 자동화 목적

---

### 3-E. Field Group 재사용 탐지

스키마 생성 시 AEP에 이미 존재하는 유사 Field Group을 탐지하여 재사용 제안:

```
ℹ️  유사한 Field Group 발견:
  → "Commerce Details" (Adobe 표준, 87% 일치)
  → "My_Commerce_Fields" (테넌트, 72% 일치)
  재사용하시겠습니까? [y/N]:
```

- 중복 Field Group 생성 방지
- AEP Schema Registry의 `list-fieldgroups` 결과와 AI 유사도 비교

---

### 3-F. `--watch` 모드 — 파일 변경 감지 자동 재생성

```bash
aep schema create --from-sample data.json --watch
```

- `data.json` 파일 변경 감지 시 스키마 자동 재분석 및 diff 출력
- 로컬 개발 반복 주기 단축

---

## 4. 우선순위

| 아이디어 | 임팩트 | 구현 난이도 | 선행 조건 | 우선순위 |
|---|---|---|---|---|
| Schema Creation Mindmap (TUI) | 높음 | 낮음 | 없음 | **P1** |
| Schema Onboarding Checklist | 높음 | 낮음 | 없음 | **P1** |
| `schema suggest` | 중간 | 낮음 | AIInferenceEngine | P2 |
| `schema diff` | 높음 | 중간 | AEP API | P2 |
| Field Group 재사용 탐지 | 높음 | 중간 | list-fieldgroups | P2 |
| `schema clone` | 중간 | 낮음 | AEP API | P3 |
| Mermaid ERD 자동 출력 | 낮음 | 낮음 | 기존 함수 | P3 |
| Web UI 마인드맵 연동 | 높음 | 높음 | React Flow, Web API | P3 (슈퍼바이저 병행) |
| `--watch` 모드 | 낮음 | 중간 | watchdog 라이브러리 | P4 |

---

## 5. 슈퍼바이저 에이전트와의 연결 고리

이 백로그의 아이디어들은 슈퍼바이저 에이전트의 핵심 기능과 직접 연결됩니다.

```
현재 CLI 개선 (이 백로그)
    ├── Schema Creation Mindmap (TUI) ──→ 슈퍼바이저 "마인드맵 수립" 단계 시각화
    ├── Onboarding Checklist         ──→ 슈퍼바이저 "컨텍스트 주입" 입력 데이터
    ├── schema diff                  ──→ 슈퍼바이저 "임팩트 분석" 기반
    └── Field Group 재사용 탐지      ──→ 슈퍼바이저 "Schema Architect" 에이전트 로직
```

---

*연관 백로그: SUPERVISOR_AGENT.md, AEP_MINDMAP.md, AEP_MINDMAP_WEB_UI.md*
