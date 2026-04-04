"""Schema Wizard Orchestrator — step-by-step schema design with agent validation."""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Checklist definitions per phase ──────────────────────────────────────────

PHASE_CHECKLISTS: Dict[int, List[Dict[str, str]]] = {
    1: [
        {"id": "p1_entities", "label": "엔티티 목록 파악 (ERD 작성)"},
        {"id": "p1_state_vs_event", "label": "각 엔티티의 성격 파악 (상태 데이터 vs 이벤트 데이터)"},
        {"id": "p1_pii", "label": "PII/민감 데이터 필드 식별"},
        {"id": "p1_source", "label": "데이터 소스별 수집 주기 파악"},
    ],
    2: [
        {"id": "p2_classify", "label": "Profile / ExperienceEvent / Custom 분류 완료"},
        {"id": "p2_uri", "label": "각 스키마의 class URI 결정"},
        {"id": "p2_timestamp", "label": "ExperienceEvent 스키마에 timestamp 필드 포함 확인"},
    ],
    3: [
        {"id": "p3_primary", "label": "Primary Identity 필드 및 Namespace 결정"},
        {"id": "p3_secondary", "label": "Secondary Identity 목록 결정"},
        {"id": "p3_graph", "label": "Identity Graph 전략 선택 (email/crm/device/hybrid)"},
        {"id": "p3_collapse", "label": "공유 식별자 사용 여부 검토 (identity collapse 위험)"},
    ],
    4: [
        {"id": "p4_policy", "label": "시나리오에 맞는 Merge Policy 유형 선택"},
        {"id": "p4_priority", "label": "데이터 소스 우선순위 정의 (Data Source Priority 선택 시)"},
    ],
    5: [
        {"id": "p5_separate", "label": "표준 XDM 필드와 커스텀 필드 분리"},
        {"id": "p5_reuse", "label": "재사용 가능한 Field Group 식별"},
        {"id": "p5_naming", "label": "Field Group ID 네이밍 규칙 결정"},
    ],
    6: [
        {"id": "p6_types", "label": "모든 필드의 XDMDataType / XDMFieldFormat 결정"},
        {"id": "p6_epoch", "label": "epoch timestamp → ISO 8601 변환 계획"},
        {"id": "p6_phone", "label": "phone number → E.164 정규화 계획"},
        {"id": "p6_bool", "label": "boolean variant 변환 규칙 정의"},
    ],
}

# Standard XDM fields that live at root level (not under tenant namespace)
_STANDARD_XDM_FIELDS = {
    "email", "emailaddress", "personalemail", "firstname", "lastname",
    "phone", "mobilephone", "birthdate", "gender",
    "homeaddress", "workaddress", "mailingaddress", "person", "personname",
}

# PII field name patterns
_PII_PATTERNS = re.compile(
    r"(email|phone|mobile|ssn|passport|national_id|dob|birth|address|"
    r"credit_card|card_number|bank_account|tax_id|ip_address|location|geo)",
    re.IGNORECASE,
)

# Suspicious identity fields (risk of identity collapse)
_SHARED_IDENTITY_RISK = re.compile(
    r"^(info|support|admin|noreply|no-reply|contact|help|team|sales)",
    re.IGNORECASE,
)

XDM_CLASS_URIS = {
    "profile": "https://ns.adobe.com/xdm/context/profile",
    "experienceevent": "https://ns.adobe.com/xdm/context/experienceevent",
    "product": "https://ns.adobe.com/xdm/context/product",
    "b2b_account": "https://ns.adobe.com/xdm/context/account",
    "fsi_account": "https://ns.adobe.com/xdm/classes/fsi/account",
}

MERGE_POLICY_DESCRIPTIONS = {
    "timestamp-based": "가장 최근 업데이트 값 우선 — 실시간 이벤트 기반",
    "data-source-priority": "순위가 높은 데이터 소스 우선 — 마스터 데이터 존재 시",
    "last-write-wins": "마지막 쓰기 타임스탬프 기준 전역 적용",
    "data-source-specific": "필드별로 다른 소스 우선 규칙 적용",
}


# ── Helper: build fresh checklist for a phase ────────────────────────────────

def _build_checklist(phase: int) -> List[Dict[str, Any]]:
    return [
        {"id": item["id"], "label": item["label"], "status": "pending", "detail": None}
        for item in PHASE_CHECKLISTS.get(phase, [])
    ]


def _set_check(checklist: List[Dict], item_id: str, status: str, detail: str = "") -> None:
    for item in checklist:
        if item["id"] == item_id:
            item["status"] = status
            item["detail"] = detail
            return


# ── Phase runners ─────────────────────────────────────────────────────────────

class SchemaWizardOrchestrator:
    """Orchestrates the 6-phase schema design wizard, calling existing agents."""

    def __init__(
        self,
        broadcast_fn: Optional[Callable[[str, Dict], Coroutine]] = None,
    ) -> None:
        """
        Args:
            broadcast_fn: Async function(session_id, event_dict) for WebSocket updates.
                          If None, no WS events are emitted.
        """
        self._broadcast = broadcast_fn
        self._sys_path_patched = False
        self._patch_sys_path()

    def _patch_sys_path(self) -> None:
        """Add project src/ to sys.path so adobe_experience can be imported."""
        if self._sys_path_patched:
            return
        src_root = Path(__file__).parent.parent.parent
        src_str = str(src_root)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)
        self._sys_path_patched = True

    async def _emit(self, session_id: str, event: Dict[str, Any]) -> None:
        if self._broadcast:
            try:
                await self._broadcast(session_id, event)
            except Exception as exc:
                logger.warning(f"WS broadcast failed: {exc}")

    # ── Public entry point ────────────────────────────────────────────────────

    async def run_phase(
        self,
        phase: int,
        session_id: str,
        session_entities: List[Dict[str, Any]],
        session_steps: Dict[int, Any],
        user_input: Dict[str, Any],
        file_records: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Run a single wizard phase and return the StepResult dict."""
        await self._emit(session_id, {"event": "analyzing_start", "phase": phase})

        checklist = _build_checklist(phase)
        agent_output: Dict[str, Any] = {}
        recommendations: Dict[str, Any] = {}
        warnings: List[str] = []
        confidence = 0.5
        erd_mermaid: Optional[str] = None

        try:
            if phase == 1:
                agent_output, recommendations, warnings, confidence, erd_mermaid = (
                    await self._run_phase1(
                        session_id, checklist, user_input, file_records
                    )
                )
            elif phase == 2:
                agent_output, recommendations, warnings, confidence = (
                    await self._run_phase2(
                        session_id, checklist, user_input, session_entities,
                        session_steps.get(1, {})
                    )
                )
            elif phase == 3:
                agent_output, recommendations, warnings, confidence = (
                    await self._run_phase3(
                        session_id, checklist, user_input, session_entities,
                        session_steps.get(2, {})
                    )
                )
            elif phase == 4:
                agent_output, recommendations, warnings, confidence = (
                    await self._run_phase4(
                        session_id, checklist, user_input, session_entities,
                        session_steps.get(2, {}), session_steps.get(3, {})
                    )
                )
            elif phase == 5:
                agent_output, recommendations, warnings, confidence = (
                    await self._run_phase5(
                        session_id, checklist, user_input, session_entities,
                        session_steps.get(2, {})
                    )
                )
            elif phase == 6:
                agent_output, recommendations, warnings, confidence = (
                    await self._run_phase6(
                        session_id, checklist, user_input, session_entities
                    )
                )
        except Exception as exc:
            logger.error(f"Phase {phase} failed: {exc}", exc_info=True)
            warnings.append(f"분석 중 오류 발생: {exc}")
            confidence = 0.2
            for item in checklist:
                if item["status"] == "pending":
                    item["status"] = "warning"
                    item["detail"] = "에이전트 오류로 자동 검수 불가"

        await self._emit(
            session_id,
            {
                "event": "step_complete",
                "phase": phase,
                "confidence": confidence,
                "checklist": checklist,
            },
        )

        result: Dict[str, Any] = {
            "session_id": session_id,
            "phase": phase,
            "status": "completed",
            "confidence": confidence,
            "checklist": checklist,
            "agent_output": agent_output,
            "recommendations": recommendations,
            "warnings": warnings,
        }
        if erd_mermaid is not None:
            result["erd_mermaid"] = erd_mermaid
        return result

    # ── Phase 1: ERD 설계 ─────────────────────────────────────────────────────

    async def _run_phase1(
        self,
        session_id: str,
        checklist: List[Dict],
        user_input: Dict[str, Any],
        file_records: Optional[List[Dict[str, Any]]],
    ):
        mode = user_input.get("mode", "domain")
        entities: List[Dict[str, Any]] = []
        erd_mermaid: Optional[str] = None
        warnings: List[str] = []

        await self._emit(session_id, {"event": "checklist_update", "item": "p1_entities", "status": "analyzing"})

        if mode == "mermaid":
            mermaid_text = user_input.get("mermaid_erd", "")
            entities, erd_mermaid = self._parse_mermaid_erd(mermaid_text)

        elif mode == "domain":
            domain_desc = user_input.get("domain_description", "")
            entities, erd_mermaid = await self._generate_erd_from_domain(domain_desc)

        else:  # file mode — records passed via file_records
            records = file_records or []
            entities, erd_mermaid = self._analyze_records_to_erd(records)

        # ── Checklist evaluation ──
        if entities:
            _set_check(checklist, "p1_entities", "passed", f"{len(entities)}개 엔티티 감지")
        else:
            _set_check(checklist, "p1_entities", "failed", "엔티티를 감지하지 못했습니다. 입력을 확인하세요.")
            warnings.append("엔티티를 감지하지 못했습니다.")

        # State vs Event classification
        event_entities = [e for e in entities if e.get("xdm_class_hint") == "experienceevent"]
        profile_entities = [e for e in entities if e.get("xdm_class_hint") == "profile"]
        if entities:
            _set_check(
                checklist, "p1_state_vs_event", "passed",
                f"Profile 후보: {[e['name'] for e in profile_entities]}, "
                f"ExperienceEvent 후보: {[e['name'] for e in event_entities]}"
            )

        # PII detection
        pii_summary = {}
        for entity in entities:
            pii_fields = [
                f["name"] for f in entity.get("fields", [])
                if _PII_PATTERNS.search(f["name"])
            ]
            if pii_fields:
                pii_summary[entity["name"]] = pii_fields
        if pii_summary:
            detail = "; ".join(f"{k}: {v}" for k, v in pii_summary.items())
            _set_check(checklist, "p1_pii", "warning", f"PII 의심 필드 감지: {detail}")
            warnings.append(f"PII 의심 필드가 감지되었습니다: {detail}")
        else:
            _set_check(checklist, "p1_pii", "passed", "명시적 PII 필드 없음 (수동 확인 권장)")

        _set_check(checklist, "p1_source", "warning", "데이터 소스 수집 주기는 수동으로 입력하세요.")

        await self._emit(session_id, {"event": "checklist_update", "item": "p1_entities", "status": "passed"})

        confidence = 0.8 if entities else 0.2
        agent_output = {"entities": entities, "pii_summary": pii_summary}
        recommendations = {"entities": entities, "erd_mermaid": erd_mermaid}
        return agent_output, recommendations, warnings, confidence, erd_mermaid

    # ── Phase 2: XDM 클래스 선택 ─────────────────────────────────────────────

    async def _run_phase2(
        self,
        session_id: str,
        checklist: List[Dict],
        user_input: Dict[str, Any],
        entities: List[Dict[str, Any]],
        step1: Any,
    ):
        await self._emit(session_id, {"event": "checklist_update", "item": "p2_classify", "status": "analyzing"})
        overrides = user_input.get("entity_class_overrides", {})
        warnings: List[str] = []
        entity_classes: Dict[str, Dict[str, str]] = {}
        missing_timestamp: List[str] = []

        for entity in entities:
            name = entity["name"]
            hint = entity.get("xdm_class_hint", "profile")
            chosen = overrides.get(name, hint)
            uri = XDM_CLASS_URIS.get(chosen, XDM_CLASS_URIS["profile"])
            entity_classes[name] = {"class": chosen, "uri": uri}

            # Check ExperienceEvent needs timestamp
            if chosen == "experienceevent":
                field_names = [f["name"].lower() for f in entity.get("fields", [])]
                has_ts = any(
                    kw in fn for fn in field_names
                    for kw in ("timestamp", "time", "date", "created_at", "occurred")
                )
                if not has_ts:
                    missing_timestamp.append(name)

        _set_check(
            checklist, "p2_classify", "passed",
            "; ".join(f"{k}: {v['class']}" for k, v in entity_classes.items())
        )
        _set_check(
            checklist, "p2_uri", "passed",
            "; ".join(f"{k}: {v['uri']}" for k, v in entity_classes.items())
        )

        if missing_timestamp:
            _set_check(
                checklist, "p2_timestamp", "warning",
                f"timestamp 필드 없음: {missing_timestamp} — 반드시 추가하세요."
            )
            warnings.append(f"ExperienceEvent 엔티티에 timestamp 필드가 없습니다: {missing_timestamp}")
        else:
            _set_check(checklist, "p2_timestamp", "passed", "모든 ExperienceEvent에 timestamp 필드 확인")

        confidence = 0.85
        agent_output = {"entity_classes": entity_classes}
        recommendations = {"entity_classes": entity_classes}
        return agent_output, recommendations, warnings, confidence

    # ── Phase 3: Identity 전략 ────────────────────────────────────────────────

    async def _run_phase3(
        self,
        session_id: str,
        checklist: List[Dict],
        user_input: Dict[str, Any],
        entities: List[Dict[str, Any]],
        step2: Any,
    ):
        await self._emit(session_id, {"event": "checklist_update", "item": "p3_primary", "status": "analyzing"})
        overrides_primary = user_input.get("primary_identity_overrides", {})
        overrides_secondary = user_input.get("secondary_identity_overrides", {})
        graph_override = user_input.get("graph_strategy_override")
        warnings: List[str] = []

        entity_classes = {}
        if isinstance(step2, dict):
            entity_classes = step2.get("agent_output", {}).get("entity_classes", {})

        identity_map: Dict[str, Dict[str, Any]] = {}
        for entity in entities:
            name = entity["name"]
            cls = entity_classes.get(name, {}).get("class", "profile")
            fields = entity.get("fields", [])
            field_names = [f["name"].lower() for f in fields]

            primary = overrides_primary.get(name) or self._infer_primary_identity(field_names, cls)
            secondary = overrides_secondary.get(name) or self._infer_secondary_identities(field_names, primary)

            # Check collapse risk
            collapse_risk = False
            if primary and primary.get("field"):
                pf = primary["field"].lower()
                if _SHARED_IDENTITY_RISK.search(pf):
                    collapse_risk = True
                    warnings.append(f"{name}: Primary identity '{pf}'가 공유 식별자일 수 있습니다 (identity collapse 위험).")

            identity_map[name] = {
                "primary": primary,
                "secondary": secondary,
                "collapse_risk": collapse_risk,
            }

        # Graph strategy
        all_namespaces = set()
        for v in identity_map.values():
            if v.get("primary"):
                all_namespaces.add(v["primary"].get("namespace", ""))
        graph_strategy = graph_override or self._infer_graph_strategy(all_namespaces)

        # Checklist
        missing_primary = [k for k, v in identity_map.items() if not v.get("primary")]
        if missing_primary:
            _set_check(checklist, "p3_primary", "failed", f"Primary Identity 미결정: {missing_primary}")
            warnings.append(f"Primary Identity가 설정되지 않은 엔티티: {missing_primary}")
        else:
            _set_check(
                checklist, "p3_primary", "passed",
                "; ".join(f"{k}: {v['primary']['field']}({v['primary']['namespace']})" for k, v in identity_map.items() if v.get("primary"))
            )

        has_secondary = any(v.get("secondary") for v in identity_map.values())
        _set_check(
            checklist, "p3_secondary",
            "passed" if has_secondary else "warning",
            "Secondary Identity 설정됨" if has_secondary else "Secondary Identity 없음 — 크로스 디바이스 연결 불가"
        )
        _set_check(checklist, "p3_graph", "passed", f"전략: {graph_strategy}")

        collapse_risks = [k for k, v in identity_map.items() if v.get("collapse_risk")]
        if collapse_risks:
            _set_check(checklist, "p3_collapse", "warning", f"collapse 위험 엔티티: {collapse_risks}")
        else:
            _set_check(checklist, "p3_collapse", "passed", "공유 식별자 위험 없음")

        confidence = 0.75 if not missing_primary else 0.4
        agent_output = {"identity_map": identity_map, "graph_strategy": graph_strategy}
        recommendations = {"identity_map": identity_map, "graph_strategy": graph_strategy}
        return agent_output, recommendations, warnings, confidence

    # ── Phase 4: Merge Policy ────────────────────────────────────────────────

    async def _run_phase4(
        self,
        session_id: str,
        checklist: List[Dict],
        user_input: Dict[str, Any],
        entities: List[Dict[str, Any]],
        step2: Any,
        step3: Any,
    ):
        await self._emit(session_id, {"event": "checklist_update", "item": "p4_policy", "status": "analyzing"})
        overrides = user_input.get("merge_policy_overrides", {})
        source_priority = user_input.get("source_priority")
        warnings: List[str] = []

        entity_classes = {}
        if isinstance(step2, dict):
            entity_classes = step2.get("agent_output", {}).get("entity_classes", {})
        graph_strategy = "hybrid"
        if isinstance(step3, dict):
            graph_strategy = step3.get("agent_output", {}).get("graph_strategy", "hybrid")

        merge_policies: Dict[str, Dict[str, Any]] = {}
        for entity in entities:
            name = entity["name"]
            cls = entity_classes.get(name, {}).get("class", "profile")
            recommended = overrides.get(name) or self._recommend_merge_policy(cls, graph_strategy)
            merge_policies[name] = {
                "policy": recommended,
                "description": MERGE_POLICY_DESCRIPTIONS.get(recommended, ""),
            }

        _set_check(
            checklist, "p4_policy", "passed",
            "; ".join(f"{k}: {v['policy']}" for k, v in merge_policies.items())
        )

        has_source_priority = any(v["policy"] == "data-source-priority" for v in merge_policies.values())
        if has_source_priority and not source_priority:
            _set_check(checklist, "p4_priority", "warning", "Data Source Priority 선택 시 소스 우선순위 목록을 정의하세요.")
            warnings.append("Data Source Priority 정책이 선택되었지만 우선순위 목록이 없습니다.")
        else:
            _set_check(checklist, "p4_priority", "passed", "소스 우선순위 정의 완료 또는 불필요")

        confidence = 0.80
        agent_output = {"merge_policies": merge_policies, "source_priority": source_priority}
        recommendations = {"merge_policies": merge_policies}
        return agent_output, recommendations, warnings, confidence

    # ── Phase 5: Field Group & Namespace ─────────────────────────────────────

    async def _run_phase5(
        self,
        session_id: str,
        checklist: List[Dict],
        user_input: Dict[str, Any],
        entities: List[Dict[str, Any]],
        step2: Any,
    ):
        await self._emit(session_id, {"event": "checklist_update", "item": "p5_separate", "status": "analyzing"})
        overrides = user_input.get("field_group_overrides", {})
        warnings: List[str] = []

        entity_classes = {}
        if isinstance(step2, dict):
            entity_classes = step2.get("agent_output", {}).get("entity_classes", {})

        field_group_map: Dict[str, Dict[str, Any]] = {}
        for entity in entities:
            name = entity["name"]
            fields = entity.get("fields", [])

            standard_fields = []
            custom_fields = []
            for f in fields:
                if f["name"].lower() in _STANDARD_XDM_FIELDS:
                    standard_fields.append(f["name"])
                else:
                    custom_fields.append(f["name"])

            recommended_fgs = overrides.get(name) or self._recommend_field_groups(fields, entity_classes.get(name, {}).get("class", "profile"))
            field_group_map[name] = {
                "standard_fields": standard_fields,
                "custom_fields": custom_fields,
                "field_groups": recommended_fgs,
            }

        # Checklist
        all_separated = all(
            len(v["standard_fields"]) + len(v["custom_fields"]) > 0
            for v in field_group_map.values()
        )
        _set_check(
            checklist, "p5_separate",
            "passed" if all_separated else "warning",
            "표준/커스텀 필드 분리 완료" if all_separated else "일부 엔티티 필드 정보 없음"
        )

        has_fgs = any(v["field_groups"] for v in field_group_map.values())
        _set_check(
            checklist, "p5_reuse",
            "passed" if has_fgs else "warning",
            "재사용 Field Group 식별 완료" if has_fgs else "표준 Field Group 없음 — 커스텀만 생성"
        )
        _set_check(checklist, "p5_naming", "passed", "_{tenant_id}/fieldgroups/{entity}_fieldgroup 규칙 사용")

        confidence = 0.80
        agent_output = {"field_group_map": field_group_map}
        recommendations = {"field_group_map": field_group_map}
        return agent_output, recommendations, warnings, confidence

    # ── Phase 6: 타입 & 전처리 ────────────────────────────────────────────────

    async def _run_phase6(
        self,
        session_id: str,
        checklist: List[Dict],
        user_input: Dict[str, Any],
        entities: List[Dict[str, Any]],
    ):
        await self._emit(session_id, {"event": "checklist_update", "item": "p6_types", "status": "analyzing"})
        type_overrides = user_input.get("type_overrides", {})
        warnings: List[str] = []

        field_types: Dict[str, Dict[str, Any]] = {}
        epoch_fields: List[str] = []
        phone_fields: List[str] = []
        bool_variant_fields: List[str] = []

        for entity in entities:
            entity_name = entity["name"]
            for field in entity.get("fields", []):
                key = f"{entity_name}.{field['name']}"
                override = type_overrides.get(key)
                detected = field.get("xdm_type", "string")
                detected_format = field.get("xdm_format")

                xdm_type = override.get("type", detected) if override else detected
                xdm_format = override.get("format", detected_format) if override else detected_format

                # Detect preprocessing needs
                fn_lower = field["name"].lower()
                if any(kw in fn_lower for kw in ("timestamp", "created_at", "updated_at")) and detected == "integer":
                    epoch_fields.append(key)
                if any(kw in fn_lower for kw in ("phone", "tel", "mobile", "cell")):
                    phone_fields.append(key)
                if field.get("sample_values") and self._is_boolean_variant(field.get("sample_values", [])):
                    bool_variant_fields.append(key)

                field_types[key] = {"type": xdm_type, "format": xdm_format}

        # Checklist
        _set_check(checklist, "p6_types", "passed", f"{len(field_types)}개 필드 타입 매핑 완료")

        if epoch_fields:
            _set_check(checklist, "p6_epoch", "warning", f"epoch 변환 필요: {epoch_fields[:3]}")
            warnings.append(f"epoch timestamp 필드 변환 필요: {epoch_fields}")
        else:
            _set_check(checklist, "p6_epoch", "passed", "epoch timestamp 필드 없음")

        if phone_fields:
            _set_check(checklist, "p6_phone", "warning", f"E.164 정규화 필요: {phone_fields}")
            warnings.append(f"phone 필드 E.164 정규화 필요: {phone_fields}")
        else:
            _set_check(checklist, "p6_phone", "passed", "phone 필드 없음")

        if bool_variant_fields:
            _set_check(checklist, "p6_bool", "warning", f"boolean 변환 필요: {bool_variant_fields[:3]}")
            warnings.append(f"boolean variant 변환 필요: {bool_variant_fields}")
        else:
            _set_check(checklist, "p6_bool", "passed", "boolean variant 없음")

        confidence = 0.82
        agent_output = {
            "field_types": field_types,
            "epoch_fields": epoch_fields,
            "phone_fields": phone_fields,
            "bool_variant_fields": bool_variant_fields,
        }
        recommendations = {"field_types": field_types}
        return agent_output, recommendations, warnings, confidence

    # ── Finalize: 스키마 JSON 생성 ────────────────────────────────────────────

    def build_xdm_schemas(
        self,
        tenant_id: str,
        entities: List[Dict[str, Any]],
        steps: Dict[int, Any],
    ) -> List[Dict[str, Any]]:
        """Build XDM-compatible schema dicts from all wizard phase outputs."""
        entity_classes = {}
        identity_map = {}
        field_group_map = {}
        field_types = {}

        step2_out = steps.get(2, {})
        if isinstance(step2_out, dict):
            entity_classes = step2_out.get("agent_output", {}).get("entity_classes", {})

        step3_out = steps.get(3, {})
        if isinstance(step3_out, dict):
            identity_map = step3_out.get("agent_output", {}).get("identity_map", {})

        step5_out = steps.get(5, {})
        if isinstance(step5_out, dict):
            field_group_map = step5_out.get("agent_output", {}).get("field_group_map", {})

        step6_out = steps.get(6, {})
        if isinstance(step6_out, dict):
            field_types = step6_out.get("agent_output", {}).get("field_types", {})

        schemas = []
        for entity in entities:
            name = entity["name"]
            cls_info = entity_classes.get(name, {"class": "profile", "uri": XDM_CLASS_URIS["profile"]})
            identity_info = identity_map.get(name, {})
            fg_info = field_group_map.get(name, {"standard_fields": [], "custom_fields": [], "field_groups": []})

            # Build properties
            standard_props: Dict[str, Any] = {}
            custom_props: Dict[str, Any] = {}

            for field in entity.get("fields", []):
                fn = field["name"]
                key = f"{name}.{fn}"
                type_info = field_types.get(key, {})
                xdm_type = type_info.get("type", field.get("xdm_type", "string"))
                xdm_format = type_info.get("format", field.get("xdm_format"))

                prop: Dict[str, Any] = {"type": xdm_type, "title": fn.replace("_", " ").title()}
                if xdm_format:
                    prop["format"] = xdm_format

                # Apply identity descriptor
                primary = identity_info.get("primary", {})
                if primary and primary.get("field") == fn:
                    prop["meta:descriptors"] = [{"@type": "xdm:descriptorIdentity", "xdm:isPrimary": True}]

                if fn.lower() in _STANDARD_XDM_FIELDS:
                    standard_props[fn] = prop
                else:
                    custom_props[fn] = prop

            schema: Dict[str, Any] = {
                "$id": f"https://ns.adobe.com/{tenant_id}/schemas/{name.lower()}",
                "$schema": "http://json-schema.org/draft-06/schema#",
                "title": name,
                "description": f"XDM schema for {name}",
                "meta:class": cls_info.get("uri", XDM_CLASS_URIS["profile"]),
                "allOf": [
                    {"$ref": "http://json-schema.org/draft-06/schema#"},
                    {"$ref": f"#/definitions/_{tenant_id}"},
                ],
                "definitions": {},
                "properties": standard_props,
            }

            if custom_props:
                schema["definitions"][f"_{tenant_id}"] = {
                    "type": "object",
                    "properties": custom_props,
                }

            schemas.append(schema)

        return schemas

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _parse_mermaid_erd(self, mermaid_text: str):
        """Parse Mermaid ERD text using MermaidERDParser if available."""
        try:
            from adobe_experience.schema.erd_parser import MermaidERDParser
            parser = MermaidERDParser()
            entity_defs = parser.parse_erd(mermaid_text)
            entities = []
            for ed in entity_defs:
                fields = [
                    {"name": f.name, "xdm_type": str(f.xdm_type.value if hasattr(f.xdm_type, "value") else f.xdm_type)}
                    for f in (ed.fields if hasattr(ed, "fields") else [])
                ]
                hint = self._guess_xdm_class_hint(ed.name, fields)
                entities.append({"name": ed.name, "fields": fields, "xdm_class_hint": hint})
            return entities, mermaid_text
        except Exception as exc:
            logger.warning(f"MermaidERDParser failed: {exc}. Falling back to regex.")
            return self._parse_mermaid_regex(mermaid_text), mermaid_text

    def _parse_mermaid_regex(self, text: str):
        """Minimal regex-based Mermaid ERD parser as fallback."""
        entities = []
        entity_pattern = re.compile(r"(\w+)\s*\{([^}]+)\}", re.DOTALL)
        field_pattern = re.compile(r"(\w+)\s+(\w+)(?:\s+\w+)?")
        for match in entity_pattern.finditer(text):
            name = match.group(1)
            body = match.group(2)
            fields = [
                {"name": fm.group(2), "xdm_type": self._mermaid_type_to_xdm(fm.group(1))}
                for fm in field_pattern.finditer(body)
            ]
            hint = self._guess_xdm_class_hint(name, fields)
            entities.append({"name": name, "fields": fields, "xdm_class_hint": hint})
        return entities

    async def _generate_erd_from_domain(self, domain_desc: str):
        """Generate ERD from domain description using DomainAnalyzer."""
        try:
            from adobe_experience.schema.domain_analyzer import DomainAnalyzer
            analyzer = DomainAnalyzer()
            erd = await analyzer.generate_erd_from_domain(domain_desc, "", 5)
            entities = []
            mermaid_lines = ["erDiagram"]
            for entity in erd.entities:
                fields = [
                    {"name": f.name, "xdm_type": str(f.xdm_type.value if hasattr(f.xdm_type, "value") else f.xdm_type)}
                    for f in (entity.fields if hasattr(entity, "fields") else [])
                ]
                hint = self._guess_xdm_class_hint(entity.name, fields)
                entities.append({"name": entity.name, "fields": fields, "xdm_class_hint": hint})
                # Build Mermaid snippet
                field_strs = [f"    {f.get('xdm_type','string')} {f['name']}" for f in fields[:10]]
                mermaid_lines.append(f"  {entity.name} {{")
                mermaid_lines.extend(field_strs)
                mermaid_lines.append("  }")
            return entities, "\n".join(mermaid_lines)
        except Exception as exc:
            logger.warning(f"DomainAnalyzer failed: {exc}. Returning empty entities.")
            return [], None

    def _analyze_records_to_erd(self, records: List[Dict[str, Any]]):
        """Infer entity structure from flat records."""
        if not records:
            return [], None
        fields = []
        seen = set()
        for record in records[:20]:
            for k, v in record.items():
                if k not in seen:
                    seen.add(k)
                    xdm_type = self._python_val_to_xdm_type(v)
                    xdm_format = self._infer_format(k, v)
                    fields.append({"name": k, "xdm_type": xdm_type, "xdm_format": xdm_format, "sample_values": [v]})

        entity_name = "DataEntity"
        hint = self._guess_xdm_class_hint(entity_name, fields)
        entity = {"name": entity_name, "fields": fields, "xdm_class_hint": hint}

        mermaid = f"erDiagram\n  {entity_name} {{\n"
        for f in fields[:10]:
            mermaid += f"    {f['xdm_type']} {f['name']}\n"
        mermaid += "  }"
        return [entity], mermaid

    def _guess_xdm_class_hint(self, name: str, fields: List[Dict]) -> str:
        name_lower = name.lower()
        event_keywords = {"event", "log", "activity", "action", "click", "purchase", "order", "session", "view", "interaction"}
        if any(kw in name_lower for kw in event_keywords):
            return "experienceevent"
        field_names = {f["name"].lower() for f in fields}
        if "timestamp" in field_names or "event_id" in field_names:
            return "experienceevent"
        return "profile"

    def _infer_primary_identity(self, field_names: List[str], cls: str) -> Optional[Dict[str, str]]:
        if cls == "experienceevent":
            for fn in field_names:
                if "ecid" in fn:
                    return {"field": fn, "namespace": "ECID"}
        for fn in field_names:
            if "email" in fn:
                return {"field": fn, "namespace": "Email"}
        for fn in field_names:
            if "crm" in fn or "customer_id" in fn or "user_id" in fn:
                return {"field": fn, "namespace": "CRM_ID"}
        return None

    def _infer_secondary_identities(self, field_names: List[str], primary: Optional[Dict]) -> List[Dict[str, str]]:
        secondary = []
        primary_field = primary.get("field", "") if primary else ""
        for fn in field_names:
            if fn == primary_field:
                continue
            if "phone" in fn or "mobile" in fn:
                secondary.append({"field": fn, "namespace": "Phone"})
            elif "ecid" in fn:
                secondary.append({"field": fn, "namespace": "ECID"})
        return secondary

    def _infer_graph_strategy(self, namespaces: set) -> str:
        if "Email" in namespaces and "CRM_ID" in namespaces:
            return "hybrid"
        if "Email" in namespaces:
            return "email-based"
        if "CRM_ID" in namespaces:
            return "crm-based"
        if "ECID" in namespaces:
            return "device-graph"
        return "hybrid"

    def _recommend_merge_policy(self, cls: str, graph_strategy: str) -> str:
        if cls == "experienceevent":
            return "timestamp-based"
        if graph_strategy in ("crm-based",):
            return "data-source-priority"
        return "timestamp-based"

    def _recommend_field_groups(self, fields: List[Dict], cls: str) -> List[str]:
        groups = []
        field_names = {f["name"].lower() for f in fields}
        if any(kw in fn for fn in field_names for kw in ("email", "phone", "address")):
            groups.append("Personal Contact Details")
        if any(kw in fn for fn in field_names for kw in ("birth", "gender", "age")):
            groups.append("Demographic Details")
        if any(kw in fn for fn in field_names for kw in ("loyalty", "tier", "points")):
            groups.append("Loyalty Details")
        if cls == "experienceevent":
            groups.append("Web Details")
        return groups

    def _mermaid_type_to_xdm(self, mermaid_type: str) -> str:
        mapping = {
            "string": "string", "varchar": "string", "text": "string",
            "int": "integer", "integer": "integer", "bigint": "integer",
            "float": "number", "double": "number", "decimal": "number",
            "boolean": "boolean", "bool": "boolean",
            "date": "date", "datetime": "date-time", "timestamp": "date-time",
        }
        return mapping.get(mermaid_type.lower(), "string")

    def _python_val_to_xdm_type(self, val: Any) -> str:
        if isinstance(val, bool):
            return "boolean"
        if isinstance(val, int):
            return "integer"
        if isinstance(val, float):
            return "number"
        if isinstance(val, dict):
            return "object"
        if isinstance(val, list):
            return "array"
        return "string"

    def _infer_format(self, field_name: str, value: Any) -> Optional[str]:
        fn = field_name.lower()
        if "email" in fn or (isinstance(value, str) and "@" in value):
            return "email"
        if "url" in fn or "uri" in fn or (isinstance(value, str) and value.startswith("http")):
            return "uri"
        if any(kw in fn for kw in ("timestamp", "created_at", "updated_at")):
            return "date-time"
        if "date" in fn:
            return "date"
        return None

    def _is_boolean_variant(self, values: List[Any]) -> bool:
        bool_variants = {"0", "1", "yes", "no", "true", "false", "on", "off", "enabled", "disabled"}
        str_vals = {str(v).lower() for v in values if v is not None}
        return bool(str_vals and str_vals.issubset(bool_variants))
