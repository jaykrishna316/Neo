# Repository Structure Reorganization Guide

## Current vs. Proposed Structure

This guide shows how to organize the Neo repository for better discoverability and user experience.

---

## Current Structure (Flat)

```
Neo/
├── README.md
├── *.md (15+ docs)
├── *.py (10+ implementation files)
├── marketing/
│   ├── medium_article_v2.md
│   └── linkedin_post_v2.md
├── docs/
│   └── ...
├── examples/
│   └── ...
└── Other scattered files
```

**Problem:** New users are overwhelmed by 30+ files in root. Hard to find what they need.

---

## Proposed Structure

```
Neo/
│
├── 📖 README.md                          ← START HERE
├── 📖 QUICKSTART.md                      ← 5-min setup guide
│
├── 📁 docs/                              ← Complete Documentation
│   ├── 01-OVERVIEW.md                    ← Neo overview
│   ├── 02-GETTING_STARTED.md             ← Setup & installation
│   ├── 03-ARCHITECTURE.md                ← System design
│   ├── 04-CONFLICT_DETECTION.md          ← How detection works
│   ├── 05-ENFORCEMENT_GATES.md           ← Gate mechanism
│   ├── 06-GIT_INTEGRATION.md             ← Git as harness
│   ├── 07-API_REFERENCE.md               ← API endpoints
│   ├── 08-DEPLOYMENT.md                  ← Production deployment
│   ├── 09-TROUBLESHOOTING.md             ← Common issues
│   └── 10-FAQ.md                         ← Frequently asked questions
│
├── 📁 core/                              ← Core Implementation
│   ├── __init__.py
│   ├── conflict_scorer.py                ← Conflict risk scoring
│   ├── semantic_detector.py              ← AST-based detection
│   ├── enforcement_gates.py              ← Three-tier gates
│   ├── coordination_machine.py           ← State machine
│   ├── git_harness.py                    ← Git integration
│   └── activity_log.py                   ← Event logging
│
├── 📁 agents/                            ← Agent Integration
│   ├── __init__.py
│   ├── agent_registry.py                 ← Agent management
│   ├── claude_integration.py             ← Anthropic Claude
│   ├── openai_integration.py             ← OpenAI integration
│   ├── gemini_integration.py             ← Google Gemini
│   ├── llama_integration.py              ← Meta Llama
│   └── custom_agent.py                   ← Custom agent template
│
├── 📁 storage/                           ← Storage Backends
│   ├── __init__.py
│   ├── redis_backend.py                  ← Redis implementation
│   ├── postgres_backend.py               ← PostgreSQL implementation
│   ├── mongodb_backend.py                ← MongoDB implementation
│   ├── s3_backend.py                     ← AWS S3 backend
│   └── abstract_backend.py               ← Base storage interface
│
├── 📁 security/                          ← Security & Auth
│   ├── __init__.py
│   ├── oauth2_provider.py                ← OAuth2 implementation
│   ├── mtls_handler.py                   ← mTLS support
│   ├── api_key_manager.py                ← API key management
│   ├── encryption.py                     ← Encryption utilities
│   └── rate_limiter.py                   ← Rate limiting
│
├── 📁 api/                               ← REST API
│   ├── __init__.py
│   ├── routes.py                         ← API endpoints
│   ├── middleware.py                     ← Auth, logging
│   ├── schemas.py                        ← Request/response models
│   └── openapi.py                        ← OpenAPI/Swagger
│
├── 📁 deploy/                            ← Deployment Files
│   ├── kubernetes/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── kustomization.yaml
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── terraform/
│   │   ├── aws/
│   │   ├── gcp/
│   │   └── azure/
│   ├── helm/
│   │   └── neo-chart/
│   └── scripts/
│       ├── install.sh
│       ├── deploy.sh
│       └── rollback.sh
│
├── 📁 examples/                          ← Usage Examples
│   ├── basic_coordination.py
│   ├── multi_agent_flow.py
│   ├── conflict_resolution_flow.py
│   └── git_webhook_handler.py
│
├── 📁 tests/                             ← Test Suite
│   ├── unit/
│   │   ├── test_conflict_detector.py
│   │   ├── test_enforcement_gates.py
│   │   └── test_state_machine.py
│   ├── integration/
│   │   ├── test_git_integration.py
│   │   ├── test_agent_coordination.py
│   │   └── test_api_endpoints.py
│   ├── performance/
│   │   ├── bench_conflict_detection.py
│   │   └── bench_state_machine.py
│   └── conftest.py
│
├── 📁 marketing/                         ← Marketing & Presentation
│   ├── README.md                         ← Marketing overview
│   ├── landing-page/
│   │   └── index.html
│   ├── linkedin/
│   │   ├── posts.md
│   │   └── carousel.md
│   ├── medium/
│   │   ├── article-1.md
│   │   └── article-2.md
│   ├── case-studies/
│   │   ├── case-study-1.md
│   │   └── case-study-2.md
│   ├── whitepapers/
│   │   └── neo-architecture.pdf
│   └── assets/
│       ├── logo.svg
│       ├── banner.png
│       └── diagrams/
│
├── 📁 .claude/                           ← Claude Code Config
│   ├── CLAUDE.md                         ← Project docs
│   └── settings.json                     ← Claude settings
│
├── 📁 .github/                           ← GitHub Config
│   ├── workflows/
│   │   ├── ci.yml                        ← CI/CD pipeline
│   │   ├── tests.yml
│   │   └── deploy.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.md
│   │   └── feature.md
│   └── PULL_REQUEST_TEMPLATE.md
│
├── 📄 ENTERPRISE_ADOPTION.md             ← Enterprise guide (NEW)
├── 📄 ARCHITECTURE.md                    ← High-level design
├── 📄 API.md                             ← API documentation
├── 📄 DEPLOYMENT.md                      ← Deployment guide
├── 📄 CONTRIBUTING.md                    ← Contribution guidelines
├── 📄 LICENSE                            ← MIT/Apache license
├── 📄 pyproject.toml                     ← Python package config
├── 📄 requirements.txt                   ← Dependencies
├── 📄 .gitignore
└── 📄 .env.example                       ← Environment template
```

---

## File Migration Plan

### Keep in Root (Critical for Users)

```
README.md                    ← Project overview
QUICKSTART.md               ← 5-minute setup
ENTERPRISE_ADOPTION.md      ← NEW: Enterprise guide
ARCHITECTURE.md             ← System overview
LICENSE
pyproject.toml
requirements.txt
.gitignore
.env.example
```

### Move to `/docs/` (Comprehensive Documentation)

```
From Root → To docs/

AGENT_INTEGRATION_GUIDE.md           → docs/05-AGENT_INTEGRATION.md
AGENT_INTEGRATION_SUMMARY.md         → docs/03-ARCHITECTURE.md (merge)
CONFLICT_WARNING_POC.md              → docs/04-CONFLICT_DETECTION.md
TECHNICAL_ROADMAP.md                 → docs/ROADMAP.md
ENFORCEMENT_GATES_SUMMARY.md         → docs/05-ENFORCEMENT_GATES.md
ENHANCED_ACTIVITY_LOG.md             → docs/08-LOGGING.md
DESIGN_SYSTEM.md                     → docs/DESIGN_SYSTEM.md
FUTURISTIC_UI_SUMMARY.md             → docs/UI.md
OPTIMIZATIONS_SUMMARY.md             → docs/PERFORMANCE.md
DELIVERY_SUMMARY.md                  → docs/RELEASE_NOTES.md
IMPLEMENTATION_SUMMARY.md            → docs/IMPLEMENTATION.md
NEO_COORDINATION_EVIDENCE.md          → docs/VALIDATION.md
DEMO_SCENARIOS.md                    → docs/TUTORIALS.md
TEST.md                              → docs/TESTING.md
```

### Move to `/core/` (Implementation)

```
From Root → To core/

conflict_scoring.py                  → core/conflict_scorer.py
semantic_conflict_detector.py        → core/semantic_detector.py
coordination_state_machine.py        → core/coordination_machine.py
enforcement_gates_summary.py         → core/enforcement_gates.py
activity_log.py                      → core/activity_log.py
git_integration.py                   → core/git_harness.py
```

### Move to `/agents/` (Agent Integration)

```
From Root → To agents/

agent_integration.py                 → agents/agent_registry.py
expertise_matcher.py                 → agents/expertise_matcher.py
intent_classifier.py                 → agents/intent_classifier.py
developer_patterns.py                → agents/patterns.py
```

### Move to `/examples/` (Usage Examples)

```
From Root → To examples/

cli_simulation.py                    → examples/cli_demo.py
empirical_validation.py              → examples/validation_example.py
ui_dashboard.html                    → examples/dashboard.html
neo_linkedin_carousel.html           → examples/carousel.html
```

### Move to `/marketing/` (Marketing Assets)

```
From Root → To marketing/

neo_linkedin_carousel.html           → marketing/linkedin/carousel.html
neo-article-updated.html             → marketing/medium/article.html
neo_carousel_professional.html       → marketing/linkedin/carousel-pro.html
Neo_LinkedIn_Carousel.pdf            → marketing/whitepapers/carousel.pdf
```

### Archive / Delete (Pre-generation artifacts)

```
Pre-generation files (delete or archive):

create_carousel_pdf.py               → Archive to /archive/ (unused)
create_docx.py                       → Archive to /archive/ (unused)
create_linkedin_carousel.py          → Archive to /archive/ (unused)
generate_proper_pdf.py               → Archive to /archive/ (unused)
create_pdf_direct.py                 → Archive to /archive/ (unused)
```

### Keep Only Config Files

```
Do NOT move (essential infrastructure):

.gitignore
.env.example
.devsync/
.github/
.claude/
deploy/
tests/
```

---

## Benefits of New Structure

| Aspect | Before | After |
|--------|--------|-------|
| **User Onboarding** | 30+ files in root | 3 files: README, QUICKSTART, ENTERPRISE |
| **Documentation** | Scattered across root | Organized in `/docs/` |
| **Code Discovery** | Mixed with docs | Separated in `/core/`, `/agents/`, `/storage/` |
| **Deployment** | Unclear | Clear `/deploy/` structure with all options |
| **Examples** | None | `/examples/` with common patterns |
| **Testing** | Mixed | Organized `/tests/` structure |
| **Maintenance** | Hard to navigate | Clear file organization |

---

## Migration Steps

### Step 1: Create Folder Structure
```bash
mkdir -p docs core agents storage security api deploy/{kubernetes,docker,terraform,helm,scripts} examples tests/{unit,integration,performance} marketing/{linkedin,medium,case-studies,whitepapers,assets}
```

### Step 2: Move Files
```bash
# Documentation
mv AGENT_INTEGRATION_GUIDE.md docs/03-AGENT_INTEGRATION.md
mv CONFLICT_WARNING_POC.md docs/04-CONFLICT_DETECTION.md
# ... (continue with other files)

# Core implementation
mv conflict_scoring.py core/
mv semantic_conflict_detector.py core/
# ... etc
```

### Step 3: Create Index Files
```bash
# Create docs/README.md that links all docs
# Create core/__init__.py with exports
# Create examples/README.md with descriptions
```

### Step 4: Update Imports
```bash
# Update all Python imports to reflect new structure
find . -name "*.py" -exec sed -i 's/from conflict_scoring/from core.conflict_scorer/' {} \;
# ... etc
```

### Step 5: Update Documentation
```bash
# Update README.md with new structure
# Update QUICKSTART.md with folder navigation
# Create CONTRIBUTING.md with developer guide
```

---

## Directory-Specific Details

### `/docs/`
- Numbered for reading order (01-, 02-, etc.)
- Each file ~5-10 pages
- Cross-links between files
- Search index generated

### `/core/`
- Core coordination logic
- No external dependencies (except standard library + specified packages)
- 100% test coverage target
- Clear exports in `__init__.py`

### `/deploy/`
- Infrastructure-as-Code ready
- Multi-cloud support (AWS, GCP, Azure, On-prem)
- Scripts for quick setup
- CI/CD templates

### `/examples/`
- Runnable Python scripts
- Each example: single use case
- Clear comments and docstrings
- README with descriptions

### `/marketing/`
- Landing pages
- Social media content
- Case studies
- Whitepapers & assets

---

## New User Experience

### Before (Overwhelming)
```
User visits repo → Sees 40+ files → Confused → "Where do I start?"
```

### After (Clear Path)
```
User visits repo → README.md (2 min read)
                → QUICKSTART.md (5 min setup)
                → docs/02-GETTING_STARTED.md (deeper dive)
                → docs/03-ARCHITECTURE.md (understand design)
                → examples/ (see it in action)
                → Deploy to production
```

---

## Implementation Timeline

- **Week 1:** Create folder structure, move files
- **Week 2:** Update imports, test everything
- **Week 3:** Update documentation, create index files
- **Week 4:** Update marketing materials, test user onboarding
- **Week 5:** Merge to main branch, communicate changes

---

## Questions to Consider

1. Should we keep `/examples/` as `.py` or add Jupyter notebooks?
2. Should deployment be organized by cloud provider or deployment method?
3. Do we want a `/plugins/` folder for custom extensions?
4. Should `tests/` be at root or inside `core/`?

---

**Recommendation:** Implement immediately before enterprise evaluation begins. Clear structure = professional impression. 🎯
