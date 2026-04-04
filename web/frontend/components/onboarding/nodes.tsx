"use client";

import { Handle, Node, NodeProps, Position } from "@xyflow/react";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  Circle,
  Database,
  FileJson,
  GitBranch,
  Layers,
  Target,
  Upload,
  UserCheck,
  Users,
  Zap,
} from "lucide-react";
import { goToOnboardingAction } from "@/lib/onboarding-nav";
import { pipelineNodeCaption } from "@/lib/normalize-onboarding-status";
import type { OnboardingStep } from "@/lib/types/onboarding";
import { PipelineNodeData } from "@/lib/mindmap-layout";

type PipelineNodeProps = NodeProps<Node<PipelineNodeData>>;

function navigable(step: OnboardingStep): boolean {
  return Boolean(step.action_url?.trim());
}

// ── Shared styling ─────────────────────────────────────────────────────────

const STEP_STYLE: Record<string, { border: string; bg: string; icon: string; iconColor: string }> = {
  auth:          { border: "border-slate-400",   bg: "bg-slate-50",   icon: "", iconColor: "text-slate-500" },
  schema:        { border: "border-indigo-400",  bg: "bg-indigo-50",  icon: "", iconColor: "text-indigo-500" },
  source:        { border: "border-violet-400",  bg: "bg-violet-50",  icon: "", iconColor: "text-violet-500" },
  dataflow:      { border: "border-blue-400",    bg: "bg-blue-50",    icon: "", iconColor: "text-blue-500" },
  dataset:       { border: "border-emerald-400", bg: "bg-emerald-50", icon: "", iconColor: "text-emerald-500" },
  ingest:        { border: "border-teal-400",    bg: "bg-teal-50",    icon: "", iconColor: "text-teal-500" },
  profile_ready: { border: "border-rose-400",    bg: "bg-rose-50",    icon: "", iconColor: "text-rose-500" },
  segment:       { border: "border-cyan-400",    bg: "bg-cyan-50",    icon: "", iconColor: "text-cyan-600" },
  destination:   { border: "border-orange-400",  bg: "bg-orange-50",  icon: "", iconColor: "text-orange-600" },
};

function stepIcon(key: string, className: string) {
  switch (key) {
    case "auth":          return <Zap className={className} />;
    case "schema":        return <FileJson className={className} />;
    case "source":        return <Layers className={className} />;
    case "dataflow":      return <GitBranch className={className} />;
    case "dataset":       return <Database className={className} />;
    case "ingest":        return <Upload className={className} />;
    case "profile_ready": return <UserCheck className={className} />;
    case "segment":       return <Users className={className} />;
    case "destination":   return <Target className={className} />;
    default:              return <Circle className={className} />;
  }
}

// ── Completed node ──────────────────────────────────────────────────────────

function CompletedNode({ data }: PipelineNodeProps) {
  const { step } = data;
  const s = STEP_STYLE[step.key] ?? STEP_STYLE.auth;
  const router = useRouter();
  const canNav = navigable(step);

  const go = () => goToOnboardingAction(step.action_url, router);

  return (
    <div
      className={`w-52 rounded-xl border-2 ${s.border} ${s.bg} shadow-sm transition-shadow
        ${canNav ? "cursor-pointer hover:shadow-md" : "cursor-default"}`}
      onClick={canNav ? go : undefined}
      onKeyDown={
        canNav
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                go();
              }
            }
          : undefined
      }
      role={canNav ? "button" : undefined}
      tabIndex={canNav ? 0 : undefined}
    >
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5" />
      <div className="p-3 flex items-start gap-2">
        <div className="mt-0.5 flex-shrink-0">
          {stepIcon(step.key, `w-4 h-4 ${s.iconColor}`)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-1 mb-0.5">
            <p className="text-xs font-semibold text-gray-800 truncate">{step.label}</p>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
          </div>
          {step.resource_name && (
            <p className="text-[10px] text-gray-500 truncate font-mono">{step.resource_name}</p>
          )}
          {!step.resource_name && (
            <p className="text-[10px] text-emerald-600">Done</p>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5" />
    </div>
  );
}

// ── Proposed (incomplete) node ──────────────────────────────────────────────

function ProposedNode({ data }: PipelineNodeProps) {
  const { step, isNext } = data;
  const router = useRouter();
  const canNav = navigable(step);

  const go = () => goToOnboardingAction(step.action_url, router);

  return (
    <div
      className={`w-52 rounded-xl border-2 border-dashed transition-all
        ${canNav ? "cursor-pointer" : "cursor-default"}
        ${isNext
          ? "border-amber-400 bg-amber-50 shadow-md " + (canNav ? "hover:shadow-lg" : "")
          : "border-gray-300 bg-gray-50 " + (canNav ? "hover:border-gray-400" : "")
        }`}
      onClick={canNav ? go : undefined}
      onKeyDown={
        canNav
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                go();
              }
            }
          : undefined
      }
      role={canNav ? "button" : undefined}
      tabIndex={canNav ? 0 : undefined}
    >
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5" />
      <div className="p-3 flex items-start gap-2">
        <div className="mt-0.5 flex-shrink-0">
          {stepIcon(step.key, `w-4 h-4 ${isNext ? "text-amber-500" : "text-gray-400"}`)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-1 mb-0.5">
            <p className={`text-xs font-semibold truncate ${isNext ? "text-amber-800" : "text-gray-500"}`}>
              {step.label}
            </p>
            {isNext && (
              <span className="text-[9px] font-bold text-amber-600 bg-amber-100 px-1 rounded flex-shrink-0">
                NEXT
              </span>
            )}
          </div>
          <p className={`text-[10px] leading-snug line-clamp-2 ${isNext ? "text-amber-600" : "text-gray-400"}`}>
            {pipelineNodeCaption(step)}
          </p>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5" />
    </div>
  );
}

// ── nodeTypes export ────────────────────────────────────────────────────────

export const nodeTypes = {
  auth:          CompletedNode,
  schema:        CompletedNode,
  source:        CompletedNode,
  dataflow:      CompletedNode,
  dataset:       CompletedNode,
  ingest:        CompletedNode,
  profile_ready: CompletedNode,
  segment:       CompletedNode,
  destination:   CompletedNode,
  proposed:      ProposedNode,
};
