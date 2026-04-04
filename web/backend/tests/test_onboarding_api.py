"""Onboarding status / progress API tests (phased pipeline through activation)."""

import base64

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AEPConfig, Dataset, Schema

EXPECTED_STEP_KEYS = [
    "auth",
    "schema",
    "source",
    "dataflow",
    "dataset",
    "ingest",
    "profile_ready",
    "segment",
    "destination",
]

EXPECTED_PHASE_IDS = [
    "platform_access",
    "data_modeling",
    "collection_landing",
    "profile_readiness",
    "audiences",
    "activation",
]


async def _register_and_headers(client: AsyncClient, login_id: str) -> tuple[dict[str, str], int]:
    reg = await client.post(
        "/api/auth/register",
        json={"login_id": login_id, "password": "pw", "name": "Onb"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    return headers, me.json()["id"]


@pytest.mark.asyncio
async def test_step_order_and_next_after_catalog_ready_is_source(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """With auth, schema, and dataset in DB, first incomplete step is source (3rd)."""
    headers, user_id = await _register_and_headers(client, "onb-next-source")

    secret_b64 = base64.b64encode(b"dummy-secret").decode()
    cfg = AEPConfig(
        user_id=user_id,
        sandbox_name="prod",
        client_id="cid",
        encrypted_client_secret=secret_b64,
        org_id="org",
        technical_account_id="tech",
    )
    db_session.add(cfg)
    sch = Schema(
        user_id=user_id,
        aep_schema_id="xdm-onb-test-1",
        name="schema",
        title="Schema",
        class_id="https://ns.adobe.com/xdm/context/profile",
        definition_json="{}",
    )
    db_session.add(sch)
    await db_session.flush()
    db_session.add(
        Dataset(
            user_id=user_id,
            schema_id=sch.id,
            aep_dataset_id="aep-ds-onb-1",
            name="DS",
        )
    )
    await db_session.commit()

    r = await client.get("/api/onboarding/status", headers=headers)
    assert r.status_code == 200
    body = r.json()
    steps = body["steps"]
    assert [s["key"] for s in steps] == EXPECTED_STEP_KEYS

    assert steps[0]["key"] == "auth" and steps[0]["completed"] is True
    assert steps[0]["phase_id"] == "platform_access"
    assert steps[1]["key"] == "schema" and steps[1]["completed"] is True
    assert steps[1]["phase_id"] == "data_modeling"
    assert steps[2]["key"] == "source" and steps[2]["completed"] is False
    assert steps[2]["phase_id"] == "collection_landing"
    ds_step = next(s for s in steps if s["key"] == "dataset")
    assert ds_step["completed"] is True

    phases = body["phases"]
    assert len(phases) == len(EXPECTED_PHASE_IDS)
    assert [p["id"] for p in sorted(phases, key=lambda x: x["order"])] == EXPECTED_PHASE_IDS
    coll = next(p for p in phases if p["id"] == "collection_landing")
    assert coll["total_count"] == 4
    assert coll["completed_count"] == 1

    first_open = next(s for s in steps if not s["completed"])
    assert first_open["key"] == "source"


@pytest.mark.asyncio
async def test_put_source_complete_next_incomplete_is_dataflow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """After source marked manual complete, first incomplete is dataflow (no AEP flow detected)."""
    headers, user_id = await _register_and_headers(client, "onb-source-put")

    secret_b64 = base64.b64encode(b"dummy-secret").decode()
    db_session.add(
        AEPConfig(
            user_id=user_id,
            sandbox_name="prod",
            client_id="cid",
            encrypted_client_secret=secret_b64,
            org_id="org",
            technical_account_id="tech",
        )
    )
    sch = Schema(
        user_id=user_id,
        aep_schema_id="xdm-onb-test-2",
        name="s",
        title="S",
        class_id="https://ns.adobe.com/xdm/context/profile",
        definition_json="{}",
    )
    db_session.add(sch)
    await db_session.flush()
    db_session.add(
        Dataset(
            user_id=user_id,
            schema_id=sch.id,
            aep_dataset_id="aep-ds-onb-2",
            name="D",
        )
    )
    await db_session.commit()

    put = await client.put(
        "/api/onboarding/progress",
        headers=headers,
        json={"step_key": "source", "completed": True},
    )
    assert put.status_code == 200
    body = put.json()
    steps = body["steps"]
    assert [s["key"] for s in steps] == EXPECTED_STEP_KEYS
    assert len(body["phases"]) == 6

    src = next(s for s in steps if s["key"] == "source")
    assert src["completed"] is True
    assert src["manual_marked"] is True

    first_open = next(s for s in steps if not s["completed"])
    assert first_open["key"] == "dataflow"


@pytest.mark.asyncio
async def test_put_unknown_step_key_400(client: AsyncClient) -> None:
    """Progress API rejects keys not in STEP_DEFINITIONS."""
    headers, _ = await _register_and_headers(client, "onb-bad-step")
    r = await client.put(
        "/api/onboarding/progress",
        headers=headers,
        json={"step_key": "not_a_real_step", "completed": True},
    )
    assert r.status_code == 400
