# Interactive Node-Edge 시각화 프레임워크 검토

AEP 마인드맵의 Schema → Field Group → Dataset → Dataflow 관계를
인터랙티브하게 시각화하기 위한 프레임워크 비교 분석입니다.

현재 Web 스택: **Next.js 14 / React 18 / Tailwind / Radix UI**

---

## 1. 후보 프레임워크 비교

### 1-A. React Flow (`@xyflow/react`)
> 현재 `AEP_MINDMAP_WEB_UI.md`에서 채택한 방향

| 항목 | 평가 |
|---|---|
| React 통합 | ★★★★★ (React 전용, JSX 노드 컴포넌트) |
| 커스텀 노드 | ★★★★★ (임의의 React 컴포넌트를 노드로 사용) |
| 인터랙션 | ★★★★☆ (드래그, 줌, 패닝, 미니맵 내장) |
| 번들 크기 | ~120KB (gzip ~35KB) |
| 라이선스 | MIT (v11+) |
| 학습 비용 | 낮음 |
| AEP 적합도 | **높음** |

**장점**
- `SchemaNode`, `DatasetNode` 등 React 컴포넌트를 그대로 노드로 사용 → Tailwind/Radix UI와 100% 호환
- `Handle` 컴포넌트로 연결 포인트 세밀 제어
- `useReactFlow()` 훅으로 노드 상태를 React state처럼 관리
- `MiniMap`, `Controls`, `Background` 패널 내장
- **Edge 애니메이션** (`animated: true`, custom SVG path) 기본 지원
- AI 제안 노드(`ProposedStepNode`)의 점선/고스트 스타일 표현 용이

**단점**
- 수만 개 이상 노드에서 성능 저하 (AEP 리소스 수준에서는 문제 없음)
- D3 수준의 force-directed layout은 직접 구현 필요 (또는 `d3-force` 연동)

**결론: AEP 마인드맵의 1순위 선택**

---

### 1-B. D3.js (`d3`)
> 가장 낮은 레벨의 데이터 시각화 라이브러리

| 항목 | 평가 |
|---|---|
| React 통합 | ★★☆☆☆ (DOM 조작 방식 충돌, useRef 우회 필요) |
| 커스텀 노드 | ★★★☆☆ (SVG/HTML 직접 조작) |
| 인터랙션 | ★★★★★ (zoom, drag, force simulation 최강) |
| 번들 크기 | ~230KB (모듈 분리 시 ~40KB) |
| 라이선스 | ISC |
| 학습 비용 | 높음 |
| AEP 적합도 | **중간** |

**장점**
- `d3-force` 레이아웃: 노드 간 척력/인력 물리 시뮬레이션으로 자동 배치
- 완전한 커스터마이징 (픽셀 단위 제어)
- 대용량 그래프 성능 우수

**단점**
- React와 DOM 소유권 충돌 → `useEffect` + `useRef` 패턴 필수, 코드 복잡도 급증
- Tailwind/Radix UI와 직접 통합 불가 (SVG 기반)
- 노드 안에 React 컴포넌트 렌더링이 번거로움 (foreignObject 활용 필요)
- 개발 생산성 낮음

**결론: React Flow에 `d3-force` 레이아웃만 차용하는 방식이 더 실용적**

---

### 1-C. Cytoscape.js
> 생물정보학/네트워크 분석 분야 강자

| 항목 | 평가 |
|---|---|
| React 통합 | ★★★☆☆ (`react-cytoscapejs` 래퍼 존재) |
| 커스텀 노드 | ★★★☆☆ (CSS 스타일시트 방식, React JSX 불가) |
| 인터랙션 | ★★★★☆ (레이아웃 알고리즘 다수 내장) |
| 번들 크기 | ~280KB |
| 라이선스 | MIT |
| 학습 비용 | 중간 |
| AEP 적합도 | **낮음~중간** |

**장점**
- `cola`, `dagre`, `elk` 등 다양한 자동 레이아웃 알고리즘 플러그인
- 그래프 분석 API (최단 경로, 컴포넌트 탐지 등) 내장

**단점**
- 노드 스타일을 JSON 스타일시트로 정의 → Tailwind/Radix UI와 단절
- React 컴포넌트를 노드로 사용 불가 (Canvas/SVG 렌더)
- 커뮤니티 규모 축소 추세

**결론: AEP 마인드맵 요구사항과 스택 불일치, 비추천**

---

### 1-D. Elkjs + React Flow (조합)
> 자동 레이아웃이 필요한 복잡한 DAG에 최적

| 항목 | 평가 |
|---|---|
| React 통합 | ★★★★★ (React Flow 위에 레이어 추가) |
| 커스텀 노드 | ★★★★★ (React Flow 그대로) |
| 레이아웃 자동화 | ★★★★★ (Eclipse Layout Kernel, 계층형 DAG 최강) |
| 번들 크기 | React Flow + ~200KB |
| 라이선스 | EPL 2.0 (상업용 주의) |
| AEP 적합도 | **높음 (복잡한 경우)** |

**AEP 시나리오:**  
Schema → FieldGroup → Dataset → Dataflow → Destination 처럼
방향성 있는 DAG(Directed Acyclic Graph) 구조에서 노드 수가 늘어날 때 `elkjs`의 자동 배치가 강점.

**결론: React Flow 기본 적용 후, 노드 수 증가 시 `elkjs` 레이아웃 플러그인 추가 전략**

---

### 1-E. Sigma.js + Graphology
> 대용량 그래프 전문 (수천~수만 노드)

| 항목 | 평가 |
|---|---|
| React 통합 | ★★★☆☆ (`@react-sigma/core` 존재) |
| 커스텀 노드 | ★★☆☆☆ (Canvas 기반, HTML 노드 불가) |
| 성능 | ★★★★★ (WebGL 렌더) |
| AEP 적합도 | **낮음** |

**결론: AEP 리소스 규모(~수백 노드)에서 오버스펙, 비추천**

---

## 2. 최종 권장 조합

```
React Flow (@xyflow/react v12)          ← 메인 렌더러
    + dagre (자동 계층형 레이아웃)        ← 초기 노드 배치 자동화
    + d3-force (선택적)                  ← 자유형 탐색 모드 레이아웃
    + elkjs (장기 옵션)                  ← 복잡도 증가 시 교체
```

### 이유
1. **현재 스택 완벽 통합**: Tailwind, Radix UI, lucide-react를 노드 내부에서 그대로 사용
2. **개발 속도**: `AEP_MINDMAP_WEB_UI.md`의 설계 (`SchemaNode`, `DatasetNode`, `ProposedStepNode`)를 그대로 구현 가능
3. **dagre 레이아웃**: Schema → FieldGroup → Dataset 계층 구조를 위에서 아래로 자동 정렬
4. **점진적 확장**: 처음엔 React Flow만, 노드 수 증가 시 elkjs 플러그인만 교체

---

## 3. React Flow + dagre 적용 설계

### 설치
```bash
npm install @xyflow/react dagre
npm install -D @types/dagre
```

### 레이아웃 유틸 (예시)
```typescript
// lib/mindmap-layout.ts
import dagre from 'dagre';
import { Node, Edge } from '@xyflow/react';

const NODE_WIDTH = 256;   // SchemaNode 기준
const NODE_HEIGHT = 100;

export function applyDagreLayout(nodes: Node[], edges: Edge[]) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80 });

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));

  dagre.layout(g);

  return nodes.map((n) => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
  });
}
```

### 노드 타입 매핑 (AEP 리소스)

| AEP 리소스 | 노드 타입 | 색상 |
|---|---|---|
| XDM Schema | `schema` | Indigo (#6366f1) |
| Field Group | `fieldgroup` | Purple (#a855f7) |
| Dataset | `dataset` | Emerald (#10b981) |
| Dataflow | `dataflow` | Blue (#3b82f6) |
| Identity Namespace | `identity` | Amber (#f59e0b) |
| AI 제안 (다음 단계) | `proposed` | Amber 점선 |

### Edge 상태별 스타일

| 상태 | 색상 | 스타일 |
|---|---|---|
| 정상 연결 | Emerald | `animated: true`, solid |
| 미연결 (제안) | Amber | `strokeDasharray: '5 5'` |
| 오류 | Red | `animated: false`, 경고 라벨 |
| 처리 중 | Blue | 빠른 CSS `stroke-dashoffset` 애니메이션 |

---

## 4. CLI → Web UI 데이터 파이프라인

```
aep schema create (Python CLI)
    │
    ▼
~/.adobe/workspace/mindmap_state.json  ← 생성 결과 직렬화
    │
    ▼
Web API GET /api/mindmap              ← FastAPI 파일 읽기
    │
    ▼
React Flow Canvas                     ← nodes/edges 렌더링
    │
    ▼
aep web open --page mindmap           ← 브라우저 자동 오픈
```

`mindmap_state.json` 스키마 예시:
```json
{
  "updated_at": "2026-04-01T12:00:00Z",
  "nodes": [
    { "id": "schema-1", "type": "schema", "data": { "title": "Customer Profile", "class": "Profile" } },
    { "id": "fg-1", "type": "fieldgroup", "data": { "title": "Customer Profile - Custom Fields" } },
    { "id": "proposed-dataset", "type": "proposed", "data": { "label": "데이터셋 생성", "command": "aep dataset create --schema-id ..." } }
  ],
  "edges": [
    { "id": "e1", "source": "schema-1", "target": "fg-1", "status": "connected" },
    { "id": "e2", "source": "schema-1", "target": "proposed-dataset", "status": "proposed" }
  ]
}
```

---

## 5. 진행 상태

- [x] 프레임워크 비교 분석
- [x] React Flow + dagre 조합 결정
- [ ] `mindmap_state.json` 직렬화 로직 (Python CLI)
- [ ] Web API `/api/mindmap` 엔드포인트
- [ ] `SchemaNode`, `FieldGroupNode`, `DatasetNode` 컴포넌트
- [ ] `ProposedStepNode` (AI 제안 노드)
- [ ] dagre 자동 레이아웃 유틸
- [ ] Edge 상태별 애니메이션
- [ ] `aep mindmap generate` CLI 커맨드

---

*연관 백로그: AEP_MINDMAP.md, AEP_MINDMAP_WEB_UI.md, SCHEMA_UX_IMPROVEMENT.md*
