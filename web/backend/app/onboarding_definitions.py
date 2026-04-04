"""Static onboarding phase and step definitions (AEP journey modules).

Phases map to adobe_experience package boundaries: access, schema, catalog/ingestion/flow,
then profile readiness, segmentation, destinations.
"""

from typing import TypedDict


class PhaseDict(TypedDict):
    id: str
    title: str
    description: str
    order: int
    depends_on: list[str]


class StepDict(TypedDict, total=False):
    key: str
    phase_id: str
    label: str
    description: str
    action_url: str
    action_label: str
    cli_only: bool
    node_hint: str
    manual_complete_allowed: bool


# Linear dependency chain for documentation and UI (each phase may contain multiple steps).
PHASE_DEFINITIONS: list[PhaseDict] = [
    {
        "id": "platform_access",
        "title": "Platform access",
        "description": (
            "Connect this app to Adobe Experience Platform with OAuth Server-to-Server credentials "
            "and a sandbox."
        ),
        "order": 0,
        "depends_on": [],
    },
    {
        "id": "data_modeling",
        "title": "Data modeling",
        "description": (
            "Define the XDM contract—class (Profile vs Experience Event), Primary Identity, "
            "field groups, and formats—before ingestion."
        ),
        "order": 1,
        "depends_on": ["platform_access"],
    },
    {
        "id": "collection_landing",
        "title": "Collection & landing",
        "description": (
            "Source accounts, ingestion dataflows, Catalog datasets, and batch/stream validation."
        ),
        "order": 2,
        "depends_on": ["data_modeling"],
    },
    {
        "id": "profile_readiness",
        "title": "Profile readiness",
        "description": (
            "Merge policies, identity graph, and confirmation that Profile/Event data is stitching "
            "as expected before audiences and activation."
        ),
        "order": 3,
        "depends_on": ["collection_landing"],
    },
    {
        "id": "audiences",
        "title": "Audiences",
        "description": "Segment definitions, evaluation, and quality checks in Experience Platform.",
        "order": 4,
        "depends_on": ["profile_readiness"],
    },
    {
        "id": "activation",
        "title": "Activation",
        "description": (
            "Destinations, activation dataflows, mappings, and consent/DULE alignment for outbound delivery."
        ),
        "order": 5,
        "depends_on": ["audiences"],
    },
]

# Order follows AEP UI for ingestion: Schemas → Sources → wizard → Datasets → Monitoring,
# then profile/segment/destination stubs (manual until API wiring).
STEP_DEFINITIONS: list[StepDict] = [
    {
        "key": "auth",
        "phase_id": "platform_access",
        "label": "AEP authentication",
        "description": (
            "Register OAuth Server-to-Server credentials so this app can call Adobe Experience Platform APIs. "
            "(Client ID, Secret, Org ID, Technical Account ID, and sandbox from Admin / Developer Console.)"
        ),
        "action_url": "/settings",
        "action_label": "Go to Settings",
        "cli_only": False,
        "node_hint": "App Settings · API credentials · Sandbox",
        "manual_complete_allowed": False,
    },
    {
        "key": "schema",
        "phase_id": "data_modeling",
        "label": "XDM schema",
        "description": (
            "Define an XDM schema in Experience Platform **Schemas** for the data you ingest. "
            "Lock in profile vs event class, Primary Identity, and field formats—they drive Dataset and mapping."
        ),
        "action_url": "/schemas",
        "action_label": "Create schema",
        "cli_only": False,
        "node_hint": "AEP Schemas · class · Identity",
        "manual_complete_allowed": False,
    },
    {
        "key": "source",
        "phase_id": "collection_landing",
        "label": "Source connection",
        "description": (
            "In **Sources**, pick a catalog connector (S3, Azure Blob, SFTP/FTP, etc.) and connect an **Account**. "
            "(Data browse and the ingestion wizard come next.) When done in AEP, mark complete here with "
            "**Confirm source connection**."
        ),
        "action_url": "",
        "action_label": "Confirm source connection",
        "cli_only": False,
        "node_hint": "AEP Sources · connector · account",
        "manual_complete_allowed": True,
    },
    {
        "key": "dataflow",
        "phase_id": "collection_landing",
        "label": "Ingestion dataflow (Sources wizard)",
        "description": (
            "From **Sources**, open your connection and run the ingestion wizard (**Add data**, **Enable**, **Set up**—"
            "labels vary by version/locale). Flow: select data (browse) → map fields → **create or pick a Catalog "
            "Dataset** → schedule and review."
        ),
        "action_url": "/dataflows",
        "action_label": "Open Dataflows",
        "cli_only": False,
        "node_hint": "Sources wizard · mapping · Dataset",
        "manual_complete_allowed": False,
    },
    {
        "key": "dataset",
        "phase_id": "collection_landing",
        "label": "Catalog dataset review",
        "description": (
            "In **Datasets**, create a schema-backed dataset directly or verify one created in the wizard—name, "
            "schema link, Profile dataset toggle, etc. If a collection dataflow is already detected, this step "
            "may auto-complete."
        ),
        "action_url": "/datasets",
        "action_label": "Open Datasets",
        "cli_only": False,
        "node_hint": "AEP Datasets · Catalog check",
        "manual_complete_allowed": True,
    },
    {
        "key": "ingest",
        "phase_id": "collection_landing",
        "label": "Batch ingestion & validation",
        "description": (
            "Confirm batches succeeded and rows landed using **Monitoring**, **Batches**, or dataset preview. "
            "In this app, use the Batches page for uploads and status."
        ),
        "action_url": "/batches",
        "action_label": "Upload data",
        "cli_only": False,
        "node_hint": "Monitoring · batch · validation",
        "manual_complete_allowed": False,
    },
    {
        "key": "profile_ready",
        "phase_id": "profile_readiness",
        "label": "Profile & identity readiness",
        "description": (
            "In AEP, confirm **merge policy**, primary identity strategy, and that Profile or Experience Event records "
            "appear as expected (sample profile, identity graph). Mark complete when ready for audiences."
        ),
        "action_url": "",
        "action_label": "Confirm profile readiness",
        "cli_only": False,
        "node_hint": "Profiles · Merge policies · Identity",
        "manual_complete_allowed": True,
    },
    {
        "key": "segment",
        "phase_id": "audiences",
        "label": "Audiences (segments)",
        "description": (
            "Create or verify **Segments** in Experience Platform (rule-based or streaming), run evaluation, "
            "and sanity-check population. When done in AEP, confirm here (automation via Segmentation API can follow)."
        ),
        "action_url": "",
        "action_label": "Confirm audience created",
        "cli_only": False,
        "node_hint": "Segments · Audiences · evaluation",
        "manual_complete_allowed": True,
    },
    {
        "key": "destination",
        "phase_id": "activation",
        "label": "Destinations & activation",
        "description": (
            "Configure a **Destination** and activation dataflow, map fields and consent labels, and verify the first "
            "successful delivery. Complete in AEP UI for now; this app can link to Destinations later."
        ),
        "action_url": "",
        "action_label": "Confirm destination activation",
        "cli_only": False,
        "node_hint": "Destinations · activation dataflow · mapping",
        "manual_complete_allowed": True,
    },
]


def all_step_keys() -> set[str]:
    return {s["key"] for s in STEP_DEFINITIONS}


def phase_by_id() -> dict[str, PhaseDict]:
    return {p["id"]: p for p in PHASE_DEFINITIONS}
