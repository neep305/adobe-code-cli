"""Onboarding status API router."""

import asyncio
import json
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import OnboardingProgress, User
from app.config import get_settings
from app.onboarding_completion import detect_all_step_completion
from app.onboarding_definitions import PHASE_DEFINITIONS, STEP_DEFINITIONS, all_step_keys
from app.schemas.onboarding import (
    OnboardingPhaseSummary,
    OnboardingPlanRequest,
    OnboardingPlanResponse,
    OnboardingProgressUpdate,
    OnboardingStatusResponse,
    OnboardingStepStatus,
)

router = APIRouter()


def _build_phase_summaries(steps: List[OnboardingStepStatus]) -> List[OnboardingPhaseSummary]:
    by_phase: dict[str, List[OnboardingStepStatus]] = {}
    for s in steps:
        by_phase.setdefault(s.phase_id, []).append(s)
    out: List[OnboardingPhaseSummary] = []
    for p in sorted(PHASE_DEFINITIONS, key=lambda x: x["order"]):
        pid = p["id"]
        phase_steps = by_phase.get(pid, [])
        total = len(phase_steps)
        done = sum(1 for x in phase_steps if x.completed)
        prog = done / total if total else 0.0
        out.append(
            OnboardingPhaseSummary(
                id=pid,
                title=p["title"],
                description=p["description"],
                order=p["order"],
                depends_on=list(p["depends_on"]),
                completed_count=done,
                total_count=total,
                progress=prog,
            )
        )
    return out


def _manual_completion_label(step_key: str) -> Optional[str]:
    if step_key == "source":
        return "Connection confirmed"
    if step_key == "dataset":
        return "Catalog reviewed"
    if step_key == "profile_ready":
        return "Profile readiness confirmed"
    if step_key == "segment":
        return "Audience confirmed"
    if step_key == "destination":
        return "Destination activation confirmed"
    return None


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Get onboarding progress status for the current user.

    Automatically detects completed steps based on existing resources.
    Merges with OnboardingProgress.completed_steps for manual completion.
    """
    completion = await detect_all_step_completion(current_user, db)

    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.user_id == current_user.id)
    )
    progress = progress_result.scalar_one_or_none()
    manual_keys: set[str] = set()
    if progress and progress.completed_steps:
        try:
            raw = json.loads(progress.completed_steps)
            if isinstance(raw, list):
                manual_keys = {str(x) for x in raw}
        except json.JSONDecodeError:
            manual_keys = set()

    steps = []
    for step_def in STEP_DEFINITIONS:
        key = step_def["key"]
        auto_done, resource_id, resource_name = completion.get(key, (False, None, None))
        manual_marked = key in manual_keys
        completed = auto_done or manual_marked
        if manual_marked and not auto_done:
            label_manual = _manual_completion_label(key)
            resource_name = resource_name or label_manual or "Marked complete manually"
        steps.append(
            OnboardingStepStatus(
                key=key,
                phase_id=step_def["phase_id"],
                label=step_def["label"],
                description=step_def["description"],
                completed=completed,
                cli_only=step_def["cli_only"],
                node_hint=step_def["node_hint"],
                allow_manual_complete=step_def["manual_complete_allowed"],
                manual_marked=manual_marked,
                resource_id=resource_id,
                resource_name=resource_name,
                action_url=step_def["action_url"],
                action_label=step_def["action_label"],
            )
        )

    completed_count = sum(1 for s in steps if s.completed)
    total_count = len(steps)
    phases = _build_phase_summaries(steps)

    return OnboardingStatusResponse(
        steps=steps,
        phases=phases,
        completed_count=completed_count,
        total_count=total_count,
        overall_progress=completed_count / total_count if total_count > 0 else 0.0,
    )


@router.put("/progress", response_model=OnboardingStatusResponse)
async def update_onboarding_progress(
    body: OnboardingProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Manually mark an onboarding step as complete or incomplete."""
    valid_keys = all_step_keys()
    if body.step_key not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Unknown step key: {body.step_key}")

    # Upsert OnboardingProgress
    progress_result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.user_id == current_user.id)
    )
    progress = progress_result.scalar_one_or_none()

    if progress is None:
        progress = OnboardingProgress(user_id=current_user.id)
        db.add(progress)

    completed_steps: list = json.loads(progress.completed_steps or "[]")
    if body.completed and body.step_key not in completed_steps:
        completed_steps.append(body.step_key)
    elif not body.completed and body.step_key in completed_steps:
        completed_steps.remove(body.step_key)
    progress.completed_steps = json.dumps(completed_steps)

    await db.commit()

    return await get_onboarding_status(current_user, db)


def _rule_onboarding_plan(
    user_text: str,
    steps: List[OnboardingStepStatus],
) -> OnboardingPlanResponse:
    """Keyword-based onboarding guidance when LLM is unavailable."""
    t = user_text.lower()
    next_actionable = next((s for s in steps if not s.completed), None)

    def step_by_key(k: str) -> Optional[OnboardingStepStatus]:
        return next((s for s in steps if s.key == k), None)

    suggested: Optional[OnboardingStepStatus] = None
    reply_lines: list[str] = []

    if any(x in t for x in ("schema", "스키마", "xdm")):
        suggested = step_by_key("schema")
        reply_lines.append(
            "Create or refine schemas on the Schemas page using sample CSV/JSON drafts, then review before AEP."
        )
    elif any(x in t for x in ("auth", "자격", "credential", "인증", "sandbox", "설정")):
        suggested = step_by_key("auth")
        reply_lines.append("Register AEP API credentials under Settings in this app.")
    elif any(x in t for x in ("source", "s3", "sftp", "소스", "blob", "connector")):
        suggested = step_by_key("source")
        reply_lines.append(
            "Connect a source account in Experience Platform **Sources** (pick a connector, then create an account). "
            "When finished, use Confirm source connection in onboarding."
        )
    elif any(x in t for x in ("dataflow", "데이터플로우", "파이프라인", "매핑", "ingestion", "add data")):
        suggested = step_by_key("dataflow")
        reply_lines.append(
            "The ingestion wizard in **Sources** continues from your connection: add data, map fields, "
            "pick or create a dataset, then schedule."
        )
    elif any(x in t for x in ("dataset", "데이터셋", "catalog")):
        suggested = step_by_key("dataset")
        reply_lines.append(
            "Use **Datasets** to create a Catalog dataset or verify settings for one created in the wizard."
        )
    elif any(x in t for x in ("upload", "batch", "수집", "ingest", "업로드", "monitoring")):
        suggested = step_by_key("ingest")
    elif any(
        x in t
        for x in (
            "merge policy",
            "merge",
            "identity graph",
            "profile readiness",
            "stitching",
            "프로필",
            "아이덴티티",
            "병합",
        )
    ):
        suggested = step_by_key("profile_ready")
        reply_lines.append(
            "Confirm merge policies and identity behavior in Experience Platform **Profiles** / **Identities**, "
            "then mark **Profile readiness** when data stitches as expected."
        )
    elif any(
        x in t
        for x in (
            "segment",
            "audience",
            "audiences",
            "세그먼트",
            "오디언스",
        )
    ):
        suggested = step_by_key("segment")
        reply_lines.append(
            "Define or verify **Segments** in Experience Platform, run evaluation, then confirm **Audiences** "
            "in onboarding when satisfied."
        )
    elif any(
        x in t
        for x in (
            "destination",
            "destinations",
            "activation",
            "activate",
            "보내기",
            "대상",
        )
    ):
        suggested = step_by_key("destination")
        reply_lines.append(
            "Set up a **Destination** and activation dataflow in Experience Platform, verify the first delivery, "
            "then confirm **Destinations & activation** here."
        )

    if suggested is None:
        if next_actionable:
            suggested = next_actionable
            reply_lines.append(f"Recommended next step: {next_actionable.label}.")
        else:
            reply_lines.append("All onboarding steps look complete.")

    follow = [
        "Have you already saved AEP credentials in Settings?",
        "Is your sample data CSV or JSON?",
    ]

    return OnboardingPlanResponse(
        reply=" ".join(reply_lines) if reply_lines else "How can I help?",
        suggested_step_key=suggested.key if suggested else None,
        action_url=suggested.action_url if suggested else None,
        action_label=suggested.action_label if suggested else None,
        follow_up_questions=follow,
        used_llm=False,
    )


def _claude_onboarding_plan_sync(user_text: str, steps_summary: str) -> dict:
    """Call Anthropic once; return parsed dict or {}."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return {}
    try:
        import anthropic
    except ImportError:
        return {}

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    msg = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are an Adobe Experience Platform onboarding assistant.\n"
                    f"Pipeline steps (JSON):\n{steps_summary}\n\n"
                    f"User message:\n{user_text}\n\n"
                    "Respond with ONLY valid JSON: "
                    '{"reply":"short paragraph in English",'
                    '"suggested_step_key":"auth|schema|source|dataflow|dataset|ingest|'
                    'profile_ready|segment|destination or null",'
                    '"follow_up_questions":["q1","q2"]}'
                ),
            }
        ],
    )
    text = ""
    for block in msg.content:
        if block.type == "text":
            text += block.text
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {}
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return {}


@router.post("/plan", response_model=OnboardingPlanResponse)
async def onboarding_plan_chat(
    body: OnboardingPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingPlanResponse:
    """Conversational Plan-mode guidance; uses Claude when ANTHROPIC_API_KEY is set."""
    status = await get_onboarding_status(current_user, db)
    last_user = ""
    for m in reversed(body.messages):
        if m.role == "user":
            last_user = m.content.strip()
            break

    if not last_user:
        return OnboardingPlanResponse(
            reply="Describe your goal in one sentence (e.g. I want to build a profile schema).",
            follow_up_questions=[
                "Is this profile data or event data?",
                "Do you have a sample file ready?",
            ],
        )

    steps_summary = json.dumps(
        [
            {
                "key": s.key,
                "phase_id": s.phase_id,
                "label": s.label,
                "done": s.completed,
                "cli_only": s.cli_only,
            }
            for s in status.steps
        ]
    )
    settings = get_settings()

    if settings.anthropic_api_key:
        raw = await asyncio.to_thread(_claude_onboarding_plan_sync, last_user, steps_summary)
        if raw.get("reply"):
            sk = raw.get("suggested_step_key")
            step = next((s for s in status.steps if s.key == sk), None) if sk else None
            fq = raw.get("follow_up_questions") or []
            if not isinstance(fq, list):
                fq = []
            return OnboardingPlanResponse(
                reply=str(raw["reply"]),
                suggested_step_key=str(sk) if sk else None,
                action_url=step.action_url if step else None,
                action_label=step.action_label if step else None,
                follow_up_questions=[str(x) for x in fq][:5],
                used_llm=True,
            )

    return _rule_onboarding_plan(last_user, status.steps)
