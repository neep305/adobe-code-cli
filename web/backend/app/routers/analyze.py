"""Data analysis API router."""

import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path for importing CLI modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from adobe_experience.agent.registry import AgentRegistry
from adobe_experience.agent.supervisor_graph import SupervisorGraphRunner
from adobe_experience.core.config import get_config

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.analyze import (
    AnalysisAgentResult,
    AnalyzeResponse,
    MarkdownContent,
)

router = APIRouter()


def _load_records_from_file(file_content: bytes, filename: str) -> list:
    """Load records from uploaded file (JSON or CSV)."""
    content_str = file_content.decode("utf-8")
    
    if filename.endswith(".json"):
        data = json.loads(content_str)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            raise ValueError("JSON must be array of objects or single object")
    
    elif filename.endswith(".csv"):
        import csv
        reader = csv.DictReader(io.StringIO(content_str))
        return list(reader)
    
    else:
        raise ValueError("Unsupported file format. Use .json or .csv")


@router.post("/run", response_model=AnalyzeResponse)
async def run_analysis(
    file: UploadFile = File(...),
    intent: str = Form(...),
    verbose: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """Run supervisor-based data analysis on uploaded file.
    
    Args:
        file: JSON or CSV file containing sample records
        intent: Natural language description of analysis intent
        verbose: Show detailed agent execution trace
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Analysis results with paths to saved files
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a name"
        )
    
    if not (file.filename.endswith(".json") or file.filename.endswith(".csv")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON and CSV files are supported"
        )
    
    # Read file content
    try:
        file_content = await file.read()
        records = _load_records_from_file(file_content, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}"
        )
    
    # Create output directory
    output_dir = Path.cwd() / ".adobe-workspace" / "web-output" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create request for supervisor
    analysis_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    request = {
        "request_id": f"req-{analysis_id}",
        "trace_id": f"trace-{analysis_id}",
        "intent": intent,
        "input_source": "file",
        "payload": {
            "records": records,
            "filename": file.filename,
        },
    }
    
    # Run supervisor analysis
    # Note: verbose output capture would require custom console handler
    # For now, we just pass verbose flag but don't capture output
    registry = AgentRegistry()
    runner = SupervisorGraphRunner(registry, verbose=False)  # Backend doesn't capture verbose output yet
    state = runner.run(request)
    
    # Save results to files
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    json_path = output_dir / f"analysis_{timestamp}.json"
    md_path = output_dir / f"analysis_{timestamp}.md"
    
    # Save JSON
    json_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    
    # Generate Markdown report
    md_content = _generate_markdown_report(state, file.filename)
    md_path.write_text(md_content, encoding="utf-8")
    
    # Build agent results
    agent_results = []
    for agent_name, result in state.results.items():
        agent_results.append(
            AnalysisAgentResult(
                agent_name=agent_name,
                status=result.status.value,
                confidence=result.confidence,
                summary=result.summary,
                warnings=result.warnings,
            )
        )
    
    return AnalyzeResponse(
        analysis_id=analysis_id,
        route=state.route,
        agents=state.selected_agents,
        confidence=state.confidence,
        warnings=state.warnings,
        summary=state.final_summary or "Analysis complete",
        json_path=str(json_path.relative_to(Path.cwd())),
        md_path=str(md_path.relative_to(Path.cwd())),
        agent_results=agent_results,
        verbose_output=None,  # TODO: Implement verbose output capture
        created_at=datetime.utcnow(),
    )


@router.get("/results/{analysis_id}/markdown", response_model=MarkdownContent)
async def get_markdown_content(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
) -> MarkdownContent:
    """Get markdown report content for an analysis.
    
    Args:
        analysis_id: Analysis ID (timestamp)
        current_user: Current authenticated user
        
    Returns:
        Markdown file content
    """
    # Find markdown file by analysis_id pattern
    output_dir = Path.cwd() / ".adobe-workspace" / "web-output" / "analysis"
    
    # Try to find file with analysis_id in name
    md_files = list(output_dir.glob(f"analysis_{analysis_id}*.md"))
    
    if not md_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Markdown file not found for analysis {analysis_id}"
        )
    
    md_file = md_files[0]
    
    try:
        content = md_file.read_text(encoding="utf-8")
        return MarkdownContent(
            content=content,
            filename=md_file.name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read markdown file: {str(e)}"
        )


def _generate_markdown_report(state, filename: str) -> str:
    """Generate markdown report from analysis state."""
    lines = [
        f"# Data Analysis Report",
        f"",
        f"**File**: {filename}  ",
        f"**Analysis ID**: {state.request_id}  ",
        f"**Route**: {state.route}  ",
        f"**Confidence**: {state.confidence:.2f}  ",
        f"**Created**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"",
        f"## Summary",
        f"",
        f"{state.final_summary or 'Analysis complete'}",
        f"",
        f"## Agents Executed",
        f"",
    ]
    
    for agent_name in state.selected_agents:
        lines.append(f"- **{agent_name}**")
    
    lines.extend([
        f"",
        f"## Results",
        f"",
    ])
    
    for agent_name, result in state.results.items():
        lines.extend([
            f"### {agent_name}",
            f"",
            f"- **Status**: {result.status.value}",
            f"- **Confidence**: {result.confidence:.2f}",
            f"- **Summary**: {result.summary}",
            f"",
        ])
        
        if result.warnings:
            lines.append(f"**Warnings**:")
            for warning in result.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        
        # Include key structured output
        if result.structured_output:
            lines.append(f"**Key Findings**:")
            
            record_count = result.structured_output.get("record_count")
            field_count = result.structured_output.get("field_count")
            xdm_class = result.structured_output.get("xdm_class")
            identity = result.structured_output.get("identity")
            
            if record_count is not None:
                lines.append(f"- Records analyzed: {record_count}")
            if field_count is not None:
                lines.append(f"- Fields detected: {field_count}")
            if xdm_class:
                class_name = xdm_class.get("name") if isinstance(xdm_class, dict) else xdm_class
                lines.append(f"- Recommended XDM class: {class_name}")
            if identity:
                namespace = identity.get("namespace") if isinstance(identity, dict) else identity
                lines.append(f"- Identity namespace: {namespace}")
            
            lines.append("")
    
    if state.warnings:
        lines.extend([
            f"## Warnings",
            f"",
        ])
        for warning in state.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    return "\n".join(lines)
