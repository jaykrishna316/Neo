# Neo MCP Deployment Models & SaaS Roadmap

**Status:** MVP = Self-Hosted | Future = SaaS Potential

---

## Executive Summary

**Current Model (MVP):** Self-hosted in enterprise infrastructure  
**Future Model (Optional):** Hosted SaaS with API keys (like Figma/Jira)  
**Timeline:** Self-hosted first; SaaS as follow-on revenue stream

The multitenancy architecture is **model-agnostic** — the same codebase supports both deployment approaches. This document outlines the path from self-hosted to SaaS when ready.

---

## Current State: Self-Hosted Model

### What Enterprises Get Today

**Three deployment options:**
1. **Per-tenant containers** — OS-level isolation, separate resource limits
2. **Kubernetes** — Enterprise multi-tenant orchestration
3. **Shared repo** — Cost-efficient, single container, app-level isolation

**Authentication:** Environment variables only (`CLAUDE_TENANT_ID`, `NEO_MULTITENANCY=true`)

**Scope:** One enterprise, multiple teams/departments  
**Control:** Enterprise owns infrastructure, scaling, monitoring  
**Data:** Stays in enterprise network  

### Why Self-Hosted First

✅ Lower barrier to entry (enterprises already manage similar tools)  
✅ No hosted infrastructure cost  
✅ No billing complexity (yet)  
✅ Focuses on core multitenancy quality  
✅ Enterprises prefer data residency  

**Documentation:** See `docs/DEPLOYMENT_RUNBOOK.md` for setup procedures.

---

## Future Model: SaaS Deployment

### Vision: "Neo MCP as a Service"

**When:** Phase 5+ (after self-hosted stabilizes in production)

**Model:** Hosted service serving multiple enterprise customers with API authentication

**Example flow:**
```
Enterprise A signs up
  ↓
Gets unique API key + tenant space
  ↓
Claude Code configured with:
  - MCP server URL: https://api.codeninja.io/mcp
  - API key header: Authorization: Bearer <api-key>
  ↓
Connects to hosted MCP server
  ↓
API authenticates → routes to Enterprise A's tenant
  ↓
App-level multitenancy (teams within Enterprise A)
```

### What Needs to Be Built

#### Phase 1: API Wrapper (4-6 weeks)

**New components:**
- REST/GraphQL gateway over MCP server
- OpenAPI schema for MCP tool endpoints
- Authentication middleware (API keys)
- Request routing to tenant-scoped instances
- Rate limiting per API key

**Example endpoints:**
```
POST /mcp/call
{
  "tool": "neo_log_activity",
  "input": { "agent_id": "...", "file_path": "..." }
}
```

**Result:** MCP server becomes callable via HTTP, not just stdio

---

#### Phase 2: Multi-Customer Tenancy (6-8 weeks)

**Layer 2 of isolation:** Tenant ↔ Customer mapping

```
Database (PostgreSQL/DynamoDB):
├── customers
│   ├── customer_id (acme-corp)
│   ├── api_key (hashed)
│   ├── created_at
│   └── subscription_tier (basic/pro/enterprise)
├── api_keys
│   ├── key_id
│   ├── customer_id (foreign key)
│   ├── secret (hashed)
│   └── permissions
└── tenant_mappings
    ├── tenant_id (acme-frontend, acme-backend)
    ├── customer_id (acme-corp)
    └── metadata
```

**New logic:**
- API key → customer_id lookup
- Validate requested tenant_id belongs to customer
- Enforce tenant quota (max tenants per customer)
- Activity logging (audit trail per customer)

**Result:** One hosted instance serves 100s of enterprise customers

---

#### Phase 3: Infrastructure & Ops (8-10 weeks)

**Deployment:**
- Kubernetes cluster (GKE / EKS / AKS)
- Auto-scaling based on API traffic
- Persistent storage (GCS / S3 for tenant data)
- PostgreSQL for metadata
- Redis for rate limiting / session caching

**Observability:**
- Prometheus metrics per customer
- CloudWatch / Datadog logs
- Alerts for quota violations, latency SLOs
- Customer dashboards (usage, performance)

**Security:**
- TLS everywhere (api.codeninja.io)
- API key rotation policies
- Tenant isolation verification (automated tests)
- Encryption at rest for customer data
- Compliance: SOC2, GDPR readiness

---

#### Phase 4: Billing & Provisioning (6-8 weeks)

**Signup flow:**
```
User visits app.codeninja.io
  ↓
Creates account (email/OAuth)
  ↓
Enters organization name (becomes primary tenant)
  ↓
Generates API key
  ↓
Downloads SDK / setup guide
  ↓
Configures Claude Code + MCP server URL
```

**Billing:**
- Usage-based: $/1000 operations or $/month flat fee
- Stripe integration for payments
- Usage tracking: activity logs, conflict checks, API calls
- Overage handling and notifications
- Invoicing & receipts

**Provisioning:**
- Self-service tenant creation (up to limit)
- Team management (invite users, assign tenants)
- Admin console (usage dashboard, logs, settings)

---

### Architecture Comparison

| Aspect | Self-Hosted | SaaS |
|--------|------------|------|
| **Infrastructure** | Enterprise owns | codeninja.io owns |
| **Auth** | Environment variables | API keys |
| **Scaling** | Manual per enterprise | Auto-scaled by us |
| **Data** | In enterprise network | In managed cloud |
| **Cost to customer** | $0 (they manage) | Usage-based $/month |
| **Support burden** | Low (self-service docs) | Higher (24/7 SLA) |
| **Multi-customer** | No | Yes |
| **Customization** | Full source access | Limited (API only) |

---

## Implementation Roadmap

### Phase 1: Self-Hosted (Current ✅ Complete)

**Status:** Production ready  
**What:** Multitenancy core, three deployment strategies, full docs  
**Timeline:** ✅ Done (Phases 1-4 complete)  
**Deliverables:**
- Core multitenancy (Phase 1-3 code)
- Integration & E2E tests (Phase 4)
- Deployment runbook + troubleshooting

**Next:** Market to enterprises for self-hosted adoption

---

### Phase 2: SaaS Foundation (Future - 6 months after Phase 1 stabilizes)

**Prerequisites:**
- ≥3 self-hosted customers in production
- Performance data from real workloads
- Feedback loop established
- Business case approved

**What:** API wrapper + multi-customer tenancy  
**Timeline:** 4-6 months (parallel work, 2-person team)  
**Deliverables:**
- REST API gateway over MCP
- Customer identity & API keys
- Tenant ↔ customer mapping
- Rate limiting & quota enforcement

**Success metric:** First beta customer can onboard in <1 day

---

### Phase 3: Production SaaS (Future - 3 months after Phase 2)

**Prerequisites:**
- API stable and tested
- Multi-customer isolation verified
- Kubernetes cluster operational
- Billing & provisioning working

**What:** Scale, ops, security, go-live  
**Timeline:** 3-4 months (1-2 ops engineers)  
**Deliverables:**
- Kubernetes deployment manifests
- Monitoring & alerting
- Runbook for incident response
- Security audit & compliance

**Success metric:** 10+ enterprise customers, 99.9% uptime SLA

---

## Decision Points

### For Phase 1 (Now): Stay Self-Hosted

**Recommendation:** Keep main branch clean (production-ready), iterate on `mpc-enablement` with self-hosted customers.

**Next steps:**
1. Merge `mpc-enablement` → main (when ready to release)
2. Package as Docker image + Helm chart
3. Publish to DockerHub, artifact registry
4. Market to first 3-5 beta customers
5. Collect production feedback

---

### For Phase 2 (6+ months): Go SaaS or Stay Focused?

**Questions to ask:**
- Do we have product-market fit self-hosted?
- Are customers asking for hosted option?
- Do we have 2-3 people available to build SaaS layer?
- Is the revenue potential worth ops overhead?

**If YES to all:** Start API wrapper work  
**If NO to any:** Stay focused on self-hosted, revisit in 12 months

---

## Risk Mitigation

### Self-Hosted Risks
- **Enterprises struggle to deploy** → Mitigate: Docker + Helm templates, setup support
- **Scalability issues in production** → Mitigate: E2E load tests before release
- **Poor adoption** → Mitigate: Sales/marketing focused on specific verticals

### SaaS Risks (Future)
- **Multi-customer isolation failure** → Mitigate: Security audits + pen testing
- **Scaling infrastructure issues** → Mitigate: Load testing before GA
- **High ops overhead** → Mitigate: Managed Kubernetes (GKE/EKS), auto-scaling
- **Compliance complexity** → Mitigate: SOC2 audit before marketing to enterprises

---

## Appendix: Deployment Model Comparison

### Model A: Self-Hosted (MVP ✅)

**Enterprise deploys in own infrastructure:**
```bash
# Enterprise runs this
docker run -e CLAUDE_TENANT_ID=team-a -e NEO_MULTITENANCY=true neo-mcp:latest
docker run -e CLAUDE_TENANT_ID=team-b -e NEO_MULTITENANCY=true neo-mcp:latest
```

**Pros:**
- Data stays in enterprise network
- No dependency on external service
- Full control over scaling/config
- Lower total cost of ownership (no SaaS fees)

**Cons:**
- Enterprise manages ops, scaling, backups
- Support burden on us (setup help)
- Harder to upsell

---

### Model B: SaaS Hosted (Future Option)

**codeninja.io hosts, enterprise uses via API key:**
```bash
# Enterprise configures once
export MCP_SERVER_URL=https://api.codeninja.io/mcp
export API_KEY=sk_live_abc123xyz
python3 -m core.mcp_server  # Connects to hosted backend
```

**Pros:**
- We handle ops, scaling, backups
- Easier onboarding (signup → API key → done)
- Usage-based billing (revenue potential)
- Can upsell higher tiers

**Cons:**
- Data leaves enterprise network
- Compliance/SOC2 required
- Higher operational burden on us
- Multi-customer complexity

---

### Model C: Hybrid (Optional)

**Offer both models, customer chooses:**
- Small teams → SaaS (low setup cost)
- Enterprises → Self-hosted (data residency)

**Pros:**
- Maximizes addressable market
- Different revenue models per segment

**Cons:**
- Double the ops burden
- Maintain parity between versions
- Complex support matrix

**Recommendation:** Start with A (self-hosted), add B (SaaS) if demand high.

---

## Next Steps

1. **Now:** Self-hosted with enterprise customers (Phase 1 complete)
2. **Month 3:** Collect feedback from 3-5 self-hosted deployments
3. **Month 6:** Decide: SaaS or stay focused?
4. **If SaaS:** Design API spec + data model for Phase 2
5. **If stay focused:** Double down on self-hosted adoption, expand customer base

---

**Owner:** Architecture team  
**Last Updated:** 2026-09-14  
**Branch:** mpc-enablement (ready to merge)

For deployment instructions, see `docs/DEPLOYMENT_RUNBOOK.md`  
For architecture details, see `docs/PHASE4_COMPLETION_REPORT.md`
