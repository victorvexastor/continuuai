from __future__ import annotations
import os
import hashlib
from datetime import datetime, timezone

import psycopg


def sha256b(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()


def main() -> None:
    dsn = os.environ["DATABASE_URL"]
    org_id = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000000")
    org_slug = os.environ.get("ORG_SLUG", "example")

    with psycopg.connect(dsn) as conn, conn.transaction():
        # Org (explicit id so demo requests can hardcode it)
        conn.execute(
            "INSERT INTO org(org_id, org_slug, display_name) VALUES (%s,%s,%s) "
            "ON CONFLICT (org_id) DO NOTHING",
            (org_id, org_slug, "Example Org"),
        )

        # Roles
        conn.execute(
            "INSERT INTO role(org_id, role_name) VALUES (%s,'admin') ON CONFLICT DO NOTHING",
            (org_id,),
        )
        conn.execute(
            "INSERT INTO role(org_id, role_name) VALUES (%s,'staff') ON CONFLICT DO NOTHING",
            (org_id,),
        )

        # Principals
        conn.execute(
            "INSERT INTO principal(org_id, principal_type, external_subject, display_name) "
            "VALUES (%s,'user','p1','Pilot One') ON CONFLICT DO NOTHING",
            (org_id,),
        )

        # ACLs
        acl_public = conn.execute(
            "INSERT INTO acl(org_id, name, description) VALUES (%s,'public','Demo public ACL') "
            "ON CONFLICT (org_id, name) DO UPDATE SET description=EXCLUDED.description "
            "RETURNING acl_id",
            (org_id,),
        ).fetchone()[0]

        # allow principal p1 on acl_public
        principal_id = conn.execute(
            "SELECT principal_id FROM principal WHERE org_id=%s AND external_subject='p1'",
            (org_id,),
        ).fetchone()[0]

        conn.execute(
            "INSERT INTO acl_allow(org_id, acl_id, allow_type, principal_id, role_id) "
            "VALUES (%s,%s,'principal',%s,NULL) "
            "ON CONFLICT DO NOTHING",
            (org_id, acl_public, principal_id),
        )

        # Artifacts + text
        artifact_id = conn.execute(
            "INSERT INTO artifact(org_id, source_system, source_uri, source_etag, captured_at, occurred_at, "
            "author_principal_id, content_type, storage_uri, sha256, size_bytes, acl_id, pii_classification) "
            "VALUES (%s,'demo','demo://artifact/1','v1',now(),now(),%s,'text/plain','s3://demo/1',%s,123,%s,'none') "
            "RETURNING artifact_id",
            (org_id, principal_id, sha256b("artifact1"), acl_public),
        ).fetchone()[0]

        atid = conn.execute(
            "INSERT INTO artifact_text(org_id, artifact_id, normaliser_version, language, text_utf8, text_sha256, structure_json) "
            "VALUES (%s,%s,'v1','en',%s,%s,'{}'::jsonb) RETURNING artifact_text_id",
            (
                org_id,
                artifact_id,
                "Decision log: We decided to ship Feature X behind a flag.\n"
                "Dissent: Reliability risk noted; mitigation: staged rollout.\n"
                "Outcome: mixed; rollback once, then fixed.\n",
                sha256b("text1"),
            ),
        ).fetchone()[0]

        # Evidence spans (3 small spans)
        now = datetime.now(timezone.utc)
        spans = [
            ("Decision confirmed: ship Feature X behind a flag.", 0, 52, 0.92, "a1|sec1"),
            ("Dissent: reliability risk; mitigation: staged rollout.", 53, 110, 0.84, "a1|sec1"),
            ("Outcome: mixed; rollback once, then fixed.", 111, 156, 0.78, "a1|sec2"),
        ]
        for i, (txt, s, e, conf, skey) in enumerate(spans, start=1):
            conn.execute(
                "INSERT INTO evidence_span(org_id, artifact_id, artifact_text_id, span_type, start_char, end_char, "
                "section_path, extracted_by, confidence, created_at) "
                "VALUES (%s,%s,%s,'text',%s,%s,%s,'seed',%s,now())",
                (org_id, artifact_id, atid, s, e, skey, conf),
            )

    print("seed complete")


if __name__ == "__main__":
    main()
