"""LangGraph-ready supervisor runner with deterministic routing rules.

This module intentionally keeps the runner interface stable while the backing
graph implementation evolves. It can be wired to LangGraph later without
changing callers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from adobe_experience.agent.contracts import (
    AgentResult,
    AgentResultStatus,
    Capability,
    ExecutionContext,
    SafetyMode,
)
from adobe_experience.agent.graph_state import GraphState
from adobe_experience.agent.registry import AgentRegistry, register_default_agents
from adobe_experience.agent.tracing import get_tracer


class SupervisorGraphRunner:
    """Supervisor runner that applies intent routing and policy gates."""

    def __init__(
        self,
        registry: AgentRegistry,
        read_only_default: bool = True,
        tool_bridge: Optional[Any] = None,
        tracer: Optional[Any] = None,
        verbose: bool = False,
        console: Optional[Any] = None,
    ) -> None:
        self.registry = registry
        self.read_only_default = read_only_default
        self.tool_bridge = tool_bridge
        self.tracer = tracer or get_tracer("supervisor")
        self.verbose = verbose
        self.console = console
        register_default_agents(self.registry)

    def run(self, request: Dict[str, Any]) -> GraphState:
        """Execute supervisor flow and return final graph state."""
        with self.tracer.span(
            "supervisor.run",
            inputs=request,
            metadata={"component": "SupervisorGraphRunner"},
            run_type="chain",
        ) as span:
            state = self.normalize_input(request)
            
            if self.verbose and self.console:
                self.console.print("[bold]Step 1:[/bold] Normalizing input...")
            
            state.normalized_intent = self.classify_intent(state)
            
            if self.verbose and self.console:
                self.console.print(f"[bold]Step 2:[/bold] Intent classified as: [cyan]{state.normalized_intent}[/cyan]")
            
            state.context = self.build_context(state)
            
            if self.verbose and self.console:
                self.console.print(f"[bold]Step 3:[/bold] Context built (source: [cyan]{state.context.input_source}[/cyan])")
            
            self.execute_tool_calls(state)
            state.route = self.route_capability(state)
            
            if self.verbose and self.console:
                self.console.print(f"[bold]Step 4:[/bold] Route determined: [yellow bold]{state.route}[/yellow bold]")
            
            self.execute_route(state)
            self.merge_results(state)
            
            if self.verbose and self.console:
                self.console.print(f"[bold]Step 5:[/bold] Results merged (confidence: [cyan]{state.confidence:.2f}[/cyan])")
            
            self.apply_confidence_gate(state)
            
            if self.verbose and self.console:
                confidence_level = "HIGH" if state.confidence >= 0.7 else ("MEDIUM" if state.confidence >= 0.5 else "LOW")
                confidence_color = "green" if state.confidence >= 0.7 else ("yellow" if state.confidence >= 0.5 else "red")
                self.console.print(f"[bold]Step 6:[/bold] Confidence: [{confidence_color}]{state.confidence:.2f} ({confidence_level})[/{confidence_color}]")
                if state.warnings:
                    for warning in state.warnings:
                        self.console.print(f"  [yellow]⚠[/yellow]  {warning}")
            
            self.finalize_response(state)
            span.set_outputs(
                {
                    "route": state.route,
                    "selected_agents": state.selected_agents,
                    "confidence": state.confidence,
                    "warnings": state.warnings,
                }
            )
            return state

    def normalize_input(self, request: Dict[str, Any]) -> GraphState:
        """Normalize incoming payload into a stable graph state."""
        return GraphState(
            request_id=str(request.get("request_id", "req-auto")),
            trace_id=str(request.get("trace_id", request.get("request_id", "trace-auto"))),
            raw_request=request,
        )

    def classify_intent(self, state: GraphState) -> str:
        """Classify request into analysis|schema|mixed|unsupported."""
        payload = state.raw_request
        text = f"{payload.get('intent', '')} {payload.get('query', '')}".lower()

        has_analysis = any(token in text for token in ["analy", "quality", "relationship", "profiling"])
        has_schema = any(token in text for token in ["schema", "xdm", "mapping", "class id", "identity"])

        if has_analysis and has_schema:
            return "mixed"
        if has_analysis:
            return "analysis"
        if has_schema:
            return "schema"
        return "unsupported"

    def build_context(self, state: GraphState) -> ExecutionContext:
        """Build shared execution context for routed agents."""
        payload = state.raw_request
        input_source = str(payload.get("input_source", "llm"))
        safety_mode = SafetyMode.READ_ONLY if self.read_only_default else SafetyMode.WRITE_ALLOWED

        return ExecutionContext(
            request_id=state.request_id,
            trace_id=state.trace_id,
            intent=str(payload.get("intent", payload.get("query", ""))),
            input_source=input_source,
            payload=dict(payload.get("payload", {})),
            safety_mode=safety_mode,
        )

    def route_capability(self, state: GraphState) -> str:
        """Return target route name for deterministic execution."""
        if state.normalized_intent == "analysis":
            return "analysis"
        if state.normalized_intent == "schema":
            return "schema"
        if state.normalized_intent == "mixed":
            return "mixed"
        return "unsupported"

    def execute_route(self, state: GraphState) -> None:
        """Execute routed agents based on intent classification."""
        if state.context is None:
            state.errors.append("missing execution context")
            return

        if state.route == "unsupported":
            state.warnings.append("No supported route for this request")
            return

        if state.route == "analysis":
            self._run_single_capability(state, Capability.ANALYSIS)
            return

        if state.route == "schema":
            # If no prior analysis signal is present, enforce analysis first.
            if "analysis_result" not in state.context.payload:
                self._run_single_capability(state, Capability.ANALYSIS, force_fallback=True)
            self._run_single_capability(state, Capability.SCHEMA)
            return

        if state.route == "mixed":
            self._run_single_capability(state, Capability.ANALYSIS)
            self._run_single_capability(state, Capability.SCHEMA)

    def execute_tool_calls(self, state: GraphState) -> None:
        """Run optional safe tool calls and attach results to context payload."""
        if state.context is None:
            return

        tool_calls = state.raw_request.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            return

        bridge = self.tool_bridge
        if bridge is None:
            from adobe_experience.agent.tool_bridge import LLMToolBridge

            bridge = LLMToolBridge()

        with self.tracer.span(
            "supervisor.execute_tool_calls",
            inputs={"tool_calls": tool_calls},
            metadata={"request_id": state.request_id},
            run_type="tool",
        ) as span:
            results = bridge.execute(tool_calls)
            span.set_outputs(
                {
                    "tool_result_count": len(results),
                    "failed": len([x for x in results if isinstance(x, dict) and not x.get("success", False)]),
                }
            )
        state.context.payload["tool_results"] = results

        if any(not item.get("success", False) for item in results if isinstance(item, dict)):
            state.warnings.append("One or more tool calls failed during pre-routing context collection")

    def _run_single_capability(
        self,
        state: GraphState,
        capability: Capability,
        force_fallback: bool = False,
    ) -> None:
        """Run one agent selected by capability."""
        assert state.context is not None
        candidates = self.registry.match(state.context, capability=capability)
        if force_fallback and not candidates:
            candidates = self.registry.list_agents(capability=capability)
        if not candidates:
            state.warnings.append(f"No agent registered for capability: {capability.value}")
            return

        agent = candidates[0]
        
        if self.verbose and self.console:
            self.console.print(f"\n[bold cyan]🤖 Executing Agent:[/bold cyan] {agent.name}")
            self.console.print(f"   [dim]Capability: {capability.value}[/dim]")
        
        with self.tracer.span(
            "supervisor.run_agent",
            inputs={"agent": agent.name, "capability": capability.value},
            metadata={"request_id": state.request_id},
            run_type="chain",
        ) as span:
            state.selected_agents.append(agent.name)
            result = agent.execute(state.context)
            state.results[agent.name] = result
            
            if self.verbose and self.console:
                status_icon = "✓" if result.status == AgentResultStatus.SUCCESS else ("⚠" if result.status == AgentResultStatus.WARNING else "✗")
                status_color = "green" if result.status == AgentResultStatus.SUCCESS else ("yellow" if result.status == AgentResultStatus.WARNING else "red")
                confidence_color = "green" if result.confidence >= 0.7 else ("yellow" if result.confidence >= 0.5 else "red")
                
                self.console.print(f"   [bold {status_color}]{status_icon} Status:[/bold {status_color}] {result.status.value}")
                self.console.print(f"   [bold]Confidence:[/bold] [{confidence_color}]{result.confidence:.2f}[/{confidence_color}]")
                self.console.print(f"   [bold]Summary:[/bold] {result.summary}")
                
                # Show key metrics from structured output
                if result.structured_output:
                    record_count = result.structured_output.get("record_count")
                    field_count = result.structured_output.get("field_count")
                    xdm_class = result.structured_output.get("xdm_class")
                    
                    if record_count is not None:
                        self.console.print(f"   [dim]Records analyzed: {record_count}[/dim]")
                    if field_count is not None:
                        self.console.print(f"   [dim]Fields detected: {field_count}[/dim]")
                    if xdm_class:
                        self.console.print(f"   [dim]Recommended XDM class: {xdm_class}[/dim]")
                
                if result.warnings:
                    for warning in result.warnings:
                        self.console.print(f"   [yellow]⚠  {warning}[/yellow]")
            
            span.set_outputs(
                {
                    "status": result.status.value,
                    "confidence": result.confidence,
                    "warning_count": len(result.warnings),
                }
            )

    def merge_results(self, state: GraphState) -> None:
        """Aggregate results and confidence from all executed agents."""
        if not state.results:
            state.confidence = 0.0
            return

        confidences: List[float] = []
        for agent_name, result in state.results.items():
            confidences.append(result.confidence)
            for artifact in result.artifacts:
                state.artifacts[f"{agent_name}:{artifact}"] = artifact
            state.next_actions.extend(result.next_actions)
            state.warnings.extend(result.warnings)

        state.confidence = sum(confidences) / len(confidences)

    def apply_confidence_gate(self, state: GraphState) -> None:
        """Apply confidence thresholds for warning/fallback behavior.
        
        Confidence Interpretation:
        - < 0.5 (LOW): Results uncertain, fallback recommended
        - 0.5-0.7 (MEDIUM): Results reasonable but need verification
        - >= 0.7 (HIGH): Results reliable, safe for automation
        
        The supervisor aggregates individual agent confidence scores (average)
        and applies these gates to guide downstream decision-making.
        """
        if state.confidence < 0.5:
            state.warnings.append("Low confidence (<0.5): safe fallback recommended")
            return
        if state.confidence < 0.7:
            state.warnings.append("Medium confidence (0.5-0.7): verify recommendations")

    def finalize_response(self, state: GraphState) -> None:
        """Build a final summary line suitable for CLI and LLM output."""
        if not state.results:
            state.final_summary = "No executable agent path found"
            return

        statuses = [result.status for result in state.results.values()]
        if any(status == AgentResultStatus.FAILED for status in statuses):
            summary_status = "partial_failure"
        elif any(status == AgentResultStatus.WARNING for status in statuses):
            summary_status = "warning"
        else:
            summary_status = "success"

        state.final_summary = (
            f"route={state.route}, agents={','.join(state.selected_agents)}, "
            f"status={summary_status}, confidence={state.confidence:.2f}"
        )
