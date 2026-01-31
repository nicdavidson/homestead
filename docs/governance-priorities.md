# Homestead Governance Priorities

## System Overview

Homestead is a **personal AI infrastructure platform** built around Claude and other LLMs. It consists of:

- **Manor**: Web dashboard (Next.js frontend + FastAPI backend) for management UI
- **Herald**: Telegram bot interface for conversational AI
- **Steward**: Task management system with status tracking and blockers
- **Almanac**: Job scheduler with cron/interval/once support
- **MCP Homestead**: Model Context Protocol server exposing tools to Claude CLI
- **Common/Hearth**: Shared infrastructure (database, configuration, identity)

**Key managed entities:**
- Tasks (with status, priority, assignee, dependencies, blockers)
- Jobs (scheduled automation with action configs)
- Proposals (AI-generated code changes requiring review + apply)
- Sessions (conversation history and state)
- Lore (knowledge base markdown files)
- Scratchpad (temporary notes)
- Usage metrics (token counts, costs)
- Events (audit log for system activities)

## Current Governance State

### Authentication & Authorization

**Herald (Telegram Bot) - Minimal Auth:**
- Single layer: `is_authorized(user_id: int, config: Config)` in `/herald/auth.py`
- Only checks if `user_id` is in `config.allowed_user_ids` list
- Configured via environment variable: `ALLOWED_USER_IDS` (comma-separated list)
- **Issues:**
  - All allowed users have identical full access (no role differentiation)
  - Single hardcoded Telegram user ID (6038780843) receives proposal notifications regardless of permissions
  - No session-based authentication

**Manor API - No Authentication:**
- FastAPI with open CORS: `allow_origins=["*"]`, `allow_credentials=False`
- No authentication middleware or API keys
- Assumes frontend is trusted (browser-based)
- **Issues:**
  - Anyone with network access can hit the API
  - All endpoints are unprotected
  - No user context tracking

**MCP Server:**
- Allows any Claude CLI user to invoke Homestead tools
- No per-user isolation

### Access Control & Permissions

**Current Patterns:**
- **Tasks**: No access control beyond existence check; anyone can CRUD any task
- **Jobs**: No access control; anyone can create/enable/run jobs
- **Proposals**: No access control; anyone can create/approve/apply; hardcoded approval notifications
- **Lore/Scratchpad**: File system access control only (POSIX permissions on `~/.homestead`)
- **Chat Sessions**: Linked to Telegram `chat_id` only; no user-level isolation
- **Config**: Editable fields configurable at runtime but no authorization check

**Editable Config Fields** (in `/manor/api/config.py`):
```python
EDITABLE_FIELDS = {
    "allowed_models", "subagent_model", "max_turns",
    "claude_timeout_s", "allowed_origins", "proposal_test_cmd",
    "proposal_branch", "agent_name"
}
```
Any user can modify these via `/config` endpoint.

### Audit & Accountability

**Minimal Audit Trail:**
- **Events DB** (`events.db`): Read-only endpoint at `/api/events` that shows system events
  - Queryable by source, topic, time range
  - Designed for observability but appears to be write-only via external sources
  - No audit log for user actions on proposals, tasks, jobs, etc.

- **Usage Tracking** (`usage.db`): Records token usage and costs
  - Tracks: session_id, chat_id, model, tokens, cost, source, timestamps
  - Reported by Herald bot automatically
  - No user identity (only chat_id)

- **Database Backups**: Config changes backed up with rolling 10-version retention

**Missing:**
- No audit log for: who created/modified tasks, who approved proposals, who ran jobs
- No action history (only status snapshots)
- No change tracking (no before/after diffs for config or entity changes except proposals)

### Proposal Workflow (Most Mature Governance)

The proposal system has the most developed approval workflow:

```
Create (pending) → Review (approved/rejected) → Apply (applied/failed)
```

**Schema** (from `proposals.db`):
```sql
proposals (
    id, session_id, title, description, diff, file_paths_json,
    original_content, new_content,
    status (pending|approved|rejected|applied|failed),
    created_at, reviewed_at, applied_at,
    review_notes
)
proposal_files (per-file diffs and content)
```

**Features:**
- State machine validation (only pending→approved/rejected, approved→applied)
- Test execution before commit (configurable via `PROPOSAL_TEST_CMD`)
- Git commit on successful apply + push to branch
- Rollback on test failure
- Diff visualization in UI
- Telegram notifications with inline approve/reject buttons (hardcoded chat ID)
- Per-proposal review notes

**Issues:**
- No per-proposal permissions (who can approve?)
- Hardcoded approver (Telegram user 6038780843)
- No approval chain/required reviewers
- No diff restrictions (any change magnitude allowed)

### Data Isolation & Multi-Tenancy

**Single User / Single Tenant:**
- All systems assume a single personal agent (Milo)
- No concept of multiple users or teams
- Shared SQLite databases at `~/.homestead/`
- All file I/O is to shared directories

**No Multi-Tenancy Support:**
- No user/tenant ID fields in most schemas
- `chat_id` used for Telegram sessions but not universally
- `session_id` used for Claude CLI sessions but not user-scoped

## Security Vulnerabilities & Gaps

| # | Issue | Severity | Impact |
|---|-------|----------|--------|
| 1 | No API authentication | **Critical** | Any network attacker can modify any entity |
| 2 | Open CORS | **Critical** | XSS or malicious website can steal data |
| 3 | All users have same permissions | **High** | No accountability; privilege escalation not prevented |
| 4 | Hardcoded approver IDs | **High** | Approval logic depends on hidden config |
| 5 | No audit trail for human actions | **High** | Cannot trace who did what |
| 6 | Jobs can execute arbitrary shell commands | **Medium** | Misconfigured job is code execution vulnerability |
| 7 | No rate limiting on API | **Medium** | DOS possible; no protection from abuse |
| 8 | Config changes not audited | **Medium** | Silent modification possible |
| 9 | No session expiry enforcement | **Low** | Old sessions persist indefinitely |
| 10 | File path traversal protections minimal | **Low** | Only in lore/scratchpad; not elsewhere |

## Governance Priorities

### Priority 1: Foundation (Do First) 🔴

#### 1. User Identity & Context
Add `actor_id` tracking to all operations. Right now, there's no "who" in the system.
- Extend schemas to include `created_by`, `modified_by`, `approved_by`
- Track the human behind each action (not just `chat_id` or `session_id`)

#### 2. API Authentication
Manor API is completely open (`allow_origins=["*"]`, no auth middleware). Critical vulnerability.
- Add JWT tokens or API keys
- Require authentication for all mutating endpoints
- Add auth middleware to FastAPI

#### 3. Audit Trail
No record of who did what. Only system events are logged.
- Instrument all POST/PUT/DELETE operations
- Log: actor, action, entity_type, entity_id, timestamp, before/after state
- Extend existing `events.db` or create dedicated `audit_log.db`

### Priority 2: Accountability (Do Soon) 🟡

#### 4. Role-Based Access Control (RBAC)
Currently all allowed users have identical full access.
- Define roles: `admin`, `reviewer`, `user`, `readonly`
- Add role checks to endpoints (e.g., only admins can delete jobs)
- Store roles in config or user DB

#### 5. Approval Permissions
Proposal approvals are hardcoded to a single Telegram user ID (6038780843).
- Make approver list configurable per proposal type
- Allow role-based approval (e.g., "any admin" not just "user 123")
- Add approval chains (require N reviewers)

#### 6. Change History
No way to see who modified a task/job/config or when.
- Store entity revision history (versioning pattern like config backups)
- Add `/api/{entity}/{id}/history` endpoints
- Show "Last modified by X at Y" in UI

### Priority 3: Control & Safety (Do Later) 🟢

#### 7. Sensitive Action Confirmations
Jobs can execute arbitrary shell commands. Config changes can break the system.
- Require additional approval for high-risk actions:
  - Job execution (code execution risk)
  - Config changes (system stability risk)
  - Proposal apply (code integrity risk)
- Add "sudo mode" pattern (re-authenticate for sensitive ops)

#### 8. Rate Limiting & Quotas
No protection from abuse or runaway automation.
- Per-user API rate limits
- Per-user token/cost budgets
- Job execution frequency limits

#### 9. Multi-User Session Management
Sessions never expire, no revocation mechanism.
- Add session expiry (TTL)
- Add logout/revoke endpoint
- Track active sessions per user

### Priority 4: Scale (Future) 🔵

#### 10. Fine-Grained Permissions
Resource-based access control (RBAC → ABAC).
- Per-task ownership (only assignee + admin can modify)
- Per-proposal ownership (creator + reviewers + admin)
- Delegated permissions (share a task with specific users)

## Recommended Implementation Order

### Week 1-2: Identity & Auth
1. Add user model with roles
2. Add API authentication (JWT)
3. Add auth middleware to all routes

### Week 3-4: Audit & Accountability
4. Add audit logging to all mutations
5. Add `actor_id` to all schemas
6. Migrate proposal approval to use roles

### Week 5-6: Permissions & Controls
7. Implement RBAC checks on endpoints
8. Add approval chains for proposals
9. Add sensitive action confirmations

### Later: Scale & Safety
10. Rate limiting, session management, fine-grained ACLs

## Quick Wins (Low-Hanging Fruit)

If you want to start small:

1. **Add audit middleware** (`/manor/api/middleware/audit.py`) that logs all requests to `events.db` → 1 day work
2. **Add actor_id to proposals** and show "created by" in UI → 1 day work
3. **Make approver list configurable** instead of hardcoded → 2 hours work
4. **Add CORS restrictions** to Manor API (whitelist origins) → 10 minutes work

These give immediate security/governance value without major refactoring.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                           │
├─────────────────────────────────────────────────────────────────┤
│  Browser (Manor)  │  Telegram (Herald)  │  CLI (MCP Server)    │
└─────────────┬───────────────┬──────────────────┬──────────────┘
              │               │                  │
              └─────────┬─────┴──────────────────┴─────┐
                        │                              │
             ┌──────────▼──────────┐      ┌───────────▼──────────┐
             │   FastAPI Backend   │      │   Telegram Bot       │
             │   (Manor API)       │      │   (Herald)           │
             │   Port 8700         │      │   (Polling)          │
             └──────────┬──────────┘      └───────────┬──────────┘
                        │                              │
                        └──────────┬──────────────────┘
                                   │
            ┌──────────────────────▼──────────────────────┐
            │     Shared Data Layer (~/.homestead/)       │
            ├──────────────────────────────────────────────┤
            │ ├─ tasks.db (Steward)                       │
            │ ├─ jobs.db (Almanac)                        │
            │ ├─ proposals.db (Manor)                     │
            │ ├─ sessions.db (Herald)                     │
            │ ├─ usage.db (Herald/Manor)                  │
            │ ├─ events.db (System)                       │
            │ ├─ outbox.db (Telegram messages)            │
            │ ├─ lore/ (markdown knowledge base)          │
            │ ├─ scratchpad/ (temp notes)                 │
            │ └─ skills/ (agent tools)                    │
            └──────────────────────────────────────────────┘
```

**No centralized identity or auth layer currently exists.**

## Key Files for Governance Implementation

**Start here for governance work:**

1. `/manor/api/main.py` → Add middleware for auth/audit
2. `/manor/api/config.py` → Extend Settings with auth config
3. `/manor/api/routers/proposals.py` → Validate reviewer permissions
4. `/packages/herald/herald/auth.py` → Expand auth beyond user ID check
5. `/packages/herald/herald/config.py` → Add role/permission config
6. Create `/manor/api/middleware/auth.py` → Centralized auth logic
7. Create `/manor/api/middleware/audit.py` → Log all mutations
8. Extend database schemas → Add `actor_id`, `action`, `timestamp` columns

## Summary

Homestead is a **single-user, single-tenant personal AI infrastructure** with **minimal governance**. It prioritizes usability over security, assuming the operator is trusted and networks are private. The most mature governance pattern is the **proposal workflow** with review states, but even this lacks approval permissions and full audit trails.

To scale beyond personal use, you need:
1. **Authentication layer** (who is asking?)
2. **Authorization layer** (what can they do?)
3. **Audit layer** (what did they do?)
4. **User identity** (whose action is it?)

The foundation exists (SQLite, FastAPI, structured endpoints), but no multi-user governance has been implemented.
