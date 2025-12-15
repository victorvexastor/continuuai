CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Org + identity
CREATE TABLE IF NOT EXISTS org (
  org_id uuid PRIMARY KEY,
  org_slug text NOT NULL UNIQUE,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS principal (
  principal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  principal_type text NOT NULL CHECK (principal_type IN ('user','service','group')),
  external_subject text NOT NULL,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, external_subject)
);

CREATE TABLE IF NOT EXISTS role (
  role_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  role_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, role_name)
);

-- ACLs
CREATE TABLE IF NOT EXISTS acl (
  acl_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, name)
);

CREATE TABLE IF NOT EXISTS acl_allow (
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  acl_id uuid NOT NULL REFERENCES acl(acl_id) ON DELETE CASCADE,
  allow_type text NOT NULL CHECK (allow_type IN ('principal','role')),
  principal_id uuid NULL REFERENCES principal(principal_id) ON DELETE CASCADE,
  role_id uuid NULL REFERENCES role(role_id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (allow_type='principal' AND principal_id IS NOT NULL AND role_id IS NULL) OR
    (allow_type='role' AND role_id IS NOT NULL AND principal_id IS NULL)
  ),
  UNIQUE (org_id, acl_id, allow_type, principal_id, role_id)
);

-- Artifacts + text
CREATE TABLE IF NOT EXISTS artifact (
  artifact_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,

  source_system text NOT NULL,
  source_uri text NOT NULL,
  source_etag text NULL,

  captured_at timestamptz NOT NULL DEFAULT now(),
  occurred_at timestamptz NOT NULL DEFAULT now(),

  author_principal_id uuid NULL REFERENCES principal(principal_id) ON DELETE SET NULL,

  content_type text NOT NULL,
  storage_uri text NOT NULL,
  sha256 bytea NOT NULL,
  size_bytes bigint NOT NULL DEFAULT 0,

  acl_id uuid NOT NULL REFERENCES acl(acl_id) ON DELETE RESTRICT,
  pii_classification text NOT NULL DEFAULT 'none',

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_org_time ON artifact(org_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS artifact_text (
  artifact_text_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  artifact_id uuid NOT NULL REFERENCES artifact(artifact_id) ON DELETE CASCADE,

  normaliser_version text NOT NULL,
  language text NOT NULL DEFAULT 'en',
  text_utf8 text NOT NULL,
  text_sha256 bytea NOT NULL,
  structure_json jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_text_org_art ON artifact_text(org_id, artifact_id);

-- Evidence spans
CREATE TABLE IF NOT EXISTS evidence_span (
  evidence_span_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  artifact_id uuid NOT NULL REFERENCES artifact(artifact_id) ON DELETE CASCADE,
  artifact_text_id uuid NOT NULL REFERENCES artifact_text(artifact_text_id) ON DELETE CASCADE,

  span_type text NOT NULL DEFAULT 'text',
  start_char int NOT NULL,
  end_char int NOT NULL,
  section_path text NOT NULL DEFAULT '',
  extracted_by text NOT NULL,
  confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),

  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (end_char >= start_char)
);

CREATE INDEX IF NOT EXISTS idx_evidence_org_created ON evidence_span(org_id, created_at DESC);
