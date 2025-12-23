# NeuAIs Colab Helm Chart

Deploy the NeuAIs Colab platform to Kubernetes using Helm.

## Prerequisites

- Kubernetes 1.25+
- Helm 3.8+
- NVIDIA GPU Operator
- kubectl configured

## Installation

### Quick Start

```bash
# Add the chart repository (if published)
helm repo add neuais https://charts.neuais.com
helm repo update

# Install with default values
helm install neuais-colab neuais/neuais-colab \
  --namespace neuais-colab \
  --create-namespace
```

### From Source

```bash
# Install from local chart
cd containers/helm
helm install neuais-colab ./neuais-colab \
  --namespace neuais-colab \
  --create-namespace
```

### Custom Values

Create a `custom-values.yaml`:

```yaml
global:
  domain: your-domain.com

backend:
  replicaCount: 5
  env:
    gpuCount: 8

secrets:
  jwtSecret: "your-secure-jwt-secret"
  postgresPassword: "your-secure-db-password"

ingress:
  hosts:
    - host: your-domain.com
```

Install with custom values:

```bash
helm install neuais-colab ./neuais-colab \
  --namespace neuais-colab \
  --create-namespace \
  --values custom-values.yaml
```

## Configuration

See `values.yaml` for all configuration options.

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.domain` | Main domain for the platform | `colab.neuais.com` |
| `backend.replicaCount` | Number of backend pods | `3` |
| `backend.autoscaling.enabled` | Enable autoscaling | `true` |
| `postgresql.persistence.size` | Database storage size | `50Gi` |
| `persistence.workspaces.size` | User workspace storage | `500Gi` |
| `jupyter.resources.requests.gpu` | GPUs per Jupyter session | `1` |

## Upgrading

```bash
# Upgrade with new values
helm upgrade neuais-colab ./neuais-colab \
  --namespace neuais-colab \
  --values custom-values.yaml

# Rollback if needed
helm rollback neuais-colab --namespace neuais-colab
```

## Uninstallation

```bash
helm uninstall neuais-colab --namespace neuais-colab
```

## Template Testing

```bash
# Dry run to see generated manifests
helm install neuais-colab ./neuais-colab \
  --namespace neuais-colab \
  --dry-run --debug

# Template specific resources
helm template neuais-colab ./neuais-colab \
  --show-only templates/backend-deployment.yaml
```
