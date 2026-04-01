"""Bridge between supervisor graph and LLM-safe CLI tools."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional


class LLMToolBridge:
    """Execute safe LLM tool calls and return normalized results."""

    def __init__(self) -> None:
        self._executor = None

    def execute(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls and return serializable execution results."""
        if not tool_calls:
            return []

        executor = self._ensure_executor()
        if executor is None:
            return [
                {
                    "tool_name": "<bridge>",
                    "success": False,
                    "error": "LLM tool bridge unavailable (missing optional dependencies)",
                }
            ]

        results: List[Dict[str, Any]] = []
        for call in tool_calls:
            tool_name = str(call.get("name", "")).strip()
            parameters = call.get("parameters", {})
            if not tool_name:
                results.append(
                    {
                        "tool_name": "<unknown>",
                        "success": False,
                        "error": "Tool call missing 'name'",
                    }
                )
                continue

            if not isinstance(parameters, dict):
                parameters = {}

            try:
                execution = asyncio.run(executor.execute_tool(tool_name, parameters))
                results.append(
                    {
                        "tool_name": tool_name,
                        "success": execution.success,
                        "output": execution.output,
                        "error": execution.error,
                        "error_code": execution.error_code,
                        "suggestion": execution.suggestion,
                        "execution_time_seconds": execution.execution_time_seconds,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "tool_name": tool_name,
                        "success": False,
                        "error": str(exc),
                    }
                )

        return results

    def _ensure_executor(self):
        if self._executor is not None:
            return self._executor

        try:
            from adobe_experience.cli.llm_tools import (
                CommandExecutor,
                ToolRegistry,
                register_safe_tools,
            )
            from adobe_experience.core.config import get_config

            registry = ToolRegistry()
            register_safe_tools(registry)
            self._executor = CommandExecutor(registry, get_config())
            return self._executor
        except Exception:
            return None