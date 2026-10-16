# Neo Deployment on Nebius

## Overview

This guide explains how to deploy Neo with NVIDIA NIM integration on Nebius Token Factory or Nebius AI Cloud for the hackathon.

Neo can run in two configurations on Nebius:
1. **Token Factory** - Serverless model inference (simple, scalable)
2. **AI Cloud** - Full container deployment (more control, persistent)

## Prerequisites

### Local Development

- Python 3.10+
- pip / virtualenv
- Docker (optional)
- NVIDIA NIM endpoint (local or cloud)

### Cloud Deployment (Nebius)

- Nebius account with Token Factory or AI Cloud access
- NVIDIA API credentials (from https://api.nims.nebius.ai)
- Supabase account (optional, for cloud activity log storage)
- Docker (for building container images)

## Quick Start

### 1. Local Development Setup

```bash
# Clone repository
git clone https://github.com/jaykrishna316/Neo
cd Neo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env.local
# Edit .env.local with your NVIDIA NIM endpoint and API key
```

### 2. Test with Local NVIDIA NIM

```bash
# Option A: Run NVIDIA NIM Docker locally (requires GPU)
docker run -it --rm --gpus all \
  -p 8000:8000 \
  nvcr.io/nim/nvidia/nemotron-4-340b-instruct:latest

# Option B: Use Nebius NIM Cloud endpoint
# Set in .env.local:
# NVIDIA_NIM_ENDPOINT=https://api.nims.nebius.ai/v1/...
# NVIDIA_NIM_API_KEY=your-api-key
```

### 3. Verify Installation

```bash
# Test Neo MCP server
python3 -m ide.mcp_neo_server

# In another terminal, test connection
python3 -c "
from core.agent_adapter_nvidia import create_nvidia_adapter
adapter = create_nvidia_adapter()
print('✓ Adapter initialized successfully')
"

# Test multi-agent coordination
python3 demo/multi_agent_oauth2_demo.py
```

## Docker Deployment

### Build Docker Image

```bash
# Build image
docker build -t neo:latest .
docker build -t neo:hackathon .

# Tag for Nebius registry
docker tag neo:latest \
  registry.nebius.ai/your-account/neo:latest
```

### Run Locally with Docker

```bash
# Run Neo MCP server
docker run -it --rm \
  -e NVIDIA_NIM_ENDPOINT="http://host.docker.internal:8000" \
  -e NVIDIA_NIM_MODEL="nemotron-4-340b-instruct" \
  -p 8000:8000 \
  neo:latest

# Run with Nebius NVIDIA NIM endpoint
docker run -it --rm \
  -e NVIDIA_NIM_ENDPOINT="https://api.nims.nebius.ai/v1/..." \
  -e NVIDIA_NIM_API_KEY="your-api-key" \
  -e NVIDIA_NIM_MODEL="nemotron-4-340b-instruct" \
  -p 8000:8000 \
  neo:latest

# Mount activity log (persistent across restarts)
docker run -it --rm \
  -v neo-logs:/app/.devsync \
  -e NVIDIA_NIM_ENDPOINT="..." \
  -e NVIDIA_NIM_API_KEY="..." \
  -p 8000:8000 \
  neo:latest
```

## Nebius Token Factory Deployment

### 1. Push Docker Image to Nebius Registry

```bash
# Login to Nebius registry
docker login registry.nebius.ai

# Tag image
docker tag neo:latest \
  registry.nebius.ai/your-account/neo:latest

# Push image
docker push registry.nebius.ai/your-account/neo:latest
```

### 2. Create Token Factory Configuration

Create `nebius-deploy.yaml`:

```yaml
apiVersion: serverless.nebius.ai/v1alpha1
kind: ServerlessFunction
metadata:
  name: neo-coordinator
  namespace: default
spec:
  image: registry.nebius.ai/your-account/neo:latest
  
  # Resource limits
  cpu: 1
  memory: 2Gi
  timeout: 300
  
  # Environment variables
  env:
    - name: NVIDIA_NIM_ENDPOINT
      value: "https://api.nims.nebius.ai/v1/..."
    - name: NVIDIA_NIM_MODEL
      value: "nemotron-4-340b-instruct"
    - name: ACTIVITY_LOG_MODE
      value: "supabase"
    - name: SUPABASE_URL
      valueFrom:
        secretKeyRef:
          name: supabase-config
          key: url
    - name: SUPABASE_KEY
      valueFrom:
        secretKeyRef:
          name: supabase-config
          key: key
  
  # Port exposure
  ports:
    - containerPort: 8000
      name: mcp
  
  # Networking
  public: true
  
  # Scaling
  minReplicas: 1
  maxReplicas: 3
  targetCPUUtilizationPercentage: 70
```

### 3. Create Secrets in Nebius

```bash
# Create secret for NVIDIA API key
nebius secret create nvidia-credentials \
  --api-key="your-nvidia-api-key"

# Create secret for Supabase
nebius secret create supabase-config \
  --url="https://your-project.supabase.co" \
  --key="your-anon-key"
```

### 4. Deploy to Nebius Token Factory

```bash
# Install Nebius CLI (if not already installed)
pip install nebius-cli

# Login to Nebius
nebius auth login

# Deploy function
nebius serverless deploy nebius-deploy.yaml

# Check deployment status
nebius serverless get neo-coordinator

# View logs
nebius serverless logs neo-coordinator --follow

# Get public endpoint
nebius serverless endpoint neo-coordinator
```

## Nebius AI Cloud Deployment (Kubernetes)

### 1. Prepare Kubernetes Manifests

Create `nebius-k8s.yaml`:

```yaml
---
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: neo-hackathon

---
# Secret: NVIDIA API Key
apiVersion: v1
kind: Secret
metadata:
  name: nvidia-credentials
  namespace: neo-hackathon
type: Opaque
stringData:
  api-key: "your-nvidia-api-key"

---
# Secret: Supabase Config
apiVersion: v1
kind: Secret
metadata:
  name: supabase-config
  namespace: neo-hackathon
type: Opaque
stringData:
  url: "https://your-project.supabase.co"
  key: "your-anon-key"
  service-key: "your-service-role-key"

---
# ConfigMap: Neo Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: neo-config
  namespace: neo-hackathon
data:
  NVIDIA_NIM_ENDPOINT: "https://api.nims.nebius.ai/v1/..."
  NVIDIA_NIM_MODEL: "nemotron-4-340b-instruct"
  ACTIVITY_LOG_MODE: "supabase"
  NEO_MULTITENANCY: "false"
  CLAUDE_TENANT_ID: "default"
  LOG_LEVEL: "INFO"

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo-coordinator
  namespace: neo-hackathon
spec:
  replicas: 2
  selector:
    matchLabels:
      app: neo-coordinator
  template:
    metadata:
      labels:
        app: neo-coordinator
    spec:
      containers:
      - name: neo
        image: registry.nebius.ai/your-account/neo:latest
        ports:
        - containerPort: 8000
          name: mcp
        env:
        - name: NVIDIA_NIM_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: neo-config
              key: NVIDIA_NIM_ENDPOINT
        - name: NVIDIA_NIM_API_KEY
          valueFrom:
            secretKeyRef:
              name: nvidia-credentials
              key: api-key
        - name: NVIDIA_NIM_MODEL
          valueFrom:
            configMapKeyRef:
              name: neo-config
              key: NVIDIA_NIM_MODEL
        - name: ACTIVITY_LOG_MODE
          valueFrom:
            configMapKeyRef:
              name: neo-config
              key: ACTIVITY_LOG_MODE
        - name: SUPABASE_URL
          valueFrom:
            secretKeyRef:
              name: supabase-config
              key: url
        - name: SUPABASE_KEY
          valueFrom:
            secretKeyRef:
              name: supabase-config
              key: key
        
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 4Gi
        
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: neo-coordinator
  namespace: neo-hackathon
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: neo-coordinator

---
# HorizontalPodAutoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: neo-coordinator
  namespace: neo-hackathon
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: neo-coordinator
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2. Deploy to Nebius AI Cloud

```bash
# Create namespace and deploy
kubectl apply -f nebius-k8s.yaml

# Watch deployment progress
kubectl -n neo-hackathon get deployments -w

# Check pod status
kubectl -n neo-hackathon get pods

# View logs
kubectl -n neo-hackathon logs -f deployment/neo-coordinator

# Get LoadBalancer endpoint
kubectl -n neo-hackathon get svc neo-coordinator
# Wait for EXTERNAL-IP to be assigned (may take a few minutes)
```

## Supabase Cloud Storage Setup (Optional)

For cloud deployments, use Supabase for persistent activity log storage:

### 1. Create Supabase Project

```bash
# Go to https://app.supabase.com
# Create new project with:
# - Database password: (auto-generated, save it)
# - Region: Closest to your Nebius region
# - Pricing: Free or Pro
```

### 2. Create Activity Log Table

```sql
-- In Supabase SQL Editor
CREATE TABLE activity_logs (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  tenant_id TEXT NOT NULL,
  developer_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  intent TEXT,
  lock_state TEXT,
  queue_position INTEGER,
  agent_metadata JSONB,
  region TEXT,
  intent_category TEXT
);

-- Create indexes for fast queries
CREATE INDEX activity_logs_tenant_idx ON activity_logs(tenant_id);
CREATE INDEX activity_logs_file_path_idx ON activity_logs(file_path);
CREATE INDEX activity_logs_developer_id_idx ON activity_logs(developer_id);
CREATE INDEX activity_logs_created_at_idx ON activity_logs(created_at DESC);

-- Enable Row Level Security
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
```

### 3. Update Neo Configuration

```bash
# Set in .env or deployment config:
ACTIVITY_LOG_MODE=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-public-key
SUPABASE_SERVICE_KEY=your-service-role-key  # Server-side only
```

## Verification & Testing

### Health Check

```bash
# Check deployment health
curl -X GET http://your-deployed-endpoint:8000/health

# Expected response:
# {"status": "healthy", "version": "4.1"}
```

### Test Agent Coordination

```bash
# Run multi-agent demo against cloud deployment
export NVIDIA_NIM_ENDPOINT="https://your-deployed-endpoint"
python3 demo/multi_agent_oauth2_demo.py
```

### Monitor Activity Log

```bash
# Watch activity log in real-time (file-based)
python3 scripts/watch_activity_log.py --follow --pretty

# Or query Supabase activity logs
python3 -c "
from core.storage.supabase_storage import SupabaseActivityLogStorage

storage = SupabaseActivityLogStorage(
    url='https://your-project.supabase.co',
    key='your-anon-key'
)

entries = storage.list_entries(limit=50)
for entry in entries:
    print(f\"{entry['created_at']}: {entry['developer_id']} on {entry['file_path']}\")
"
```

## Troubleshooting

### Pod/Function Won't Start

**Error: ImagePullBackOff**

```bash
# Check image exists in registry
docker images | grep neo

# Re-push if needed
docker tag neo:latest registry.nebius.ai/your-account/neo:latest
docker push registry.nebius.ai/your-account/neo:latest

# Verify pull secret
kubectl describe pod <pod-name> -n neo-hackathon
```

**Error: CrashLoopBackOff**

```bash
# Check logs for errors
kubectl logs <pod-name> -n neo-hackathon

# Common causes:
# 1. Missing environment variables
# 2. NVIDIA NIM endpoint unreachable
# 3. Supabase credentials invalid
```

### NVIDIA NIM Connection Issues

```bash
# Test NVIDIA endpoint connectivity
curl -X GET https://api.nims.nebius.ai/v1/health \
  -H "Authorization: Bearer YOUR_API_KEY"

# Check Nebius network policies
# May need to whitelist NVIDIA API domain
```

### Supabase Connection Issues

```bash
# Test Supabase connectivity
curl -X GET "https://your-project.supabase.co/rest/v1/activity_logs?limit=1" \
  -H "apikey: your-anon-key" \
  -H "Authorization: Bearer your-anon-key"
```

## Monitoring & Metrics

### Prometheus Metrics (Optional)

Enable metrics export:

```bash
export METRICS_ENABLED=true
export METRICS_PORT=9090

# Metrics will be available at: http://localhost:9090/metrics
```

### Nebius Cloud Monitoring

```bash
# View deployment metrics
nebius serverless metrics neo-coordinator \
  --metric cpu \
  --metric memory \
  --metric requests \
  --duration 1h

# Or in Kubernetes:
kubectl top pod -n neo-hackathon
```

## Cleanup

### Remove Nebius Token Factory Deployment

```bash
nebius serverless delete neo-coordinator
nebius secret delete nvidia-credentials
nebius secret delete supabase-config
```

### Remove Kubernetes Deployment

```bash
kubectl delete namespace neo-hackathon
```

### Clean Local Docker

```bash
docker rmi neo:latest
docker rmi registry.nebius.ai/your-account/neo:latest
docker volume rm neo-logs
```

## Production Considerations

### Security

- [ ] Use secrets management (Nebius Secrets, Kubernetes Secrets)
- [ ] Enable API authentication for Neo endpoints
- [ ] Use HTTPS only
- [ ] Restrict Supabase access with RLS policies
- [ ] Rotate API keys regularly
- [ ] Monitor for unauthorized access

### Scalability

- [ ] Use load balancer (automatic in Nebius)
- [ ] Configure auto-scaling based on CPU/memory
- [ ] Use Supabase for distributed activity log
- [ ] Monitor lock contention (activity log statistics)

### Reliability

- [ ] Enable health checks
- [ ] Set up monitoring/alerting
- [ ] Configure backups for Supabase
- [ ] Plan disaster recovery

### Cost Optimization

- [ ] Use appropriate resource requests/limits
- [ ] Monitor Nebius billing
- [ ] Consider reserved instances for consistent traffic
- [ ] Optimize NVIDIA NIM usage patterns

## Support & Resources

- **Neo Documentation**: See `../README.md`
- **Nebius Documentation**: https://nebius.ai/docs
- **NVIDIA NIM**: https://www.nvidia.com/en-us/nvidia-nims/
- **Supabase**: https://supabase.com/docs

## FAQ

**Q: Can I run Neo without Nebius?**  
A: Yes! Neo runs on any Docker-compatible environment. The Nebius setup is for hackathon convenience.

**Q: Do I need Supabase for production?**  
A: File-based activity log works for single-instance deployments. Supabase enables distributed multi-instance coordination.

**Q: What's the cost of running Neo on Nebius?**  
A: Check Nebius Token Factory pricing. Basic deployments may qualify for free tier/credits.

**Q: Can I use a different storage backend?**  
A: Yes! Neo's storage abstraction supports file, Supabase, and custom backends. See `core/storage/` for implementation examples.
