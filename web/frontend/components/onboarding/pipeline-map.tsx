"use client";

import { useEffect, useMemo } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  MiniMap,
  Node,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";

import { nodeTypes } from "@/components/onboarding/nodes";
import { buildPipelineLayout, PipelineNodeData } from "@/lib/mindmap-layout";
import { OnboardingStatus } from "@/lib/types/onboarding";

interface PipelineMapProps {
  status: OnboardingStatus;
}

/**
 * All React Flow hooks run under ReactFlowProvider so fitView runs after dagre positions apply.
 * (Initial `fitView` on an empty node list is a common cause of wrong zoom / misleading layout.)
 */
function PipelineMapInner({ status }: PipelineMapProps) {
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<PipelineNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const layoutKey = useMemo(
    () => status.steps.map((s) => `${s.key}:${s.completed ? 1 : 0}`).join("|"),
    [status.steps]
  );

  useEffect(() => {
    const { nodes: layoutNodes, edges: layoutEdges } = buildPipelineLayout(status.steps);
    setNodes(layoutNodes);
    setEdges(layoutEdges);
  }, [status, layoutKey, setNodes, setEdges]);

  useEffect(() => {
    if (nodes.length === 0) return;
    const id = requestAnimationFrame(() => {
      fitView({
        padding: 0.2,
        duration: 200,
        maxZoom: 1.35,
        minZoom: 0.2,
      });
    });
    return () => cancelAnimationFrame(id);
  }, [layoutKey, nodes.length, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.2, maxZoom: 1.35, minZoom: 0.2 }}
      minZoom={0.2}
      maxZoom={1.8}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      proOptions={{ hideAttribution: true }}
      defaultEdgeOptions={{
        type: "smoothstep",
      }}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
      <Controls showInteractive={false} className="!shadow-none !border !border-gray-200 !rounded-lg" />
      <MiniMap
        nodeStrokeWidth={2}
        nodeColor={(n) => {
          const data = n.data as PipelineNodeData;
          return data?.step?.completed ? "#10b981" : "#f59e0b";
        }}
        className="!border !border-gray-200 !rounded-lg !shadow-none"
        pannable
        zoomable
      />
    </ReactFlow>
  );
}

export function PipelineMap({ status }: PipelineMapProps) {
  return (
    <div className="w-full h-full min-h-[480px] rounded-xl border border-gray-200 bg-white overflow-hidden">
      <ReactFlowProvider>
        <PipelineMapInner status={status} />
      </ReactFlowProvider>
    </div>
  );
}
