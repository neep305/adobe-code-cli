import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api";
import type {
  ChecklistItem,
  FinalizeResult,
  StepResult,
  WizardSession,
  WizardWsEvent,
} from "@/lib/types/schema_wizard";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

interface UseSchemaWizardReturn {
  session: WizardSession | null;
  currentResult: StepResult | null;
  liveChecklist: ChecklistItem[];
  isAnalyzing: boolean;
  isConnected: boolean;
  error: string | null;
  createSession: () => Promise<void>;
  submitStep: (phase: number, formData: FormData) => Promise<StepResult>;
  finalizeSession: (uploadToAep: boolean) => Promise<FinalizeResult>;
  approveStep: (phase: number) => void;
}

export function useSchemaWizard(): UseSchemaWizardReturn {
  const [session, setSession] = useState<WizardSession | null>(null);
  const [currentResult, setCurrentResult] = useState<StepResult | null>(null);
  const [liveChecklist, setLiveChecklist] = useState<ChecklistItem[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<NodeJS.Timeout>();

  // ── WebSocket management ──────────────────────────────────────────────────

  const connectWs = useCallback((sessionId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (typeof window === "undefined") return;

    try {
      const ws = new WebSocket(`${WS_URL}/ws/schema-wizard/${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      ws.onmessage = (evt) => {
        try {
          const msg: WizardWsEvent = JSON.parse(evt.data);
          handleWsEvent(msg);
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => setError("WebSocket 연결 오류");

      ws.onclose = () => {
        setIsConnected(false);
        // Reconnect after 3s
        reconnectRef.current = setTimeout(() => connectWs(sessionId), 3000);
      };
    } catch {
      setError("WebSocket 연결 실패");
    }
  }, []);

  const handleWsEvent = (msg: WizardWsEvent) => {
    if (msg.event === "analyzing_start") {
      setIsAnalyzing(true);
    } else if (msg.event === "checklist_update") {
      setLiveChecklist((prev) =>
        prev.map((item) =>
          item.id === msg.item ? { ...item, status: msg.status } : item
        )
      );
    } else if (msg.event === "step_complete") {
      setIsAnalyzing(false);
      setLiveChecklist(msg.checklist);
    }
  };

  useEffect(() => {
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, []);

  // ── Session management ────────────────────────────────────────────────────

  const createSession = useCallback(async () => {
    setError(null);
    try {
      const data = await apiClient.post<WizardSession>("/api/schema-wizard/sessions");
      setSession(data);
      connectWs(data.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "세션 생성 실패");
      throw err;
    }
  }, [connectWs]);

  const submitStep = useCallback(
    async (phase: number, formData: FormData): Promise<StepResult> => {
      if (!session) throw new Error("세션이 없습니다. 먼저 세션을 생성하세요.");
      setIsAnalyzing(true);
      setError(null);

      // Initialise live checklist from phase definition
      setLiveChecklist(
        Array.from({ length: 4 }, (_, i) => ({
          id: `p${phase}_item${i}`,
          label: "분석 중...",
          status: "analyzing" as const,
          detail: null,
        }))
      );

      try {
        const result = await apiClient.uploadFormData<StepResult>(
          `/api/schema-wizard/sessions/${session.session_id}/steps/${phase}`,
          formData
        );
        setCurrentResult(result);
        setLiveChecklist(result.checklist);
        setSession((prev) =>
          prev
            ? {
                ...prev,
                current_phase: Math.max(prev.current_phase, phase + 1),
                steps: {
                  ...prev.steps,
                  [phase]: {
                    phase,
                    status: "completed",
                    user_input: {},
                    agent_output: result.agent_output,
                    checklist: result.checklist,
                    confidence: result.confidence,
                    warnings: result.warnings,
                    recommendations: result.recommendations,
                  },
                },
                erd_mermaid: result.erd_mermaid ?? prev.erd_mermaid,
                entities:
                  phase === 1
                    ? ((result.agent_output.entities as typeof prev.entities) ?? prev.entities)
                    : prev.entities,
              }
            : prev
        );
        return result;
      } catch (err) {
        setIsAnalyzing(false);
        setError(err instanceof Error ? err.message : "단계 분석 실패");
        throw err;
      }
    },
    [session]
  );

  const finalizeSession = useCallback(
    async (uploadToAep: boolean): Promise<FinalizeResult> => {
      if (!session) throw new Error("세션이 없습니다.");
      setError(null);
      try {
        return await apiClient.post<FinalizeResult>(
          `/api/schema-wizard/sessions/${session.session_id}/finalize`,
          { upload_to_aep: uploadToAep }
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "스키마 생성 실패");
        throw err;
      }
    },
    [session]
  );

  const approveStep = useCallback((phase: number) => {
    setSession((prev) => {
      if (!prev) return prev;
      const step = prev.steps[phase];
      if (!step) return prev;
      return {
        ...prev,
        steps: { ...prev.steps, [phase]: { ...step, status: "approved" } },
      };
    });
  }, []);

  return {
    session,
    currentResult,
    liveChecklist,
    isAnalyzing,
    isConnected,
    error,
    createSession,
    submitStep,
    finalizeSession,
    approveStep,
  };
}
