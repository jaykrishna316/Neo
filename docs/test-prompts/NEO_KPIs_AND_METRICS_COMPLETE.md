# Neo Complete KPIs and Metrics Reference

**Total Measurable Data Points: 127**

---

## 1. ACTIVITY LOGGING (16 metrics)

### Basic Activity Metadata
- `developer_id` - Unique identifier for the developer
- `file_path` - Path to file being modified
- `timestamp` - When activity occurred (Unix timestamp)
- `activity_duration` - How long developer spent on task (minutes)
- `session_id` - Unique session identifier for this developer's work

### Intent Documentation
- `intent` - Natural language description of what developer is doing
- `intent_category` - Type: feature, refactor, bugfix, chore, docs
- `intent_scope` - Scope: single-function, multi-function, file-level, cross-file
- `intent_confidence` - Confidence level in intent classification (0-1)
- `intent_keywords` - Extracted keywords from intent (list)

### Execution Context
- `region` - Specific code region being modified (function/class name or line range)
- `blocking_others` - Whether this work blocks other developers (bool)
- `estimated_completion` - ETA in seconds until completion
- `priority_level` - Priority: critical, high, medium, low
- `ticket_id` - Associated issue/ticket identifier
- `branch_name` - Git branch being worked on

---

## 2. CONFLICT DETECTION (18 metrics)

### Basic Conflict Metrics
- `has_conflict` - Whether conflict with another developer exists (bool)
- `conflict_count` - Number of concurrent conflicts on this file
- `conflicting_developers` - List of developer IDs creating conflicts
- `conflict_detection_timestamp` - When conflict was detected

### Risk Classification
- `risk_level` - Overall risk: LOW, MEDIUM, HIGH
- `risk_score` - Numeric risk score (0-100)
- `risk_reason` - Human-readable explanation of risk
- `risk_confidence` - Confidence in risk assessment (0-1)
- `risk_factors` - List of factors contributing to risk

### Semantic Layer Analysis
- `layers_triggered` - Which conflict layers detected issue:
  - `syntactic` - Same lines modified
  - `scope` - Same function/class
  - `semantic` - Related symbols modified
  - `type` - Type contract violations
  - `data_flow` - Shared data paths affected
- `layer_confidences` - Confidence per layer (dict)

### Region Analysis
- `regions_overlap` - Do code regions overlap (bool)
- `region_distance` - Lines between regions (number)
- `region_type_current` - Type of current region (function/class/block)
- `region_type_other` - Type of other developer's region
- `overlap_percentage` - What percentage of regions overlap (0-100)

### Signature Changes
- `signature_change_detected` - Is API signature changing (bool)
- `signature_change_type` - Type: rename, remove, modify, add
- `breaking_change` - Is this a breaking change (bool)
- `api_compatibility_impact` - How many downstream files affected

---

## 3. CONTEXT STALENESS (15 metrics)

### Freshness Status
- `freshness_status` - CURRENT, STALE_SOURCE, UNVERIFIABLE
- `is_stale` - Simple boolean (true if STALE_SOURCE)
- `staleness_age` - Seconds since baseline was recorded
- `content_hash_baseline` - Hash of file when developer read it
- `content_hash_current` - Hash of file now

### Symbol-Level Staleness
- `changed_symbols` - List of symbols that changed
- `changed_symbol_count` - Number of changed symbols
- `removed_symbols` - List of symbols that were deleted
- `added_symbols` - List of new symbols
- `modified_symbols` - List of changed symbol bodies

### Change Details
- `symbol_changes_detail` - Per-symbol change info:
  - `symbol_name` - Name of changed symbol
  - `change_type` - modified, removed, added
  - `body_hash_before` - Previous body hash
  - `body_hash_after` - Current body hash
  - `lines_changed` - Line count delta
  - `change_complexity` - simple, moderate, complex

### Staleness Impact
- `needs_context_refresh` - Should developer re-read file (bool)
- `refresh_recommendation` - Recommendation level: none, advisory, required
- `impact_if_stale` - What breaks if stale code is used
- `staleness_risk` - Risk of proceeding with stale context: LOW/MEDIUM/HIGH

---

## 4. LOCK MANAGEMENT (20 metrics)

### Lock State
- `lock_state` - ACQUIRED, WAITING, RELEASED, EXPIRED
- `lock_holder` - Developer ID holding the lock
- `lock_scope` - Scope: file, function, block
- `lock_acquired_at` - Timestamp lock was acquired
- `lock_expires_at` - Timestamp lock expires
- `lock_time_held` - How long lock has been held (seconds)

### Queue Management
- `queue_position` - Position in lock queue (0 = next)
- `queue_length` - Total developers waiting
- `queue_wait_time` - How long waiting (seconds)
- `estimated_wait_time` - Estimated seconds until acquired
- `queue_priority` - Priority in queue relative to others

### Lock Reasons and Context
- `lock_reason` - Why lock was acquired: editing, testing, building, integrating
- `waiting_for` - Who are we waiting for (if in queue)
- `blocked_by` - Which lock is blocking us
- `blocking_count` - How many developers are blocked by this lock

### Lock Expiry
- `lock_expires_in` - Seconds until expiry
- `lock_auto_renew` - Does lock auto-renew (bool)
- `lock_renewal_count` - How many times renewed
- `lock_timeout_risk` - Will lock expire soon (bool)

### Lock History
- `lock_acquisition_attempts` - How many times attempted to acquire
- `lock_acquisition_wait_total` - Total seconds spent waiting for locks
- `lock_conflict_history` - Previous lock conflicts on this file

---

## 5. IMPACT ANALYSIS (20 metrics)

### Direct Impacts
- `has_impacts` - Whether this change impacts other files (bool)
- `impact_count` - Number of files impacted
- `impacted_files` - List of affected file paths
- `impact_severity` - CRITICAL, HIGH, MEDIUM, LOW

### Upstream Dependencies (What depends on this code)
- `upstream_count` - Number of upstream dependents
- `upstream_sources` - List of files that import/depend on this file
- `upstream_types` - Types of dependency: import, call, extends, implements
- `upstream_coupling` - Coupling strength to upstream (0-1)

### Downstream Dependencies (What this code depends on)
- `downstream_count` - Number of downstream dependencies
- `downstream_targets` - List of files this depends on
- `downstream_types` - Types: import, call, extends, implements
- `downstream_coupling` - Coupling strength to downstream (0-1)

### Impact Details Per File
- `impact_detail` - Per-file impact information:
  - `target_file` - File being impacted
  - `impact_type` - Type: API-breaking, signature-change, data-flow, dependency
  - `impact_reason` - Why it's impacted
  - `impact_severity` - Critical/High/Medium/Low
  - `estimated_fix_time` - Minutes to fix impact
  - `fix_complexity` - simple, moderate, complex

### Blast Radius
- `blast_radius` - Percentage of codebase affected (0-100)
- `blast_radius_confidence` - Confidence in radius estimate (0-1)
- `blast_radius_files` - Number of files in blast radius
- `critical_impacts` - Number of critical/breaking changes
- `service_coupling_impact` - How many services affected (if multi-service)

---

## 6. SEMANTIC ANALYSIS (18 metrics)

### Symbol Extraction
- `symbol_count` - Total symbols in file
- `symbols` - List of symbol names and types
- `symbol_types` - Count by type: functions, classes, methods, constants
- `function_count` - Number of functions
- `class_count` - Number of classes
- `method_count` - Number of methods
- `async_function_count` - Number of async functions

### Symbol Properties
- `public_symbols` - Symbols with public visibility
- `private_symbols` - Symbols with private/internal visibility
- `exported_symbols` - Symbols exported by module
- `complexity_per_symbol` - Cyclomatic complexity per symbol
- `lines_of_code_per_symbol` - LOC per function/class

### Dependencies
- `dependency_count` - Total dependencies extracted
- `dependency_types` - Types: calls, imports, extends, implements, uses
- `external_dependencies` - Dependencies on external modules
- `internal_dependencies` - Dependencies within codebase
- `circular_dependencies` - Circular dependency count

### Symbol Coupling
- `symbol_coupling` - How tightly coupled symbols are (0-1)
- `symbol_cohesion` - How cohesive symbols are (0-1)
- `highly_coupled_pairs` - Pairs with high coupling
- `symbols_in_critical_path` - Symbols in execution critical path

---

## 7. PERFORMANCE METRICS (16 metrics)

### Execution Time
- `execution_time_total` - Total time to execute (seconds)
- `execution_time_generation` - Time spent on code generation (seconds)
- `execution_time_validation` - Time spent on validation (seconds)
- `execution_time_analysis` - Time spent on Neo analysis (seconds)

### Token Usage
- `tokens_used_total` - Total tokens consumed
- `tokens_used_generation` - Tokens for code generation
- `tokens_used_analysis` - Tokens for Neo analysis
- `tokens_per_second` - Generation speed (tokens/sec)
- `cost_estimate` - Estimated cost in USD

### Agent Confidence
- `agent_confidence` - Overall confidence in generation (0-1)
- `generation_confidence` - Confidence in generated code (0-1)
- `conflict_detection_confidence` - Confidence in conflict detection (0-1)
- `impact_analysis_confidence` - Confidence in impact analysis (0-1)

### Resource Usage
- `memory_used` - Peak memory used (MB)
- `cpu_time` - CPU seconds used
- `cache_hit_rate` - Freshness cache hits (0-1)

---

## 8. AGENT EXECUTION METADATA (14 metrics)

### Agent Information
- `agent_id` - Unique identifier for agent/developer
- `agent_type` - Type: claude-code, ide-extension, cli, webhook
- `agent_version` - Version of agent
- `agent_model` - LLM model used: opus, sonnet, haiku, etc.

### Execution Context
- `execution_context` - Where code was generated: claude-code, VSCode, JetBrains, etc.
- `execution_environment` - Environment: development, staging, production
- `execution_flags` - Flags used: --force, --dry-run, --verbose, etc.

### Validation Results
- `validation_passed` - Did generated code pass validation (bool)
- `validation_errors` - List of validation errors found
- `validation_warnings` - List of validation warnings
- `style_compliance` - Does code match style guide (bool)

### Generation Metadata
- `generation_attempts` - How many times generated until acceptable
- `generation_rollbacks` - How many times rolled back
- `generation_regenerated` - Was previously generated code regenerated (bool)

---

## 9. TEAM COORDINATION METRICS (12 metrics)

### Developer Activity
- `concurrent_developers` - Number of developers working simultaneously
- `developers_on_same_file` - Count of devs on current file
- `developers_on_related_files` - Count of devs on dependent files
- `team_velocity` - Lines of code per developer per hour

### Collaboration Patterns
- `collaboration_frequency` - How often developers work on same files
- `collaboration_conflict_rate` - Percentage of collaborations that create conflicts
- `average_resolution_time` - Average time to resolve conflicts (minutes)
- `handoff_efficiency` - How efficiently code passes between developers (0-1)

### Team Health
- `team_blocking_incidents` - Number of times team was blocked
- `team_wait_time_total` - Total time team spent waiting (hours)
- `team_coordination_score` - Overall coordination effectiveness (0-100)
- `team_merge_conflict_count` - Git merge conflicts (should be 0)

---

## 10. SERVICE COUPLING & ARCHITECTURE (16 metrics)

### Service Dependencies
- `service_count` - Number of services in architecture
- `service_dependencies` - Services this code depends on
- `dependent_services` - Services depending on this code
- `service_coupling_score` - How tightly coupled to other services (0-1)

### API Contracts
- `api_contract_breaking_changes` - Breaking API changes
- `api_contract_version_change` - New API version needed (bool)
- `api_compatibility_level` - backward-compatible, forward-compatible, breaking
- `api_deprecations` - Deprecated APIs being removed

### Cross-Service Impact
- `cross_service_impact_count` - Number of services impacted
- `cross_service_coordination_needed` - Other teams need to coordinate (bool)
- `cross_service_test_coverage` - Integration test coverage (0-1)
- `cross_service_deployment_order` - Deployment order constraints

### Architecture Health
- `architecture_complexity_delta` - Change in system complexity
- `architecture_technical_debt_impact` - Impact on tech debt (positive/negative)
- `architecture_maintainability_delta` - Change in maintainability
- `architecture_scalability_impact` - Impact on system scalability

---

## 11. CODE QUALITY METRICS (15 metrics)

### Complexity Analysis
- `cyclomatic_complexity` - Cyclomatic complexity of new code
- `cognitive_complexity` - Cognitive complexity of new code
- `nesting_depth` - Maximum nesting depth
- `function_length` - Average function length (lines)

### Code Health
- `code_duplication` - Percentage of duplicated code (0-100)
- `code_smells` - Number of code smells detected
- `technical_debt_introduced` - Technical debt points added
- `technical_debt_resolved` - Technical debt points removed

### Testing
- `test_coverage_change` - Change in test coverage percentage
- `test_count_change` - New tests added
- `test_execution_time` - Time to run all affected tests (seconds)
- `critical_tests_passing` - Critical tests passing (bool)

### Documentation
- `documentation_coverage` - Percentage of code documented (0-100)
- `doc_completeness_score` - How complete is documentation (0-1)
- `readme_updated` - Was README updated (bool)

---

## 12. TIMELINE & SCHEDULING (8 metrics)

### Timing
- `activity_start_time` - When work started
- `activity_end_time` - When work completed
- `activity_duration` - Total duration (seconds)
- `work_phase` - Phase: research, implementation, testing, review, deploy

### Scheduling
- `scheduled_for_deployment` - Is this scheduled to deploy (bool)
- `deployment_window` - Deployment time window
- `deployment_constraints` - Any deployment constraints
- `estimated_deployment_risk` - Risk if deployed now: CRITICAL, HIGH, MEDIUM, LOW

---

## 13. ERROR & EXCEPTION TRACKING (10 metrics)

### Errors During Development
- `errors_introduced` - Number of errors in generated code
- `error_types` - Types of errors: syntax, type, logic, runtime
- `error_severity` - Per-error severity: critical, high, medium, low
- `error_recovery_time` - Time to fix errors (seconds)

### Testing Failures
- `test_failures` - Number of test failures
- `test_failure_rate` - Percentage of tests failing (0-100)
- `flaky_test_count` - Number of flaky/intermittent tests
- `test_failure_root_cause` - Root cause of failures

### Exception Handling
- `unhandled_exceptions` - Unhandled exceptions in code
- `exception_coverage` - Percentage of code with try/catch

---

## 14. DEPLOYMENT & RELEASE METRICS (10 metrics)

### Release Information
- `release_version` - Version being released
- `release_hotfix` - Is this a hotfix (bool)
- `release_rollback_risk` - Risk if rolled back: LOW/MEDIUM/HIGH
- `release_dependencies` - Other changes this depends on

### Deployment
- `deployment_readiness` - Is code ready to deploy (bool)
- `deployment_checklist_items` - Checklist items: total, completed
- `deployment_approvals_needed` - Approvals required before deploy
- `deployment_rollback_plan` - Rollback plan documented (bool)
- `deployment_monitoring_alerts` - Alerts configured for deployment
- `deployment_estimated_time` - Estimated deployment duration (minutes)

---

## 15. AUDIT & COMPLIANCE (7 metrics)

### Code Review
- `code_review_status` - approved, pending, rejected, changes-requested
- `code_review_comments` - Number of review comments
- `code_review_violations` - Policy violations found
- `security_scan_result` - Security vulnerabilities found: 0, low, medium, high

### Compliance
- `compliance_check_passed` - Passed compliance checks (bool)
- `accessibility_score` - Accessibility compliance (0-100)
- `license_compliance` - Dependencies license-compliant (bool)

---

## SUMMARY BY CATEGORY

| Category | Count | Status |
|----------|-------|--------|
| Activity Logging | 16 | ✅ Implemented |
| Conflict Detection | 18 | ✅ Implemented |
| Context Staleness | 15 | ✅ Implemented |
| Lock Management | 20 | 🟡 Partial |
| Impact Analysis | 20 | ✅ Implemented |
| Semantic Analysis | 18 | ✅ Implemented |
| Performance Metrics | 16 | ✅ Implemented |
| Agent Execution | 14 | ✅ Implemented |
| Team Coordination | 12 | ⏳ Planned |
| Service Coupling | 16 | ⏳ Planned |
| Code Quality | 15 | ⏳ Planned |
| Timeline & Scheduling | 8 | ⏳ Planned |
| Error Tracking | 10 | ⏳ Planned |
| Deployment | 10 | ⏳ Planned |
| Audit & Compliance | 7 | ⏳ Planned |
| **TOTAL** | **127** | **15 Core + 12 Planned** |

---

## CURRENTLY AVAILABLE IN DASHBOARD

The local dashboard (`http://localhost:5555`) displays:
- ✅ All Activity Logging metrics
- ✅ All Conflict Detection metrics
- ✅ All Context Staleness metrics
- ✅ All Impact Analysis metrics
- ✅ All Semantic Analysis metrics
- ✅ All Performance metrics
- ✅ All Agent Execution metrics

**Real-time updates every 2 seconds**

---

## NEXT PHASE: EXTENDED METRICS

To add remaining 54 metrics:
1. Lock Management implementation (complete 15 remaining)
2. Team Coordination tracking
3. Service Coupling analysis
4. Code Quality scanning
5. Timeline/Scheduling system
6. Error tracking
7. Deployment coordination
8. Audit/Compliance checking

