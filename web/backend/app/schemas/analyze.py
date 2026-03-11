"""Analyze API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request for data analysis."""

    intent: str = Field(..., description="Natural language description of analysis intent")
    verbose: bool = Field(default=False, description="Show detailed execution trace")


class AnalysisAgentResult(BaseModel):
    """Single agent execution result."""

    agent_name: str
    status: str
    confidence: float
    summary: str
    warnings: List[str] = []


class AnalyzeResponse(BaseModel):
    """Response from data analysis."""

    analysis_id: str = Field(..., description="Unique analysis ID (timestamp-based)")
    route: str = Field(..., description="Route taken: analysis|schema|mixed|unsupported")
    agents: List[str] = Field(..., description="List of agents executed")
    confidence: float = Field(..., description="Overall confidence score (0.0-1.0)")
    warnings: List[str] = Field(default_factory=list, description="Warnings from agents or supervisor")
    summary: str = Field(..., description="High-level summary of analysis")
    json_path: str = Field(..., description="Path to saved JSON result file")
    md_path: str = Field(..., description="Path to saved Markdown report file")
    agent_results: List[AnalysisAgentResult] = Field(default_factory=list, description="Individual agent results")
    verbose_output: Optional[str] = Field(None, description="Verbose execution trace (if verbose=true)")
    created_at: datetime


class AnalysisResultDetail(BaseModel):
    """Detailed analysis result with structured data."""

    analysis_id: str
    route: str
    agents: List[str]
    confidence: float
    warnings: List[str]
    summary: str
    structured_output: dict = Field(default_factory=dict, description="Raw structured output from agents")
    created_at: datetime


class MarkdownContent(BaseModel):
    """Markdown file content."""

    content: str = Field(..., description="Markdown file content")
    filename: str
