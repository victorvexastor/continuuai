-- Migration 0010: principal_role mapping for ACLs
CREATE TABLE IF NOT EXISTS principal_role (
  org_id uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  principal_id uuid NOT NULL REFERENCES principal(principal_id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES role(role_id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, principal_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_principal_role_principal ON principal_role(org_id, principal_id);
CREATE INDEX IF NOT EXISTS idx_principal_role_role ON principal_role(org_id, role_id);
