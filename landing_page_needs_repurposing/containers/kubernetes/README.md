# NeuAIs Colab - Kubernetes Deployment Guide

Complete Kubernetes manifests for production deployment of the NeuAIs Colab platform.

## Prerequisites

- Kubernetes cluster v1.25+
- NVIDIA GPU Operator installed
- kubectl configured
- Helm 3+ (for cert-manager and NGINX ingress)
- StorageClass configured for dynamic provisioning

## Installation Steps

### 1. Install Required Components

```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Install cert-manager for TLS
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Install NVIDIA GPU Operator (if not already installed)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

### 2. Configure Storage Classes

Create storage classes for your cluster:

```yaml
# fast-ssd.yaml - For database storage
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/gce-pd  # Change based on cloud provider
parameters:
  type: pd-ssd
allowVolumeExpansion: true

---
# shared-storage.yaml - For user workspaces
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: shared-storage
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-standard
allowVolumeExpansion: true
```

### 3. Label GPU Nodes

Label your GPU nodes for proper scheduling:

```bash
# List nodes with GPUs
kubectl get nodes --selector=nvidia.com/gpu.present=true

# Label GPU nodes
kubectl label nodes <gpu-node-name> node-role=gpu-worker
kubectl label nodes <gpu-node-name> nvidia.com/gpu=true

# Taint GPU nodes (optional, prevents non-GPU workloads)
kubectl taint nodes <gpu-node-name> nvidia.com/gpu=true:NoSchedule
```

### 4. Build and Push Docker Images

```bash
# Build frontend
cd frontend
docker build -t neuais/colab-frontend:latest .
docker push neuais/colab-frontend:latest

# Build backend
cd ../backend
docker build -t neuais/colab-backend:latest .
docker push neuais/colab-backend:latest

# Build Jupyter image
cd ../containers
docker build -f Dockerfile.jupyter -t neuais/jupyter:latest .
docker push neuais/jupyter:latest
```

### 5. Update Secrets

Edit `secrets.yaml` with your actual secrets:

```bash
# Generate a secure JWT secret
openssl rand -base64 32

# Update secrets.yaml with generated values
vim containers/kubernetes/secrets.yaml
```

### 6. Deploy to Kubernetes

```bash
cd containers/kubernetes

# Create namespace
kubectl apply -f namespace.yaml

# Create ConfigMaps and Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# Create Persistent Volumes
kubectl apply -f persistent-volumes.yaml

# Deploy PostgreSQL
kubectl apply -f postgres.yaml

# Deploy Redis
kubectl apply -f redis.yaml

# Deploy Backend
kubectl apply -f backend.yaml

# Deploy Frontend
kubectl apply -f frontend.yaml

# Configure RBAC
kubectl apply -f rbac.yaml

# Apply security policies
kubectl apply -f security-policies.yaml
kubectl apply -f resource-quota.yaml

# Create Ingress (update DNS first!)
kubectl apply -f ingress.yaml
```

### 7. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n neuais-colab

# Check services
kubectl get svc -n neuais-colab

# Check ingress
kubectl get ingress -n neuais-colab

# Check persistent volumes
kubectl get pvc -n neuais-colab

# View logs
kubectl logs -n neuais-colab deployment/backend -f
```

## Resource Manifests

### File Structure

```
kubernetes/
├── namespace.yaml              # Namespace definition
├── configmap.yaml             # Configuration data
├── secrets.yaml               # Sensitive data (passwords, tokens)
├── persistent-volumes.yaml    # Storage claims
├── postgres.yaml              # PostgreSQL StatefulSet
├── redis.yaml                 # Redis deployment
├── backend.yaml               # Backend API deployment + HPA
├── frontend.yaml              # Frontend deployment
├── jupyter-pod-template.yaml  # Jupyter session template
├── ingress.yaml               # Ingress + TLS configuration
├── rbac.yaml                  # Service accounts and roles
├── security-policies.yaml     # Network policies + PDB
└── resource-quota.yaml        # Resource limits
```

## Architecture

### Components

1. **Frontend**: 2 replicas, served via NGINX
2. **Backend**: 3-10 replicas (autoscaled), with Docker socket access
3. **PostgreSQL**: 1 replica StatefulSet with persistent storage
4. **Redis**: 1 replica for session caching
5. **Jupyter Sessions**: Dynamic pods with GPU allocation

### Networking

- **Frontend**: `colab.neuais.com` → frontend-service:80
- **Backend**: `api.colab.neuais.com` → backend-service:5000
- **TLS**: Automatic via Let's Encrypt + cert-manager
- **WebSocket**: Enabled for real-time collaboration

### GPU Management

- GPU nodes labeled with `nvidia.com/gpu=true`
- Jupyter pods request `nvidia.com/gpu: 1`
- Node selector ensures GPU pod placement
- ResourceQuota limits max GPUs to 8

### Storage

- **postgres-pvc**: 50Gi SSD for database
- **workspaces-pvc**: 500Gi shared storage for user notebooks
- **datasets-pvc**: 1Ti shared storage for datasets

### Security

- **NetworkPolicy**: Isolates pods, restricts traffic
- **RBAC**: Backend can create/delete Jupyter pods
- **PodDisruptionBudget**: Ensures high availability
- **ResourceQuota**: Prevents resource exhaustion
- **Secrets**: JWT and DB passwords stored securely

## Monitoring

### Add Prometheus Monitoring

```bash
# Install Prometheus Operator
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### ServiceMonitor for Backend

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: backend-metrics
  namespace: neuais-colab
spec:
  selector:
    matchLabels:
      app: backend
  endpoints:
  - port: http
    path: /metrics
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend -n neuais-colab --replicas=5

# Scale frontend
kubectl scale deployment frontend -n neuais-colab --replicas=3
```

### Auto-scaling

Backend includes HorizontalPodAutoscaler:
- Min: 3 replicas
- Max: 10 replicas
- CPU threshold: 70%
- Memory threshold: 80%

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n neuais-colab

# View logs
kubectl logs <pod-name> -n neuais-colab

# Check events
kubectl get events -n neuais-colab --sort-by='.lastTimestamp'
```

### GPU Allocation Issues

```bash
# Verify GPU nodes
kubectl get nodes -o json | jq '.items[] | {name:.metadata.name, gpus:.status.allocatable."nvidia.com/gpu"}'

# Check GPU operator
kubectl get pods -n gpu-operator
```

### Database Connection Issues

```bash
# Test PostgreSQL connectivity
kubectl run -it --rm psql-test --image=postgres:15 --restart=Never -n neuais-colab -- \
  psql -h postgres-service -U neuais -d neuais_colab
```

### Ingress Not Working

```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check cert-manager
kubectl get certificates -n neuais-colab
kubectl describe certificate neuais-colab-tls -n neuais-colab
```

## Backup and Restore

### Database Backup

```bash
# Create backup
kubectl exec -n neuais-colab postgres-0 -- \
  pg_dump -U neuais neuais_colab > backup.sql

# Restore backup
kubectl exec -i -n neuais-colab postgres-0 -- \
  psql -U neuais neuais_colab < backup.sql
```

### Workspace Backup

```bash
# Backup PVC data
kubectl cp neuais-colab/<backend-pod>:/data/workspaces ./workspaces-backup
```

## Update Strategy

```bash
# Rolling update backend
kubectl set image deployment/backend backend=neuais/colab-backend:v2.0 -n neuais-colab

# Check rollout status
kubectl rollout status deployment/backend -n neuais-colab

# Rollback if needed
kubectl rollout undo deployment/backend -n neuais-colab
```

## Cost Optimization

1. **Use Preemptible/Spot instances** for non-critical pods
2. **Auto-scale down** during off-hours
3. **Use node pools** - separate GPU and CPU node pools
4. **Monitor resource usage** with Prometheus
5. **Set appropriate resource requests/limits**

## Production Checklist

- [ ] GPU nodes labeled and tainted
- [ ] Storage classes configured
- [ ] Secrets updated with secure values
- [ ] DNS records pointing to ingress
- [ ] TLS certificates issued
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Resource quotas reviewed
- [ ] Network policies tested
- [ ] Load testing completed
- [ ] Disaster recovery plan documented

## Support

For issues or questions, refer to:
- Project README: [README.md](../../README.md)
- Implementation Plan: Check artifacts directory
- Kubernetes Documentation: https://kubernetes.io/docs/
