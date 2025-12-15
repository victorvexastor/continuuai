Below is a **copy/paste repo skeleton** you can drop into a new git repo. It includes:

* `migrations/` (ordered SQL, Postgres)
* `helm/continuuai/` (single-tenant chart: GPU inference, KMS notes, audit logging, network policies)
* `proto/` (typed event payloads + envelope)
* `services/retrieval/scorer.py` (reference hybrid scorer + MMR + policy filter skeleton)

---

## 1) Repo tree

```text
continuuai/
  README.md
  LICENSE
  .gitignore

  migrations/
    0001_extensions.sql
    0002_core_identity.sql
    0003_artifacts.sql
    0004_evidence_spans.sql
    0005_event_log.sql
    0006_policy_acl.sql
    0007_graph.sql
    0008_audit.sql
    0009_indexes.sql

  proto/
    buf.yaml
    continuuai/
      v1/
        common.proto
        events.proto
        decision.proto
        query.proto
        policy.proto

  services/
    retrieval/
      README.md
      requirements.txt
      scorer.py
      policy.py
      store_pg.py

  helm/
    continuuai/
      Chart.yaml
      values.yaml
      templates/
        _helpers.tpl
        namespace.yaml
        networkpolicy-default-deny.yaml
        configmap-schemas.yaml
        secret-tenant.yaml
        serviceaccount.yaml
        deployment-api-gateway.yaml
        service-api-gateway.yaml
        deployment-retrieval.yaml
        service-retrieval.yaml
        deployment-inference.yaml
        service-inference.yaml
        deployment-eventlog-writer.yaml
        service-eventlog-writer.yaml
        deployment-graph-deriver.yaml
        cronjob-graph-rebuild.yaml
        poddisruptionbudget.yaml
        hpa.yaml
        notes.txt
```

---

## 2) `migrations/` (SQL files in order)

### `migrations/0001_extensions.sql`

```sql
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Optional if you later use pg_trgm / full text helpers
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMIT;
```

### `migrations/0002_core_identity.sql`

```sql
BEGIN;

CREATE TABLE org (
  org_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_slug     text UNIQUE NOT NULL,
  display_name text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE principal (
  principal_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id           uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  principal_type   text NOT NULL CHECK (principal_type IN ('user','service')),
  external_subject text,
  display_name     text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, principal_type, external_subject)
);

CREATE TABLE role (
  role_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  role_name  text NOT NULL,
  UNIQUE (org_id, role_name)
);

CREATE TABLE principal_role (
  org_id        uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  principal_id  uuid NOT NULL REFERENCES principal(principal_id) ON DELETE CASCADE,
  role_id       uuid NOT NULL REFERENCES role(role_id) ON DELETE CASCADE,
  PRIMARY KEY (org_id, principal_id, role_id)
);

COMMIT;
```

### `migrations/0003_artifacts.sql`

```sql
BEGIN;

CREATE TABLE artifact (
  artifact_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,

  source_system       text NOT NULL,
  source_uri          text NOT NULL,
  source_etag         text,
  captured_at         timestamptz NOT NULL,
  occurred_at         timestamptz,
  author_principal_id uuid REFERENCES principal(principal_id),

  content_type        text NOT NULL,
  storage_uri         text NOT NULL,
  sha256              bytea NOT NULL,
  size_bytes          bigint NOT NULL,

  acl_id              uuid NOT NULL,
  pii_classification  text NOT NULL DEFAULT 'unknown'
                     CHECK (pii_classification IN ('unknown','none','low','moderate','high')),

  created_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, source_system, source_uri, source_etag)
);

CREATE TABLE artifact_text (
  artifact_text_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  artifact_id         uuid NOT NULL REFERENCES artifact(artifact_id) ON DELETE CASCADE,

  normaliser_version  text NOT NULL,
  language            text NOT NULL DEFAULT 'en',
  text_utf8           text NOT NULL,
  text_sha256         bytea NOT NULL,
  structure_json      jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, artifact_id, normaliser_version)
);

COMMIT;
```

### `migrations/0004_evidence_spans.sql`

```sql
BEGIN;

CREATE TABLE evidence_span (
  evidence_span_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,

  artifact_id         uuid NOT NULL REFERENCES artifact(artifact_id) ON DELETE CASCADE,
  artifact_text_id    uuid REFERENCES artifact_text(artifact_text_id) ON DELETE SET NULL,

  span_type           text NOT NULL CHECK (span_type IN ('text','audio','video','code','table')),
  start_char          integer,
  end_char            integer,
  start_ms            integer,
  end_ms              integer,

  section_path        text,
  speaker             text,
  message_id          text,

  extracted_by        text NOT NULL,
  confidence          real NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
  created_at          timestamptz NOT NULL DEFAULT now(),

  CHECK (
    (span_type = 'text' AND start_char IS NOT NULL AND end_char IS NOT NULL AND start_char < end_char)
 OR (span_type IN ('audio','video') AND start_ms IS NOT NULL AND end_ms IS NOT NULL AND start_ms < end_ms)
 OR (span_type IN ('code','table') AND start_char IS NOT NULL AND end_char IS NOT NULL AND start_char < end_char)
  )
);

COMMIT;
```

### `migrations/0005_event_log.sql`

```sql
BEGIN;

CREATE TABLE event_log (
  event_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,

  occurred_at         timestamptz NOT NULL,
  ingested_at         timestamptz NOT NULL DEFAULT now(),

  actor_principal_id  uuid REFERENCES principal(principal_id),
  actor_type          text NOT NULL CHECK (actor_type IN ('human','system','integration')),

  event_type          text NOT NULL,
  event_version       integer NOT NULL DEFAULT 1,
  payload             jsonb NOT NULL,

  evidence_span_ids   uuid[] NOT NULL DEFAULT '{}',
  idempotency_key     text NOT NULL,

  prev_event_hash     bytea,
  event_hash          bytea NOT NULL,
  signature           bytea,

  UNIQUE (org_id, idempotency_key)
);

COMMIT;
```

### `migrations/0006_policy_acl.sql`

```sql
BEGIN;

CREATE TABLE acl (
  acl_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  name         text NOT NULL,
  description  text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, name)
);

CREATE TABLE acl_allow (
  org_id        uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  acl_id        uuid NOT NULL REFERENCES acl(acl_id) ON DELETE CASCADE,
  allow_type    text NOT NULL CHECK (allow_type IN ('principal','role')),
  principal_id  uuid REFERENCES principal(principal_id) ON DELETE CASCADE,
  role_id       uuid REFERENCES role(role_id) ON DELETE CASCADE,
  PRIMARY KEY (org_id, acl_id, allow_type, principal_id, role_id)
);

CREATE TABLE retention_policy (
  retention_policy_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id              uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  name                text NOT NULL,
  max_age_days        integer,
  forget_mode         text NOT NULL DEFAULT 'tombstone'
                     CHECK (forget_mode IN ('tombstone','cryptoshred')),
  created_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, name)
);

ALTER TABLE artifact
  ADD COLUMN retention_policy_id uuid REFERENCES retention_policy(retention_policy_id);

COMMIT;
```

### `migrations/0007_graph.sql`

```sql
BEGIN;

ALTER TABLE artifact
  ADD CONSTRAINT fk_artifact_acl FOREIGN KEY (acl_id) REFERENCES acl(acl_id) ON DELETE RESTRICT;

CREATE TABLE graph_node (
  node_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  node_type       text NOT NULL CHECK (node_type IN (
    'Decision','Option','Constraint','Assumption','Tradeoff','Dissent','Outcome','Theme','Actor','Artifact'
  )),
  title           text NOT NULL,
  body            text,
  props           jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  source_event_id uuid NOT NULL REFERENCES event_log(event_id) ON DELETE RESTRICT,
  acl_id          uuid NOT NULL REFERENCES acl(acl_id) ON DELETE RESTRICT
);

CREATE TABLE graph_edge (
  edge_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  edge_type       text NOT NULL CHECK (edge_type IN (
    'SUPPORTED_BY','CONSIDERED','REJECTED','CONSTRAINED_BY','ASSUMES',
    'HAS_TRADEOFF','HAS_DISSENT','LED_TO','MADE_BY','ABOUT','REFERS_TO'
  )),
  from_node_id    uuid NOT NULL REFERENCES graph_node(node_id) ON DELETE CASCADE,
  to_node_id      uuid NOT NULL REFERENCES graph_node(node_id) ON DELETE CASCADE,
  weight          real NOT NULL DEFAULT 1.0 CHECK (weight >= 0),
  props           jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_event_id uuid NOT NULL REFERENCES event_log(event_id) ON DELETE RESTRICT
);

COMMIT;
```

### `migrations/0008_audit.sql`

```sql
BEGIN;

CREATE TABLE audit_query (
  audit_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id             uuid NOT NULL REFERENCES org(org_id) ON DELETE CASCADE,
  query_id           text NOT NULL,
  principal_id       uuid NOT NULL REFERENCES principal(principal_id),
  mode               text NOT NULL CHECK (mode IN ('recall','reflection','projection')),
  created_at         timestamptz NOT NULL DEFAULT now(),

  policy_hash        bytea NOT NULL,
  retrieval_set_hash bytea NOT NULL,
  evidence_span_ids  uuid[] NOT NULL,
  response_hash      bytea NOT NULL,

  latency_ms         integer NOT NULL,
  status             text NOT NULL CHECK (status IN ('ok','insufficient_evidence','policy_denied','error')),
  error_code         text,

  UNIQUE (org_id, query_id)
);

COMMIT;
```

### `migrations/0009_indexes.sql`

```sql
BEGIN;

CREATE INDEX idx_artifact_org_time ON artifact(org_id, captured_at DESC);
CREATE INDEX idx_artifact_acl ON artifact(org_id, acl_id);

CREATE INDEX idx_artifact_text_artifact ON artifact_text(org_id, artifact_id);
CREATE INDEX idx_evidence_artifact ON evidence_span(org_id, artifact_id);

CREATE INDEX idx_event_time ON event_log(org_id, occurred_at DESC);
CREATE INDEX idx_event_type ON event_log(org_id, event_type);

CREATE INDEX idx_graph_node_type ON graph_node(org_id, node_type);
CREATE INDEX idx_graph_edge_from ON graph_edge(org_id, from_node_id);
CREATE INDEX idx_graph_edge_to ON graph_edge(org_id, to_node_id);
CREATE INDEX idx_graph_edge_type ON graph_edge(org_id, edge_type);

CREATE INDEX idx_audit_time ON audit_query(org_id, created_at DESC);

COMMIT;
```

---

## 3) `proto/` (Buf + protobufs)

### `proto/buf.yaml`

```yaml
version: v1
name: buf.build/continuuai/continuuai
breaking:
  use:
    - FILE
lint:
  use:
    - DEFAULT
```

### `proto/continuuai/v1/common.proto`

```proto
syntax = "proto3";

package continuuai.v1;

import "google/protobuf/timestamp.proto";

message EvidenceRef {
  string evidence_span_id = 1; // UUID as string
  string note = 2;
}

message ActorRef {
  string principal_id = 1; // UUID
  string actor_type = 2;   // human|system|integration
}

message OrgRef {
  string org_id = 1; // UUID
}

message EventEnvelope {
  string event_id = 1; // UUID
  OrgRef org = 2;
  google.protobuf.Timestamp occurred_at = 3;
  google.protobuf.Timestamp ingested_at = 4;

  ActorRef actor = 5;

  string event_type = 6;
  int32 event_version = 7;

  // One-of payload is in events.proto; we keep a generic JSON fallback too.
  bytes payload_json = 8;

  repeated EvidenceRef evidence = 9;

  string idempotency_key = 10;
  bytes prev_event_hash = 11;
  bytes event_hash = 12;
  bytes signature = 13;
}
```

### `proto/continuuai/v1/decision.proto`

```proto
syntax = "proto3";

package continuuai.v1;

message DecisionProposed {
  string decision_id = 1; // stable UUID
  string title = 2;
  string context = 3;

  repeated string option_ids = 4;
  repeated string constraint_ids = 5;
  repeated string assumption_ids = 6;

  // freeform tags/scopes
  repeated string scopes = 7; // e.g. project/team ids
}

message DecisionConfirmed {
  string decision_id = 1;
  string chosen_option_id = 2;
  string rationale = 3;
}

message DecisionAmended {
  string decision_id = 1;
  string amendment = 2; // what changed + why
}

message DecisionOutcomeRecorded {
  string decision_id = 1;
  string outcome_summary = 2;
  string outcome_status = 3; // success|mixed|failed|unknown
}
```

### `proto/continuuai/v1/query.proto`

```proto
syntax = "proto3";

package continuuai.v1;

message QueryAsked {
  string query_id = 1;
  string mode = 2; // recall|reflection|projection
  string query_text = 3;
  repeated string scopes = 4;
}

message QueryAnswered {
  string query_id = 1;
  string response_hash_hex = 2;
  repeated string evidence_span_ids = 3;
  string status = 4; // ok|insufficient_evidence|policy_denied|error
}
```

### `proto/continuuai/v1/policy.proto`

```proto
syntax = "proto3";

package continuuai.v1;

message AclCreated {
  string acl_id = 1;
  string name = 2;
  string description = 3;
}

message RetentionPolicyCreated {
  string retention_policy_id = 1;
  string name = 2;
  int32 max_age_days = 3; // 0 means infinite when interpreted
  string forget_mode = 4; // tombstone|cryptoshred
}
```

### `proto/continuuai/v1/events.proto`

```proto
syntax = "proto3";

package continuuai.v1;

import "continuuai/v1/decision.proto";
import "continuuai/v1/query.proto";
import "continuuai/v1/policy.proto";

message EventPayload {
  oneof payload {
    DecisionProposed decision_proposed = 1;
    DecisionConfirmed decision_confirmed = 2;
    DecisionAmended decision_amended = 3;
    DecisionOutcomeRecorded decision_outcome_recorded = 4;

    QueryAsked query_asked = 10;
    QueryAnswered query_answered = 11;

    AclCreated acl_created = 20;
    RetentionPolicyCreated retention_policy_created = 21;
  }
}
```

---

## 4) Helm chart: `helm/continuuai/`

### `helm/continuuai/Chart.yaml`

```yaml
apiVersion: v2
name: continuuai
description: Continuuai single-tenant deployment (API, retrieval, inference, eventlog, graph-deriver)
type: application
version: 0.1.0
appVersion: "0.1.0"
```

### `helm/continuuai/values.yaml`

```yaml
tenant:
  orgSlug: "example"
  orgId: "00000000-0000-0000-0000-000000000000"
  namespaceCreate: true

image:
  registry: "registry.local/continuuai"
  tag: "dev"
  pullPolicy: IfNotPresent

serviceAccount:
  create: true
  name: ""

networkPolicy:
  defaultDeny: true

kms:
  # Notes only: actual KMS encryption-at-rest is cluster-level (apiserver/etcd).
  enabled: true
  provider: "cloud-kms"
  keyRef: "kms-key-ref-placeholder"

audit:
  appAuditEnabled: true
  kubernetesAuditNotes: true

postgres:
  host: "postgres.example.svc.cluster.local"
  port: 5432
  database: "continuuai"
  user: "continuuai"
  # password is stored in secret-tenant.yaml

objectStore:
  uri: "s3://continuuai-example"
  region: "ap-southeast-2"

resources:
  apiGateway:
    requests: { cpu: "200m", memory: "256Mi" }
    limits: { cpu: "1", memory: "512Mi" }
  retrieval:
    requests: { cpu: "500m", memory: "512Mi" }
    limits: { cpu: "2", memory: "2Gi" }
  inference:
    requests: { cpu: "4", memory: "16Gi" }
    limits: { cpu: "8", memory: "32Gi", nvidia.com/gpu: 1 }

gpu:
  nodeSelector:
    nodepool: "gpu"
  tolerations:
    - key: "nvidia.com/gpu"
      operator: "Exists"
      effect: "NoSchedule"

replicas:
  apiGateway: 2
  retrieval: 2
  inference: 2
  eventlogWriter: 2
  graphDeriver: 1

hpa:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  cpuUtilization: 70

schemas:
  responseContractJson: |
    {"contract_version":"v1","note":"put the full JSON schema here in real deploy"}
```

### `helm/continuuai/templates/_helpers.tpl`

```yaml
{{- define "continuuai.name" -}}
continuuai
{{- end -}}

{{- define "continuuai.fullname" -}}
{{ include "continuuai.name" . }}-{{ .Values.tenant.orgSlug }}
{{- end -}}

{{- define "continuuai.saName" -}}
{{- if .Values.serviceAccount.name -}}
{{ .Values.serviceAccount.name }}
{{- else -}}
{{ include "continuuai.fullname" . }}
{{- end -}}
{{- end -}}
```

### `helm/continuuai/templates/namespace.yaml`

```yaml
{{- if and .Values.tenant.namespaceCreate .Release.IsInstall -}}
apiVersion: v1
kind: Namespace
metadata:
  name: continuuai-org-{{ .Values.tenant.orgSlug }}
  labels:
    continuuuai.org/tenant: "{{ .Values.tenant.orgSlug }}"
{{- end -}}
```

### `helm/continuuai/templates/networkpolicy-default-deny.yaml`

```yaml
{{- if .Values.networkPolicy.defaultDeny -}}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
{{- end -}}
```

### `helm/continuuai/templates/configmap-schemas.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: response-schemas
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
data:
  response-contract.v1.json: |
{{ .Values.schemas.responseContractJson | indent 4 }}
```

### `helm/continuuai/templates/secret-tenant.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tenant-secrets
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
type: Opaque
stringData:
  org_id: "{{ .Values.tenant.orgId }}"
  postgres_password: "CHANGE_ME"
```

### `helm/continuuai/templates/serviceaccount.yaml`

```yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "continuuai.saName" . }}
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
{{- end -}}
```

### `helm/continuuai/templates/deployment-api-gateway.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  replicas: {{ .Values.replicas.apiGateway }}
  selector:
    matchLabels: { app: api-gateway }
  template:
    metadata:
      labels: { app: api-gateway }
    spec:
      serviceAccountName: {{ include "continuuai.saName" . }}
      containers:
        - name: api-gateway
          image: "{{ .Values.image.registry }}/api-gateway:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports: [{ containerPort: 8080 }]
          env:
            - name: ORG_ID
              valueFrom: { secretKeyRef: { name: tenant-secrets, key: org_id } }
          resources:
            requests: {{ toYaml .Values.resources.apiGateway.requests | nindent 12 }}
            limits: {{ toYaml .Values.resources.apiGateway.limits | nindent 12 }}
```

### `helm/continuuai/templates/service-api-gateway.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  selector: { app: api-gateway }
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

### `helm/continuuai/templates/deployment-retrieval.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: retrieval-service
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  replicas: {{ .Values.replicas.retrieval }}
  selector:
    matchLabels: { app: retrieval-service }
  template:
    metadata:
      labels: { app: retrieval-service }
    spec:
      serviceAccountName: {{ include "continuuai.saName" . }}
      containers:
        - name: retrieval
          image: "{{ .Values.image.registry }}/retrieval-service:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports: [{ containerPort: 8080 }]
          env:
            - name: ORG_ID
              valueFrom: { secretKeyRef: { name: tenant-secrets, key: org_id } }
            - name: POSTGRES_HOST
              value: "{{ .Values.postgres.host }}"
            - name: POSTGRES_PORT
              value: "{{ .Values.postgres.port }}"
            - name: POSTGRES_DB
              value: "{{ .Values.postgres.database }}"
            - name: POSTGRES_USER
              value: "{{ .Values.postgres.user }}"
            - name: POSTGRES_PASSWORD
              valueFrom: { secretKeyRef: { name: tenant-secrets, key: postgres_password } }
          resources:
            requests: {{ toYaml .Values.resources.retrieval.requests | nindent 12 }}
            limits: {{ toYaml .Values.resources.retrieval.limits | nindent 12 }}
```

### `helm/continuuai/templates/service-retrieval.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: retrieval-service
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  selector: { app: retrieval-service }
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

### `helm/continuuai/templates/deployment-inference.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  replicas: {{ .Values.replicas.inference }}
  selector:
    matchLabels: { app: inference-service }
  template:
    metadata:
      labels: { app: inference-service }
    spec:
      serviceAccountName: {{ include "continuuai.saName" . }}
      nodeSelector:
{{ toYaml .Values.gpu.nodeSelector | indent 8 }}
      tolerations:
{{ toYaml .Values.gpu.tolerations | indent 8 }}
      containers:
        - name: inference
          image: "{{ .Values.image.registry }}/inference-service:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports: [{ containerPort: 8080 }]
          env:
            - name: ORG_ID
              valueFrom: { secretKeyRef: { name: tenant-secrets, key: org_id } }
            - name: RESPONSE_SCHEMA_PATH
              value: "/schemas/response-contract.v1.json"
          volumeMounts:
            - name: schemas
              mountPath: /schemas
              readOnly: true
          resources:
            requests: {{ toYaml .Values.resources.inference.requests | nindent 12 }}
            limits: {{ toYaml .Values.resources.inference.limits | nindent 12 }}
      volumes:
        - name: schemas
          configMap:
            name: response-schemas
```

### `helm/continuuai/templates/service-inference.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: inference-service
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  selector: { app: inference-service }
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

### `helm/continuuai/templates/deployment-eventlog-writer.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eventlog-writer
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  replicas: {{ .Values.replicas.eventlogWriter }}
  selector:
    matchLabels: { app: eventlog-writer }
  template:
    metadata:
      labels: { app: eventlog-writer }
    spec:
      serviceAccountName: {{ include "continuuai.saName" . }}
      containers:
        - name: eventlog-writer
          image: "{{ .Values.image.registry }}/eventlog-writer:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports: [{ containerPort: 8080 }]
          env:
            - name: ORG_ID
              valueFrom: { secretKeyRef: { name: tenant-secrets, key: org_id } }
```

### `helm/continuuai/templates/service-eventlog-writer.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: eventlog-writer
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  selector: { app: eventlog-writer }
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

### `helm/continuuai/templates/deployment-graph-deriver.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graph-deriver
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  replicas: {{ .Values.replicas.graphDeriver }}
  selector:
    matchLabels: { app: graph-deriver }
  template:
    metadata:
      labels: { app: graph-deriver }
    spec:
      serviceAccountName: {{ include "continuuai.saName" . }}
      containers:
        - name: graph-deriver
          image: "{{ .Values.image.registry }}/graph-deriver:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          env:
            - name: ORG_ID
              valueFrom: { secretKeyRef: { name: tenant-secrets, key: org_id } }
```

### `helm/continuuai/templates/cronjob-graph-rebuild.yaml`

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: graph-rebuild-nightly
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  schedule: "17 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: {{ include "continuuai.saName" . }}
          restartPolicy: OnFailure
          containers:
            - name: graph-rebuild
              image: "{{ .Values.image.registry }}/graph-deriver:{{ .Values.image.tag }}"
              args: ["--rebuild-from-scratch"]
              env:
                - name: ORG_ID
                  valueFrom: { secretKeyRef: { name: tenant-secrets, key: org_id } }
```

### `helm/continuuai/templates/poddisruptionbudget.yaml`

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: inference-pdb
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: inference-service
```

### `helm/continuuai/templates/hpa.yaml`

```yaml
{{- if .Values.hpa.enabled -}}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: retrieval-hpa
  namespace: continuuai-org-{{ .Values.tenant.orgSlug }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: retrieval-service
  minReplicas: {{ .Values.hpa.minReplicas }}
  maxReplicas: {{ .Values.hpa.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.hpa.cpuUtilization }}
{{- end -}}
```

### `helm/continuuai/templates/notes.txt`

```text
KMS NOTES (cluster-level):
- Kubernetes secret encryption-at-rest is configured on the API server / managed service, not in Helm.
- Use cloud KMS (AWS KMS / GCP KMS / Azure Key Vault) for etcd envelope encryption.
- App-level envelope encryption should be used for artifacts in object storage.

AUDIT NOTES:
- Enable Kubernetes API audit logging at the cluster control plane.
- Application audit (audit_query table) logs query -> evidence set -> response hash for replayability.
```

---

## 5) Reference scorer implementation (Python)

### `services/retrieval/requirements.txt`

```txt
numpy>=1.26
python-dateutil>=2.9
```

### `services/retrieval/policy.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Set, Dict

@dataclass(frozen=True)
class PrincipalContext:
    org_id: str
    principal_id: str
    role_ids: Set[str]

class PolicyStore:
    """
    Stub. In production:
      - load ACL allows from Postgres (acl_allow + principal_role)
      - cache per-org for short TTL
    """
    def __init__(self, acl_map: Dict[str, Set[str]] | None = None) -> None:
        # acl_id -> set of allowed principal_ids (demo)
        self._acl_map = acl_map or {}

    def allowed_acl(self, ctx: PrincipalContext, acl_id: str) -> bool:
        allowed_principals = self._acl_map.get(acl_id, set())
        return ctx.principal_id in allowed_principals
```

### `services/retrieval/scorer.py`

```python
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Iterable
import numpy as np

from policy import PolicyStore, PrincipalContext

# -----------------------------
# Data structures
# -----------------------------

@dataclass
class EvidenceSpan:
    evidence_span_id: str
    artifact_id: str
    acl_id: str
    text: str
    occurred_at: datetime  # domain time for recency
    confidence: float = 1.0
    section_key: str = ""  # e.g. section_path|message_id for bundling

@dataclass
class GraphSignal:
    # precomputed relevance in [0,1] (you can compute via traversals)
    graph_relevance: float

@dataclass
class Candidate:
    span: EvidenceSpan
    sim: float            # semantic similarity [-1..1] or [0..1] after normalisation
    bm25: float           # lexical score (raw)
    graph: GraphSignal

@dataclass
class ScoredSpan:
    span: EvidenceSpan
    score: float

@dataclass
class ContextPackage:
    evidence_spans: List[EvidenceSpan]
    retrieval_debug: Dict[str, object]


# -----------------------------
# Helpers
# -----------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def normalise_01(values: List[float]) -> List[float]:
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if math.isclose(vmin, vmax):
        return [1.0 for _ in values]
    return [(v - vmin) / (vmax - vmin) for v in values]

def recency_decay(occurred_at: datetime, tau_days: float = 90.0) -> float:
    age_days = max(0.0, (now_utc() - occurred_at).total_seconds() / (3600 * 24))
    return math.exp(-(age_days / tau_days))

def coverage_factor(text: str, min_chars: int = 80, max_chars: int = 2200) -> float:
    # penalise tiny spans + overly huge spans; this is intentionally gentle
    n = len(text or "")
    if n <= 0:
        return 0.0
    if n < min_chars:
        return max(0.2, n / float(min_chars))
    if n > max_chars:
        return max(0.5, max_chars / float(n))
    return 1.0

def mmr_select(items: List[ScoredSpan], k: int, lam: float, sim_matrix: Optional[np.ndarray] = None) -> List[ScoredSpan]:
    """
    MMR selection. If you don't have a similarity matrix, we approximate by text hash overlap (cheap).
    """
    if k <= 0 or not items:
        return []

    selected: List[ScoredSpan] = []
    remaining = items[:]

    # Fallback similarity: Jaccard over token sets (cheap, imperfect)
    def cheap_sim(a: EvidenceSpan, b: EvidenceSpan) -> float:
        ta = set((a.text or "").lower().split()[:80])
        tb = set((b.text or "").lower().split()[:80])
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / float(len(ta | tb))

    while remaining and len(selected) < k:
        best_idx = 0
        best_val = -1e9
        for i, cand in enumerate(remaining):
            if not selected:
                diversity_pen = 0.0
            else:
                diversity_pen = max(cheap_sim(cand.span, s.span) for s in selected)
            val = lam * cand.score - (1.0 - lam) * diversity_pen
            if val > best_val:
                best_val = val
                best_idx = i
        selected.append(remaining.pop(best_idx))
    return selected


# -----------------------------
# Scoring
# -----------------------------

MODE_WEIGHTS = {
    "recall":      dict(w_sem=0.45, w_lex=0.25, w_graph=0.20, w_rec=0.08, w_auth=0.02, lam=0.75),
    "reflection":  dict(w_sem=0.35, w_lex=0.15, w_graph=0.35, w_rec=0.10, w_auth=0.05, lam=0.65),
    "projection":  dict(w_sem=0.30, w_lex=0.10, w_graph=0.40, w_rec=0.15, w_auth=0.05, lam=0.60),
}

def score_candidates(
    candidates: List[Candidate],
    mode: str,
    policy_store: PolicyStore,
    principal_ctx: PrincipalContext,
    max_bundles: int = 12,
    max_spans_per_bundle: int = 2,
) -> ContextPackage:
    mode = mode.lower().strip()
    if mode not in MODE_WEIGHTS:
        raise ValueError(f"Unknown mode: {mode}")

    w = MODE_WEIGHTS[mode]

    # 1) Policy filter FIRST (no ranking on disallowed items)
    allowed = [c for c in candidates if policy_store.allowed_acl(principal_ctx, c.span.acl_id)]
    if not allowed:
        return ContextPackage(evidence_spans=[], retrieval_debug={"reason": "policy_filtered_all"})

    # 2) Normalise bm25 into [0,1]
    bm25_norm = normalise_01([c.bm25 for c in allowed])

    # 3) Normalise sim into [0,1] if given as [-1,1]
    sims_raw = []
    for c in allowed:
        s = c.sim
        if s < 0.0:  # assume cosine in [-1,1]
            s = (s + 1.0) / 2.0
        sims_raw.append(max(0.0, min(1.0, s)))
    sim_norm = sims_raw  # already in [0,1]

    # 4) Compute scores
    scored: List[ScoredSpan] = []
    for i, c in enumerate(allowed):
        rec = recency_decay(c.span.occurred_at, tau_days=90.0)
        graph = max(0.0, min(1.0, c.graph.graph_relevance))
        authority = max(0.0, min(1.0, c.span.confidence))  # placeholder
        cov = coverage_factor(c.span.text)

        score = (
            w["w_sem"] * sim_norm[i]
            + w["w_lex"] * bm25_norm[i]
            + w["w_graph"] * graph
            + w["w_rec"] * rec
            + w["w_auth"] * authority
        ) * cov

        scored.append(ScoredSpan(span=c.span, score=score))

    scored.sort(key=lambda s: s.score, reverse=True)

    # 5) Bundle by section_key (artifact/thread/section)
    bundles: Dict[str, List[ScoredSpan]] = {}
    for s in scored:
        key = s.span.section_key or f"{s.span.artifact_id}"
        bundles.setdefault(key, []).append(s)

    # Take top-N from each bundle
    bundle_reps: List[ScoredSpan] = []
    for key, items in bundles.items():
        items.sort(key=lambda x: x.score, reverse=True)
        bundle_reps.extend(items[:max_spans_per_bundle])

    bundle_reps.sort(key=lambda x: x.score, reverse=True)

    # 6) MMR pick to reduce redundancy
    selected = mmr_select(bundle_reps, k=max_bundles, lam=w["lam"])

    # 7) Return context
    debug = {
        "mode": mode,
        "candidates_in": len(candidates),
        "candidates_allowed": len(allowed),
        "bundle_count": len(bundles),
        "selected": [{"id": s.span.evidence_span_id, "score": s.score} for s in selected],
    }
    return ContextPackage(
        evidence_spans=[s.span for s in selected],
        retrieval_debug=debug
    )


# -----------------------------
# Demo entrypoint
# -----------------------------

if __name__ == "__main__":
    # Minimal sanity run
    ps = PolicyStore(acl_map={"acl-public": {"p1"}})
    ctx = PrincipalContext(org_id="o1", principal_id="p1", role_ids=set())

    base_time = now_utc()

    candidates = [
        Candidate(EvidenceSpan("e1","a1","acl-public","Decision confirmed: ship X", base_time, 0.9, "a1|sec1"),
                  sim=0.72, bm25=12.3, graph=GraphSignal(0.8)),
        Candidate(EvidenceSpan("e2","a1","acl-public","Dissent: worried about reliability", base_time, 0.8, "a1|sec1"),
                  sim=0.61, bm25=10.1, graph=GraphSignal(0.9)),
        Candidate(EvidenceSpan("e3","a2","acl-private","Hidden thing", base_time, 0.9, "a2|sec7"),
                  sim=0.99, bm25=99.0, graph=GraphSignal(1.0)),
    ]

    pkg = score_candidates(candidates, "reflection", ps, ctx)
    print(pkg.retrieval_debug)
    print([s.evidence_span_id for s in pkg.evidence_spans])
```

### `services/retrieval/store_pg.py` (stub for DB access)

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import List

# Placeholder module so you have a clear seam:
# - load candidates from Postgres (and vector store if separate)
# - join ACL ids per evidence span
# - return Candidate objects for scorer.py

@dataclass
class PgConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

class PgStore:
    def __init__(self, cfg: PgConfig) -> None:
        self.cfg = cfg

    def fetch_candidates(self, org_id: str, query_text: str, limit: int = 500):
        raise NotImplementedError("Implement with psycopg/asyncpg + your indexes/vector store")
```

### `services/retrieval/README.md`

```md
# Retrieval Service (reference)

This folder contains:
- policy-first filtering
- hybrid scoring (semantic + lexical + graph + recency)
- MMR selection + bundling

Wire it to:
- Postgres for evidence spans + ACL ids
- A vector index for semantic similarity
- Optional BM25/FTS engine for lexical scores
```

---

## 6) Root `README.md`

```md
# Continuuai (skeleton)

## Migrations
Apply in order in `migrations/`. Example:
- Use your migration tool of choice (goose, flyway, dbmate, sqitch, liquibase).
- Or manually `psql -f migrations/0001_extensions.sql ...`

## Helm
Install:
- `helm install continuuai helm/continuuai -f helm/continuuai/values.yaml`

Notes:
- KMS secret encryption is cluster-level (control plane), not Helm.
- This chart includes GPU scheduling for inference.

## Proto
Protobuf definitions live in `proto/`.
- Uses Buf (optional) for lint/breaking.
```

---

If you want the **same skeleton but with a working local dev loop** (Docker Compose: Postgres + MinIO + “fake inference” that returns a schema-valid response), I can add `docker-compose.yml`, a tiny FastAPI gateway, and a migration runner so you can type one command and see end-to-end “query → retrieval → contract-valid JSON” working.
