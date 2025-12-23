import importlib.util
import os
import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
ANALYZER_PATH = ROOT / "services" / "pattern-analyzer" / "app.py"
API_GATEWAY_PATH = ROOT / "services" / "api-gateway" / "app.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def ensure_schema(conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS insight, dissent_record, decision, decision_stream, principal, org CASCADE;")

        cur.execute(
            """
            CREATE TABLE org (
              org_id uuid PRIMARY KEY,
              org_slug text,
              display_name text
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE principal (
              principal_id uuid PRIMARY KEY,
              display_name text
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE decision_stream (
              stream_id uuid PRIMARY KEY,
              org_id uuid NOT NULL,
              stream_name text NOT NULL,
              description text,
              status text DEFAULT 'active',
              color text,
              archived_at timestamptz
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE decision (
              decision_id uuid PRIMARY KEY,
              org_id uuid NOT NULL,
              stream_id uuid NOT NULL,
              title text NOT NULL,
              what_decided text NOT NULL,
              reasoning text NOT NULL,
              constraints_at_time jsonb DEFAULT '[]'::jsonb,
              alternatives_considered jsonb DEFAULT '[]'::jsonb,
              decided_by uuid NOT NULL,
              decided_at timestamptz NOT NULL,
              status text DEFAULT 'active',
              revisit_date date
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE dissent_record (
              dissent_id uuid PRIMARY KEY,
              org_id uuid NOT NULL,
              decision_id uuid NOT NULL,
              dissenter_name text NOT NULL,
              concern text NOT NULL,
              reasoning text NOT NULL,
              status text DEFAULT 'open',
              created_at timestamptz DEFAULT now()
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE insight (
              insight_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              org_id uuid NOT NULL,
              insight_type text NOT NULL,
              severity text NOT NULL,
              title text NOT NULL,
              description text NOT NULL,
              decision_ids uuid[] DEFAULT '{}',
              evidence jsonb DEFAULT '{}'::jsonb,
              status text DEFAULT 'active',
              created_at timestamptz DEFAULT now(),
              updated_at timestamptz DEFAULT now()
            );
            """
        )
    conn.commit()


@pytest.fixture(scope="session")
def db_url():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set; set to a scratch Postgres instance to run integration tests.")
    return url


@pytest.fixture()
def conn(db_url):
    conn = psycopg.connect(db_url)
    ensure_schema(conn)
    yield conn
    conn.close()


def seed_basic_data(conn: psycopg.Connection):
    org_id = uuid.uuid4()
    principal_id = uuid.uuid4()
    stream_id = uuid.uuid4()
    decision_due_id = uuid.uuid4()
    decision_dissent_id = uuid.uuid4()

    with conn.cursor() as cur:
        cur.execute("INSERT INTO org (org_id, org_slug, display_name) VALUES (%s, %s, %s)", (org_id, "test-org", "Test Org"))
        cur.execute("INSERT INTO principal (principal_id, display_name) VALUES (%s, %s)", (principal_id, "Ada Lovelace"))
        cur.execute(
            "INSERT INTO decision_stream (stream_id, org_id, stream_name, description, status, color) VALUES (%s, %s, %s, %s, %s, %s)",
            (stream_id, org_id, "Platform", "Platform decisions", "active", "#5c7cff"),
        )
        cur.execute(
            """
            INSERT INTO decision (
              decision_id, org_id, stream_id, title, what_decided, reasoning,
              decided_by, decided_at, status, revisit_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, now() - INTERVAL '90 days', 'active', now() - INTERVAL '30 days')
            """,
            (
                decision_due_id,
                org_id,
                stream_id,
                "API Versioning Policy",
                "Maintain backwards compatibility and deprecate over two releases.",
                "We promised compatibility to enterprise customers.",
                principal_id,
            ),
        )
        cur.execute(
            """
            INSERT INTO decision (
              decision_id, org_id, stream_id, title, what_decided, reasoning,
              decided_by, decided_at, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, now() - INTERVAL '10 days', 'active')
            """,
            (
                decision_dissent_id,
                org_id,
                stream_id,
                "Expose Feature X broadly",
                "Launch to all users without feature flag.",
                "Faster feedback outweighs risk.",
                principal_id,
            ),
        )
        cur.execute(
            """
            INSERT INTO dissent_record (dissent_id, org_id, decision_id, dissenter_name, concern, reasoning, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'open')
            """,
            (
                uuid.uuid4(),
                org_id,
                decision_dissent_id,
                "Maria Chen",
                "Security implications have not been addressed.",
                "No review from security yet.",
            ),
        )
    conn.commit()

    return {
        "org_id": org_id,
        "principal_id": principal_id,
        "stream_id": stream_id,
        "decision_due_id": decision_due_id,
        "decision_dissent_id": decision_dissent_id,
    }


def test_analyzer_populates_dashboard(monkeypatch, conn, db_url):
    # Seed baseline data
    ids = seed_basic_data(conn)
    org_id = str(ids["org_id"])

    # Point both services at the scratch DB
    os.environ["DATABASE_URL"] = db_url

    # Load analyzer app and stub heavy detectors to avoid embedding/LLM calls
    analyzer_app = load_module(ANALYZER_PATH, "pattern_analyzer_app")

    class NoopDetector:
        def __init__(self, *args, **kwargs):
            pass

        def detect(self):
            return []

    analyzer_app.AssumptionDriftDetector = NoopDetector
    analyzer_app.DecisionConflictDetector = NoopDetector
    analyzer_app.ValuesConflictDetector = NoopDetector

    analyzer_client = TestClient(analyzer_app.app)
    analyze_resp = analyzer_client.post("/analyze", json={"org_id": org_id})
    assert analyze_resp.status_code == 200
    analyze_data = analyze_resp.json()
    assert analyze_data["insights_generated"] >= 1
    assert not analyze_data["errors"]

    # Load API gateway with the same DB connection
    api_gateway = load_module(API_GATEWAY_PATH, "api_gateway_app")
    api_client = TestClient(api_gateway.app)
    dashboard_resp = api_client.get(f"/v1/dashboard?org_id={org_id}")
    assert dashboard_resp.status_code == 200
    dashboard = dashboard_resp.json()

    # Needs attention should include both revisit_due and unresolved_dissent items
    kinds = {item["type"] for item in dashboard["needs_attention"]}
    assert "revisit_due" in kinds
    assert "unresolved_dissent" in kinds

    # Stats should reflect the seeded decisions
    assert dashboard["stats"]["total_decisions"] >= 2
    assert dashboard["stats"]["open_dissent"] >= 1

    # Recent decisions list should contain our seeded titles
    recent_titles = {d["title"] for d in dashboard["recent_decisions"]}
    assert "API Versioning Policy" in recent_titles
    assert "Expose Feature X broadly" in recent_titles
