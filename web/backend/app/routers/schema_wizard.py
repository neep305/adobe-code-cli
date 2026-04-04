"""Schema Wizard API router — step-by-step XDM schema design with agent validation."""

from __future__ import annotations

import io
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

# Add project src/ to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.schemas.schema_wizard import (
    FinalizeInput,
    FinalizeResult,
    SessionResponse,
    Step1Input,
    Step2Input,
    Step3Input,
    Step4Input,
    Step5Input,
    Step6Input,
    StepResult,
    StepState,
    WizardSession,
)
from app.websockets.schema_wizard_ws import broadcast_wizard_event

router = APIRouter()

# ── In-memory session store (keyed by session_id) ────────────────────────────
# For production, replace with Redis or a DB-backed store.
_sessions: Dict[str, WizardSession] = {}

STEP_INPUT_MODELS = {
    1: Step1Input,
    2: Step2Input,
    3: Step3Input,
    4: Step4Input,
    5: Step5Input,
    6: Step6Input,
}


def _get_session(session_id: str) -> WizardSession:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")
    return session


def _load_records(file_content: bytes, filename: str) -> list:
    text = file_content.decode("utf-8")
    if filename.endswith(".json"):
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    elif filename.endswith(".csv"):
        import csv
        return list(csv.DictReader(io.StringIO(text)))
    raise ValueError(f"Unsupported file type: {filename}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Create a new schema wizard session and return the session_id."""
    session_id = str(uuid.uuid4())
    session = WizardSession(session_id=session_id)
    _sessions[session_id] = session
    return _session_to_response(session)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Get full wizard session state."""
    return _session_to_response(_get_session(session_id))


@router.post("/sessions/{session_id}/steps/{phase}", response_model=StepResult)
async def submit_step(
    session_id: str,
    phase: int,
    # Step 1 can also include a file upload
    file: Optional[UploadFile] = File(None),
    step_data: str = Form("{}"),
    current_user: User = Depends(get_current_user),
) -> StepResult:
    """Submit user input for a wizard phase and trigger agent analysis.

    The response includes checklist statuses and agent recommendations.
    Real-time progress is streamed via WS /ws/schema-wizard/{session_id}.

    Args:
        session_id: Wizard session ID
        phase: Phase number (1-6)
        file: Optional file upload (required for phase 1 with mode=file)
        step_data: JSON-encoded step input (Step1Input, Step2Input, etc.)
    """
    if phase < 1 or phase > 6:
        raise HTTPException(status_code=400, detail="Phase must be 1-6")

    session = _get_session(session_id)

    # Parse step_data JSON
    try:
        raw_input: Dict[str, Any] = json.loads(step_data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid step_data JSON: {exc}")

    # Load file records for phase 1 file mode
    file_records: Optional[List[Dict[str, Any]]] = None
    if file and file.filename:
        try:
            content = await file.read()
            file_records = _load_records(content, file.filename)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}")

    # Mark step as analyzing
    session.steps[phase] = StepState(phase=phase, status="analyzing")
    session.updated_at = datetime.utcnow()

    # Build orchestrator
    from adobe_experience.agent.schema_wizard_orchestrator import SchemaWizardOrchestrator

    async def _ws_broadcast(sid: str, event: dict) -> None:
        await broadcast_wizard_event(sid, event)

    orchestrator = SchemaWizardOrchestrator(broadcast_fn=_ws_broadcast)

    # Run the phase
    result_dict = await orchestrator.run_phase(
        phase=phase,
        session_id=session_id,
        session_entities=session.entities,
        session_steps={k: v.model_dump() for k, v in session.steps.items()},
        user_input=raw_input,
        file_records=file_records,
    )

    # Persist results back to session
    step_state = StepState(
        phase=phase,
        status="completed",
        user_input=raw_input,
        agent_output=result_dict.get("agent_output", {}),
        checklist=result_dict.get("checklist", []),
        confidence=result_dict.get("confidence", 0.5),
        warnings=result_dict.get("warnings", []),
        recommendations=result_dict.get("recommendations", {}),
    )
    session.steps[phase] = step_state

    # Update session-level state from phase 1 results
    if phase == 1:
        entities = result_dict.get("agent_output", {}).get("entities", [])
        if entities:
            session.entities = entities
        if result_dict.get("erd_mermaid"):
            session.erd_mermaid = result_dict["erd_mermaid"]

    session.current_phase = max(session.current_phase, phase + 1)
    session.updated_at = datetime.utcnow()

    return StepResult(**result_dict)


@router.get("/sessions/{session_id}/steps/{phase}", response_model=StepResult)
async def get_step(
    session_id: str,
    phase: int,
    current_user: User = Depends(get_current_user),
) -> StepResult:
    """Get results for a specific wizard phase."""
    session = _get_session(session_id)
    step = session.steps.get(phase)
    if not step:
        raise HTTPException(status_code=404, detail=f"Phase {phase} not yet submitted")
    return StepResult(
        session_id=session_id,
        phase=phase,
        status=step.status,
        confidence=step.confidence,
        checklist=step.checklist,
        agent_output=step.agent_output,
        recommendations=step.recommendations,
        warnings=step.warnings,
        erd_mermaid=session.erd_mermaid if phase == 1 else None,
    )


@router.post("/sessions/{session_id}/finalize", response_model=FinalizeResult)
async def finalize_session(
    session_id: str,
    body: FinalizeInput,
    current_user: User = Depends(get_current_user),
) -> FinalizeResult:
    """Generate final XDM schema JSON files from all phase outputs.

    Optionally uploads schemas to AEP Schema Registry.

    Args:
        session_id: Wizard session ID
        body: FinalizeInput with upload_to_aep flag and optional output_directory
    """
    session = _get_session(session_id)

    if not session.entities:
        raise HTTPException(status_code=400, detail="No entities found. Complete Phase 1 first.")

    from adobe_experience.agent.schema_wizard_orchestrator import SchemaWizardOrchestrator

    orchestrator = SchemaWizardOrchestrator()

    # Determine tenant_id (default: "myorg")
    tenant_id = "myorg"
    try:
        from adobe_experience.core.config import get_config
        cfg = get_config()
        if cfg.aep_tenant_id:
            tenant_id = cfg.aep_tenant_id
    except Exception:
        pass

    schemas = orchestrator.build_xdm_schemas(
        tenant_id=tenant_id,
        entities=session.entities,
        steps={k: v.model_dump() for k, v in session.steps.items()},
    )

    # Save to local files
    output_dir = Path(body.output_directory) if body.output_directory else (
        Path.cwd() / ".adobe-workspace" / "schema-wizard" / session_id
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    output_files: List[str] = []
    for schema in schemas:
        schema_name = schema.get("title", "schema").lower().replace(" ", "_")
        out_path = output_dir / f"{schema_name}_xdm.json"
        out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        output_files.append(str(out_path))

    # Optional AEP upload
    uploaded_ids: List[str] = []
    warnings: List[str] = []
    if body.upload_to_aep:
        try:
            from adobe_experience.aep.client import AEPClient
            from adobe_experience.core.config import get_config
            from adobe_experience.schema.xdm import XDMSchemaRegistry
            from adobe_experience.schema.models import XDMSchema

            cfg = get_config()
            async with AEPClient(cfg) as aep:
                registry = XDMSchemaRegistry(aep)
                for schema_dict in schemas:
                    try:
                        xdm = XDMSchema(**schema_dict)
                        schema_id = await registry.create_schema(xdm)
                        uploaded_ids.append(schema_id)
                    except Exception as exc:
                        warnings.append(f"스키마 업로드 실패 ({schema_dict.get('title', '?')}): {exc}")
        except Exception as exc:
            warnings.append(f"AEP 연결 실패: {exc}")

    return FinalizeResult(
        session_id=session_id,
        schemas=schemas,
        output_files=output_files,
        uploaded_schema_ids=uploaded_ids,
        warnings=warnings,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _session_to_response(session: WizardSession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        current_phase=session.current_phase,
        total_phases=session.total_phases,
        steps=session.steps,
        erd_mermaid=session.erd_mermaid,
        entities=session.entities,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
