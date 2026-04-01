# AEP 마인드맵 Web UI: React Flow 노드 설계

## 1. 개요
React Flow의 `Custom Node` 기능을 사용하여 AEP 리소스의 메타데이터를 캔버스에 렌더링하고, 에이전트와 상호작용하는 UI 컴포넌트를 정의합니다.

## 2. 커스텀 노드 컴포넌트 예시 (TypeScript)

### A. 기본 리소스 노드 (BaseResourceNode)
모든 AEP 노드의 공통 레이아웃을 정의합니다.

```typescript
import { Handle, Position } from 'reactflow';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export const SchemaNode = ({ data }: { data: any }) => {
  return (
    <Card className="w-64 border-2 border-indigo-500 shadow-lg">
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-indigo-500" />
      <CardHeader className="p-3 bg-indigo-50">
        <div className="flex justify-between items-center">
          <CardTitle className="text-sm font-bold truncate">{data.title}</CardTitle>
          <Badge variant="outline" className="text-[10px]">Schema</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-3 text-xs">
        <div className="space-y-1">
          <p className="text-muted-foreground">Class: {data.baseClass}</p>
          <p className="font-mono text-[10px] bg-slate-100 p-1 rounded">{data.id}</p>
        </div>
      </CardContent>
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-indigo-500" />
    </Card>
  );
};

export const DatasetNode = ({ data }: { data: any }) => {
  return (
    <Card className="w-64 border-2 border-emerald-500">
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-emerald-500" />
      <CardHeader className="p-3 bg-emerald-50">
        <div className="flex justify-between items-center">
          <CardTitle className="text-sm font-bold">{data.name}</CardTitle>
          <Badge className="bg-emerald-500">Dataset</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-3 text-xs">
        <div className="flex justify-between mb-2">
          <span>Status:</span>
          <Badge variant={data.status === 'Success' ? 'success' : 'destructive'}>
            {data.status}
          </Badge>
        </div>
        <p className="text-muted-foreground">Records: {data.recordCount.toLocaleString()}</p>
      </CardContent>
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-emerald-500" />
    </Card>
  );
};
```

### B. 에이전트 제안 노드 (ProposedStepNode)
에이전트가 "다음에 생성할 것"을 제안할 때 보여주는 고스트 노드입니다.

```typescript
export const ProposedStepNode = ({ data }: { data: any }) => {
  return (
    <div className="w-64 p-4 border-2 border-dashed border-amber-400 bg-amber-50 rounded-xl opacity-80 group hover:opacity-100 transition-all">
      <div className="text-[10px] font-bold text-amber-600 mb-1 flex items-center gap-1">
        ✨ AI Suggestion
      </div>
      <h4 className="text-sm font-bold mb-2">{data.label}</h4>
      <p className="text-xs text-muted-foreground mb-3">{data.description}</p>
      <button className="w-full py-1 bg-amber-500 text-white text-xs rounded hover:bg-amber-600">
        이 단계 실행하기
      </button>
    </div>
  );
};
```

## 3. 노드 및 에지 타입 등록
React Flow 인스턴스에서 다음과 같이 `nodeTypes`와 `edgeTypes`를 등록하여 사용합니다.

```typescript
const nodeTypes = { 
  schema: SchemaNode, 
  dataset: DatasetNode, 
  proposed: ProposedStepNode 
};

// Custom Edge는 상태에 따라 애니메이션과 색상을 동적으로 변경합니다.
const edgeTypes = {
  workflow: WorkflowEdge,
};
```

## 4. 데이터 흐름 에지(Edge) 애니메이션 설계

데이터의 흐름 상태에 따라 에지의 `style`과 `animated` 속성을 다르게 적용하여 시각적 피드백을 제공합니다.

### A. 상태별 에지 스타일 정의

1. **정상 흐름 (Success)**
   - **색상**: `#10b981` (Emerald 500)
   - **애니메이션**: `animated: true` (부드러운 점선 이동)
   - **의도**: 데이터가 지연 없이 타겟 리소스로 잘 전달되고 있음을 의미합니다.

2. **데이터 오류/중단 (Failure)**
   - **색상**: `#ef4444` (Red 500)
   - **애니메이션**: `animated: false`, `strokeDasharray: '5 5'` (정지된 점선)
   - **특수효과**: 에지 중앙에 ⚠️ 아이콘 또는 'Error' 라벨 표시
   - **의도**: 데이터 흐름이 끊겼거나 배치가 실패했음을 즉각적으로 경고합니다.

3. **처리 중 (Processing/Active)**
   - **색상**: `#3b82f6` (Blue 500)
   - **애니메이션**: 빠른 속도의 `stroke-dashoffset` CSS 애니메이션 적용
   - **의도**: 현재 대량의 데이터가 동기화 중이거나 ingestion이 활발히 일어나고 있음을 표현합니다.

### B. CSS 애니메이션 예시

```css
/* 처리 중인 에지에 적용할 빠른 흐름 효과 */
.react-flow__edge-path.processing {
  stroke-dasharray: 10;
  animation: flow 0.5s linear infinite;
}

@keyframes flow {
  from {
    stroke-dashoffset: 20;
  }
  to {
    stroke-dashoffset: 0;
  }
}
```

## 5. 진행 상태
- [x] 개념 설계 (Architecture)
- [x] UI/UX 디자인 가이드라인 (TUI/Rich)
- [x] React Flow 커스텀 노드 컴포넌트 설계
- [x] 데이터 흐름 에지 애니메이션 아이디어 정리
- [ ] CLI 오케스트레이터 (Python Logic) 구현