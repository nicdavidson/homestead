# Homestead Documentation Reorganization Plan

**Date:** January 31, 2026
**Status:** Analysis Complete - Ready for Implementation
**Scope:** 61 total markdown files across multiple locations

---

## Executive Summary

The Homestead documentation is currently **fragmented and difficult to navigate**:

- **61 markdown files** scattered across multiple directories
- **Duplicate files** in `lore/` and `lore/base/` (15 files with overlap)
- **Package-specific docs** in subdirectories with inconsistent naming (11 Hearth docs use UPPERCASE)
- **Mixed content types** - user guides, API references, architecture docs, investigations all at different levels
- **No clear hierarchy** - users don't know where to start or how to navigate

**Key Problems:**
1. **Discoverability:** New users can't tell what to read first
2. **Duplication:** lore/base/ and lore/ have parallel structure with unclear purpose
3. **Inconsistency:** File naming (architecture.md vs ARCHITECTURE.md), formats, and organization vary by package
4. **Hidden documentation:** Package docs buried in subdirectories with no central index
5. **No growth path:** Investigation docs (claude-dir-investigation.md, haiku-optimization-opportunities.md) aren't linked to actionable work

---

## Current State Analysis

### File Distribution

| Location | Count | Type |
|----------|-------|------|
| Root `/` | 1 | Main README |
| `docs/` | 7 | Architecture, API, governance, roadmaps, investigations |
| `lore/` | 8 | Identity, personality, agent definitions |
| `lore/base/` | 7 | Base identity templates (DUPLICATE) |
| `packages/hearth/docs/` | 11 | Hearth-specific guides and architecture |
| `packages/*/` | 0 other | (No docs in herald, steward, almanac, common) |
| **Total** | **61** | |

### Content Categories

**By Purpose:**

| Category | Files | Locations |
|----------|-------|-----------|
| **User Guides** | 4 | docs/ (README-like), hearth/docs/ |
| **API/Technical Reference** | 2 | docs/api-reference.md, hearth/docs/ |
| **Architecture & Design** | 6 | docs/architecture.md, docs/*.md, hearth/docs/ARCHITECTURE.md, lore/*.md |
| **Identity/Personality** | 8 | lore/*.md (soul, claude, user, agents, triggers) |
| **Identity Templates** | 7 | lore/base/*.md (DUPLICATE of lore/) |
| **Roadmaps & Strategic** | 3 | docs/ (memory-roadmap, governance-priorities) |
| **Investigations** | 3 | docs/ (claude-dir, haiku-opt, backup-migration) |
| **Generated/Temporary** | ?  | Various .gitignore entries suggest cache files |

### Duplication Analysis

**lore/ vs lore/base/ - Direct Parallels:**

```
lore/soul.md                    ←→ lore/base/soul.md
lore/claude.md                  ←→ lore/base/claude.md
lore/user.md                    ←→ lore/base/user.md
lore/identity.md                ←→ lore/base/identity.md
lore/agents.md                  ←→ lore/base/agents.md
lore/triggers.md                ←→ lore/base/triggers.md
lore/architecture.md            ←→ lore/base/architecture.md
```

**Unclear Purpose:**
- `lore/base/` appears to be template/baseline versions
- `lore/` appears to be active/customized versions
- No documentation explaining the relationship
- Both are tracked in git, creating confusion

**Additional Lore Files (Not in base/):**
- `lore/dreamfactory-value-prop.md` (standalone, project-specific)

### Naming Inconsistencies

**Hearth docs use inconsistent naming:**
- UPPERCASE files: `ARCHITECTURE.md`, `SERVICE_SETUP.md`, `QUICKSTART.md`, `START_HERE.md`, `UNIFIED_SERVICE.md`, `ENTITY_GIT_WORKFLOW.md`, `ENTITY_DEVELOPMENT_GUIDE.md`, `COLLABORATION_MODEL.md`, `SETUP_GUIDE.md`
- lowercase files: `architecture.md`, `competitive-intel.md`
- Duplicates with same name: `ARCHITECTURE.md` and `architecture.md` both exist

**Top-level docs use lowercase:**
- `architecture.md`, `api-reference.md`, `governance-priorities.md`, `memory-roadmap.md`, `backup-and-migration-strategy.md`

---

## Proposed New Structure

### Directory Hierarchy

```
homestead/
├── README.md                           # Main entry point (unchanged)
│
├── docs/                               # REORGANIZED
│   ├── START_HERE.md                   # Navigation guide (NEW)
│   ├── GLOSSARY.md                     # Terms & concepts (NEW)
│   │
│   ├── user-guide/                     # For end users
│   │   ├── getting-started.md
│   │   ├── quick-start.md
│   │   ├── configuration.md
│   │   ├── telegram-bot.md
│   │   ├── web-dashboard.md
│   │   └── troubleshooting.md
│   │
│   ├── dev-guide/                      # For developers
│   │   ├── setup.md
│   │   ├── architecture-overview.md
│   │   ├── packages.md
│   │   ├── contributing.md
│   │   ├── testing.md
│   │   └── deployment.md
│   │
│   ├── reference/                      # Technical reference
│   │   ├── api-reference.md
│   │   ├── database-schema.md
│   │   ├── environment-variables.md
│   │   ├── cli-reference.md
│   │   └── config-options.md
│   │
│   ├── architecture/                   # Deep dives
│   │   ├── system-overview.md          # (from docs/architecture.md)
│   │   ├── message-flow.md
│   │   ├── data-layer.md
│   │   ├── package-design.md
│   │   └── cross-package-communication.md
│   │
│   ├── roadmaps/                       # Strategic documents
│   │   ├── memory-roadmap.md
│   │   ├── governance-priorities.md
│   │   ├── backup-and-migration.md
│   │   └── feature-pipeline.md
│   │
│   ├── package-guides/                 # Package-specific docs
│   │   ├── herald.md                   # Telegram bot guide
│   │   ├── manor.md                    # Web dashboard guide
│   │   ├── steward.md                  # Task management guide
│   │   ├── almanac.md                  # Job scheduling guide
│   │   ├── common.md                   # Shared infrastructure guide
│   │   ├── hearth.md                   # AI personality layer guide
│   │   └── mcp-homestead.md            # MCP server guide
│   │
│   └── research/                       # Investigation & findings
│       ├── claude-directory-deep-dive.md
│       ├── haiku-optimization-opportunities.md
│       └── [other investigations]
│
├── lore/                               # AI identity (CLEANED UP)
│   ├── README.md                       # Purpose of lore files (NEW)
│   ├── soul.md                         # Core identity (keep active version)
│   ├── claude.md                       # Claude directives
│   ├── user.md                         # User context
│   ├── triggers.md                     # Behavioral triggers
│   ├── agents.md                       # Agent definitions
│   ├── identity.md                     # System identity
│   ├── architecture.md                 # Lore-specific architecture notes
│   │
│   └── templates/                      # (NEW - moved from base/)
│       ├── soul.md.template
│       ├── claude.md.template
│       ├── user.md.template
│       ├── agents.md.template
│       ├── triggers.md.template
│       ├── identity.md.template
│       └── README.md                   # How to use templates
│
├── packages/
│   ├── herald/
│   │   ├── README.md                   # Package overview (if needed)
│   │   └── docs/                       # (MINIMAL - link to docs/package-guides/)
│   │       └── _index.md               # Redirect to main docs
│   │
│   ├── manor/
│   │   ├── README.md
│   │   └── docs/
│   │       └── _index.md
│   │
│   ├── hearth/
│   │   ├── README.md
│   │   └── docs/                       # CONSOLIDATED here or moved?
│   │       ├── START_HERE.md           (kept - it's good)
│   │       ├── ARCHITECTURE.md         (kept - detailed)
│   │       └── _index.md               (link to main docs)
│   │
│   └── [others]/
│       ├── README.md
│       └── docs/ (if any)
│
└── .gitignore                          # Updated patterns
```

### Navigation Strategy

**Single Entry Point: `/docs/START_HERE.md`**

Contains:
- **What is Homestead?** (link to root README)
- **I want to...** quick links:
  - "Get started as a user" → user-guide/quick-start.md
  - "Set up for development" → dev-guide/setup.md
  - "Understand the architecture" → architecture/system-overview.md
  - "Deploy to production" → dev-guide/deployment.md
  - "Customize my agent" → lore/README.md
  - "Find API reference" → reference/api-reference.md
  - "Configure my instance" → user-guide/configuration.md
  - "Read investigation findings" → research/
- **Document organization** (this hierarchy)
- **Glossary link**

---

## Detailed Changes

### 1. Create `/docs/START_HERE.md` (NEW)

**Purpose:** Single navigation hub for all documentation

**Contents:**
- Welcome to Homestead
- Quick links by use case
- Document structure overview
- Common tasks & where to find them
- Links to key files (README, GLOSSARY, etc.)

### 2. Create `/docs/GLOSSARY.md` (NEW)

**Purpose:** Central vocabulary reference

**Include:**
- Key terms: lore, scratchpad, skills, watchtower, outbox, herald, manor, steward, almanac, hearth, MCP
- Package names & purposes
- Component names (sessions, watchtower, etc.)
- Agent types (Grok, Sonnet, Opus)

### 3. Reorganize `/docs/` Files

**Move:**
- `docs/architecture.md` → `docs/architecture/system-overview.md`
- `docs/api-reference.md` → `docs/reference/api-reference.md`
- `docs/governance-priorities.md` → `docs/roadmaps/governance-priorities.md`
- `docs/memory-roadmap.md` → `docs/roadmaps/memory-roadmap.md`
- `docs/backup-and-migration-strategy.md` → `docs/roadmaps/backup-and-migration.md`

**Extract/Create new files from existing:**
- From `docs/architecture.md` → Split into:
  - `docs/architecture/message-flow.md` (message flow sections)
  - `docs/architecture/data-layer.md` (database & data layout sections)
  - `docs/architecture/package-design.md` (package dependency section)
  - `docs/architecture/cross-package-communication.md` (outbox section)
  - Keep `docs/architecture/system-overview.md` as main

**Create new package-specific guides:**
- `docs/package-guides/herald.md` - Extract from README.md "Herald" section + create setup/usage
- `docs/package-guides/manor.md` - Extract from README.md + api-reference.md context
- `docs/package-guides/steward.md` - Extract from README.md
- `docs/package-guides/almanac.md` - Extract from README.md
- `docs/package-guides/common.md` - Extract from README.md
- `docs/package-guides/hearth.md` - Consolidate hearth/docs/START_HERE.md + ARCHITECTURE.md
- `docs/package-guides/mcp-homestead.md` - Create from README references

**Create user guides:**
- `docs/user-guide/getting-started.md` - From root README "Quick Start"
- `docs/user-guide/configuration.md` - From root README "Configuration"
- `docs/user-guide/telegram-bot.md` - From README "Run Herald" + package-guides/herald.md
- `docs/user-guide/web-dashboard.md` - From README "Run Manor" + package-guides/manor.md
- `docs/user-guide/troubleshooting.md` - Create with common issues

**Create dev guides:**
- `docs/dev-guide/setup.md` - From root README + dev-guide-specific content
- `docs/dev-guide/architecture-overview.md` - Link to architecture/ + high-level overview
- `docs/dev-guide/packages.md` - From README "Packages" section + "Adding a New Package"
- `docs/dev-guide/contributing.md` - Create with conventions, PR process
- `docs/dev-guide/testing.md` - Create
- `docs/dev-guide/deployment.md` - Create from roadmap/backup content

**Create references:**
- `docs/reference/database-schema.md` - Extract from docs/architecture.md "Database Schema Reference"
- `docs/reference/environment-variables.md` - From root README "Environment Variables" + architecture.md
- `docs/reference/config-options.md` - Expand from README configuration section
- `docs/reference/cli-reference.md` - Create from CLI tools across packages

**Move investigations:**
- `docs/research/claude-directory-deep-dive.md` - Rename from claude-dir-investigation.md
- `docs/research/haiku-optimization-opportunities.md` - Move as-is
- Any other investigations follow same pattern

### 4. Clean Up `/lore/` Directory

**Decision on lore/base/:**
The `lore/base/` directory appears to serve as templates or baseline versions. Two options:

**Option A (Recommended): Move to templates/ subdirectory**
```
lore/
├── README.md (NEW) - explains lore structure
├── soul.md, claude.md, user.md, etc. (KEEP - active versions)
└── templates/ (NEW - from lore/base/)
    ├── soul.md.template
    ├── claude.md.template
    ├── user.md.template
    ├── agents.md.template
    ├── triggers.md.template
    ├── identity.md.template
    ├── README.md (NEW - explains templates & when to use)
    └── .gitignore (optional - to track templates)
```

**Option B (Alternative): Delete lore/base/**
If `lore/base/` is truly just forgotten/redundant copies, delete entirely.

**Decision:** Go with Option A - preserves history, makes clear they're templates for new users.

**Add `/lore/README.md`:**
- Purpose of lore files
- What each file does (soul, claude, user, triggers, agents, etc.)
- How to customize
- Link to templates/
- Link back to docs/user-guide/customize-agent.md (NEW)

### 5. Consolidate Package Documentation

**For each package (herald, manor, steward, almanac, common, hearth, mcp-homestead):**

Option 1 (Cleaner): Remove package-specific docs/, centralize in main docs/
- Create `docs/package-guides/{package}.md`
- Replace `packages/{package}/docs/` with `_index.md` or single redirect file
- Keep complex architecture docs in package if >500 lines

Option 2 (Preserve existing): Keep hearth docs as-is, consolidate others
- Hearth has extensive docs (11 files) - keep structure
- Other packages have minimal docs - consolidate to package-guides/

**Recommendation:** Option 1 for consistency, but keep hearth/docs/ as comprehensive reference due to volume.

**Actions:**
1. Create `docs/package-guides/hearth.md` that aggregates START_HERE + ARCHITECTURE + QUICKSTART
2. Rename duplicate `hearth/docs/ARCHITECTURE.md` → `ARCHITECTURE-DEEP.md` (keep for detailed ref)
3. Create minimal redirect files in package docs/ directories pointing to main docs/

### 6. Update Root Files

**`/README.md`** - Minimal changes needed, already good
- Add link to `/docs/START_HERE.md` in opening
- Optionally expand "Documentation" section to mention new structure

**`/.gitignore`** - Already exists, add patterns if needed:
```
# Documentation build artifacts (if using docs generator)
docs/_build/
docs/.doctrees/
site/

# Investigation artifacts
docs/research/**/*.tmp
```

---

## Implementation Roadmap

### Phase 1: Preparation (1-2 hours)

- [ ] Review this plan with stakeholders
- [ ] Create todo list in homestead task system
- [ ] Backup current docs (git commit)
- [ ] Create new directory structure skeleton

### Phase 2: Create New Directories & Core Files (2-3 hours)

- [ ] Create `/docs/` subdirectories (user-guide, dev-guide, reference, architecture, roadmaps, package-guides, research)
- [ ] Create `/docs/START_HERE.md` (NEW)
- [ ] Create `/docs/GLOSSARY.md` (NEW)
- [ ] Create `/lore/README.md` (NEW)
- [ ] Create `/lore/templates/` directory (NEW)

### Phase 3: Move & Consolidate Files (3-4 hours)

- [ ] Move existing docs to new locations with updated paths
- [ ] Create new guides by extracting/merging content:
  - [ ] docs/package-guides/ files (7 files)
  - [ ] docs/user-guide/ files (6 files)
  - [ ] docs/dev-guide/ files (7 files)
  - [ ] docs/reference/ files (5 files)
  - [ ] docs/architecture/ files (split from single file)
- [ ] Move lore/base/* → lore/templates/*
- [ ] Move investigations to docs/research/

### Phase 4: Update Cross-References (1-2 hours)

- [ ] Update all internal links to reflect new paths
- [ ] Update START_HERE.md with all correct links
- [ ] Create/update index files in each section
- [ ] Verify no broken links

### Phase 5: Verification & Polish (1-2 hours)

- [ ] Test navigation from START_HERE
- [ ] Verify hearth docs still accessible
- [ ] Update .gitignore if needed
- [ ] Update git commit with summary
- [ ] Add note to CHANGELOG (if exists)

**Total Time Estimate: 8-13 hours**

---

## What to Keep, Merge, Archive, or Delete

### KEEP (No Changes)

- `/README.md` - Main entry point, still excellent
- `/lore/soul.md`, `/lore/claude.md`, `/lore/user.md` - Active identity files
- `/lore/triggers.md`, `/lore/agents.md`, `/lore/identity.md` - Active identity files
- `/lore/architecture.md` - Custom architecture notes (keep in lore/)
- `/lore/dreamfactory-value-prop.md` - Project-specific knowledge
- `packages/hearth/docs/START_HERE.md` - Excellent quickstart
- `packages/hearth/docs/ARCHITECTURE.md` - Detailed architecture doc

### MERGE (Combine into Single Files)

- `docs/architecture.md` + `docs/api-reference.md` sections → Split into `docs/architecture/`, `docs/reference/api-reference.md`
- Hearth's 11 docs → Consolidate into `/docs/package-guides/hearth.md` (high-level) + keep ARCHITECTURE.md in package as deep-dive
- README.md sections ("Packages", "Quick Start", "Configuration") → Extract into user-guide/ and dev-guide/

### ARCHIVE (Move to historical/reference, not primary nav)

- `docs/claude-dir-investigation.md` → `docs/research/claude-directory-deep-dive.md`
- `docs/haiku-optimization-opportunities.md` → `docs/research/haiku-optimization-opportunities.md`
- Any investigation docs that aren't actionable → docs/research/ (lower nav priority)

### DELETE (Redundant/Broken)

- `lore/base/*` (all 7 files) → Move to `lore/templates/` instead (don't delete, rename as templates)
- Empty redirect files (if creating package-guides centralization) - **Only if not needed**
- Broken/empty proposal docs (per backup-migration analysis) - **Already broken, no action needed**

---

## Benefits of This Reorganization

### For Users

✅ **Clear starting point** - `/docs/START_HERE.md` eliminates "where do I begin?"
✅ **Reduced cognitive load** - Organized by use case (user vs. developer)
✅ **Better discoverability** - Users search within topic, not 61 files
✅ **Consistent naming** - No more UPPERCASE vs. lowercase confusion
✅ **Graduated complexity** - Quick-start → Config → Architecture progression

### For Developers

✅ **Package docs centralized** - One place per package (docs/package-guides/)
✅ **Reference section** - API, schema, env vars in one place
✅ **Architecture deep-dives** - Organized by topic, not flat
✅ **Growth path** - Research → Roadmaps → Implementation
✅ **Maintenance easier** - Clear location for each doc type

### For the Project

✅ **Reduced duplication** - lore/base/ purpose clarified, redundancy eliminated
✅ **Consistency** - Naming conventions, file organization, cross-linking
✅ **Discoverability** - START_HERE + GLOSSARY = onboarding complete
✅ **Scalability** - Structure supports adding new docs over time
✅ **Professionalism** - Well-organized docs signal project maturity

---

## Potential Issues & Mitigation

### Issue 1: Breaking Links During Reorganization

**Mitigation:**
- Use git move commands: `git mv docs/architecture.md docs/architecture/system-overview.md`
- Update all internal links in same PR
- Test cross-references before finalizing

### Issue 2: Hearth's Large Doc Set

**Current:** 11 Hearth-specific docs in `packages/hearth/docs/`
**Issue:** Consolidating might lose detail

**Mitigation:**
- Keep comprehensive docs in package (ARCHITECTURE.md, START_HERE.md are excellent)
- Create high-level guide in main docs/package-guides/hearth.md
- Link between them: "For detailed Hearth architecture, see packages/hearth/docs/ARCHITECTURE.md"

### Issue 3: Lore Customization Workflow

**Current:** Users might not understand lore/base/ purpose
**Issue:** Moving to templates/ might confuse existing users

**Mitigation:**
- Create lore/README.md explaining templates
- Add .gitignore to clarify templates aren't modified after copy
- Document workflow: copy template → customize → use as lore/

### Issue 4: Git History / Blame

**Issue:** Moving files in git can lose blame history

**Mitigation:**
- Use `git mv` (preserves history)
- Or use `git log --follow` to track moved files
- Not a blocker, just awareness

### Issue 5: Forgotten Links

**Issue:** Some docs might link to old paths

**Mitigation:**
- Search for all `.md` references before reorganizing
- Use grep to find cross-package links
- Test navigation from START_HERE thoroughly

---

## Future Enhancements

After initial reorganization:

1. **Generate HTML docs** - Use Mkdocs, Sphinx, or similar
2. **Add search index** - Full-text search across docs
3. **Create API client docs** - If SDKs created
4. **Add troubleshooting section** - Expand with community issues
5. **Documentation versioning** - If multiple versions needed
6. **Translation** - If international users
7. **Diagram generation** - Architecture diagrams from docs
8. **Live examples** - Interactive code samples

---

## Success Criteria

### Navigation Quality
- [ ] User can go from /docs/START_HERE.md to any doc in ≤3 clicks
- [ ] All internal links are correct (no 404s)
- [ ] GLOSSARY defines all domain-specific terms
- [ ] Package links go from main docs to detailed package docs

### Content Quality
- [ ] No duplicate content across files
- [ ] Each file has clear purpose statement
- [ ] Naming conventions consistent
- [ ] Lore/ directory clearly organized with templates

### Organization
- [ ] 61 files organized into 8 categories (user-guide, dev-guide, reference, architecture, roadmaps, package-guides, research, lore)
- [ ] START_HERE.md serves as navigation hub
- [ ] Each subdirectory has README or index file
- [ ] No files in wrong category

### Validation
- [ ] git status shows only reorganized/renamed files (no deletions except lore/base/)
- [ ] All existing content preserved (nothing lost, only reorganized)
- [ ] Can navigate from old link to new location (redirects or docs)
- [ ] Root README updated with link to /docs/START_HERE.md

---

## File-by-File Checklist

### Docs to Move

- [ ] `docs/architecture.md` → `docs/architecture/system-overview.md` (extract sections to separate files)
- [ ] `docs/api-reference.md` → `docs/reference/api-reference.md`
- [ ] `docs/governance-priorities.md` → `docs/roadmaps/governance-priorities.md`
- [ ] `docs/memory-roadmap.md` → `docs/roadmaps/memory-roadmap.md`
- [ ] `docs/backup-and-migration-strategy.md` → `docs/roadmaps/backup-and-migration.md`
- [ ] `docs/claude-dir-investigation.md` → `docs/research/claude-directory-deep-dive.md`
- [ ] `docs/haiku-optimization-opportunities.md` → `docs/research/haiku-optimization-opportunities.md`

### New Docs to Create

**Core Navigation:**
- [ ] `/docs/START_HERE.md` (NEW)
- [ ] `/docs/GLOSSARY.md` (NEW)
- [ ] `/lore/README.md` (NEW)

**User Guides:**
- [ ] `docs/user-guide/getting-started.md` (NEW)
- [ ] `docs/user-guide/quick-start.md` (NEW)
- [ ] `docs/user-guide/configuration.md` (NEW)
- [ ] `docs/user-guide/telegram-bot.md` (NEW)
- [ ] `docs/user-guide/web-dashboard.md` (NEW)
- [ ] `docs/user-guide/troubleshooting.md` (NEW)

**Developer Guides:**
- [ ] `docs/dev-guide/setup.md` (NEW)
- [ ] `docs/dev-guide/architecture-overview.md` (NEW)
- [ ] `docs/dev-guide/packages.md` (NEW)
- [ ] `docs/dev-guide/contributing.md` (NEW)
- [ ] `docs/dev-guide/testing.md` (NEW)
- [ ] `docs/dev-guide/deployment.md` (NEW)

**Reference:**
- [ ] `docs/reference/database-schema.md` (NEW)
- [ ] `docs/reference/environment-variables.md` (NEW)
- [ ] `docs/reference/config-options.md` (NEW)
- [ ] `docs/reference/cli-reference.md` (NEW)

**Architecture:**
- [ ] `docs/architecture/message-flow.md` (NEW - from architecture.md)
- [ ] `docs/architecture/data-layer.md` (NEW - from architecture.md)
- [ ] `docs/architecture/package-design.md` (NEW - from architecture.md)
- [ ] `docs/architecture/cross-package-communication.md` (NEW - from architecture.md)

**Package Guides:**
- [ ] `docs/package-guides/herald.md` (NEW)
- [ ] `docs/package-guides/manor.md` (NEW)
- [ ] `docs/package-guides/steward.md` (NEW)
- [ ] `docs/package-guides/almanac.md` (NEW)
- [ ] `docs/package-guides/common.md` (NEW)
- [ ] `docs/package-guides/hearth.md` (NEW - consolidates multiple hearth docs)
- [ ] `docs/package-guides/mcp-homestead.md` (NEW)

**Lore Templates:**
- [ ] `lore/templates/` directory (NEW)
- [ ] Move `lore/base/*` → `lore/templates/*.template` (7 files)
- [ ] `lore/templates/README.md` (NEW)

### Lore Files to Keep

- [ ] `lore/soul.md` (KEEP)
- [ ] `lore/claude.md` (KEEP)
- [ ] `lore/user.md` (KEEP)
- [ ] `lore/triggers.md` (KEEP)
- [ ] `lore/agents.md` (KEEP)
- [ ] `lore/identity.md` (KEEP)
- [ ] `lore/architecture.md` (KEEP)
- [ ] `lore/dreamfactory-value-prop.md` (KEEP)

---

## Appendix A: Content Inventory

### Complete File Listing (61 files)

**Root (1):**
1. README.md

**Docs (7):**
2. docs/architecture.md
3. docs/api-reference.md
4. docs/governance-priorities.md
5. docs/memory-roadmap.md
6. docs/backup-and-migration-strategy.md
7. docs/claude-dir-investigation.md
8. docs/haiku-optimization-opportunities.md

**Lore (8):**
9. lore/soul.md
10. lore/claude.md
11. lore/user.md
12. lore/triggers.md
13. lore/agents.md
14. lore/identity.md
15. lore/architecture.md
16. lore/dreamfactory-value-prop.md

**Lore Base (7) - DUPLICATES:**
17. lore/base/soul.md
18. lore/base/claude.md
19. lore/base/user.md
20. lore/base/triggers.md
21. lore/base/agents.md
22. lore/base/identity.md
23. lore/base/architecture.md

**Hearth Docs (11):**
24. packages/hearth/docs/START_HERE.md
25. packages/hearth/docs/ARCHITECTURE.md
26. packages/hearth/docs/architecture.md (lowercase duplicate)
27. packages/hearth/docs/SERVICE_SETUP.md
28. packages/hearth/docs/COLLABORATION_MODEL.md
29. packages/hearth/docs/SETUP_GUIDE.md
30. packages/hearth/docs/ENTITY_GIT_WORKFLOW.md
31. packages/hearth/docs/ENTITY_DEVELOPMENT_GUIDE.md
32. packages/hearth/docs/QUICKSTART.md
33. packages/hearth/docs/UNIFIED_SERVICE.md
34. packages/hearth/docs/competitive-intel.md

**Other Packages (0):**
- Herald: No docs/ directory
- Manor: No docs/ directory
- Steward: No docs/ directory
- Almanac: No docs/ directory
- Common: No docs/ directory
- MCP-Homestead: No docs/ directory

**Investigation Artifacts/Generated (various):**
- Various .md files in git status showing as modified/untracked
- Cache files (if any)

---

## Appendix B: Sample START_HERE.md Template

```markdown
# Getting Started with Homestead

Welcome! This is your starting point for Homestead documentation.

## What is Homestead?

Homestead is a self-sufficient AI infrastructure framework... [brief intro]

**Full overview:** See [README.md](../README.md)

---

## I want to...

### User Tasks
- **Get the bot running** → [Getting Started Guide](user-guide/getting-started.md)
- **Set up Telegram bot** → [Telegram Bot Guide](user-guide/telegram-bot.md)
- **Access web dashboard** → [Web Dashboard Guide](user-guide/web-dashboard.md)
- **Configure my instance** → [Configuration Guide](user-guide/configuration.md)
- **Customize my agent** → [Lore Files](../lore/README.md)
- **Troubleshoot issues** → [Troubleshooting](user-guide/troubleshooting.md)

### Developer Tasks
- **Set up for development** → [Dev Setup](dev-guide/setup.md)
- **Understand the architecture** → [Architecture Overview](dev-guide/architecture-overview.md)
- **Learn about packages** → [Package Guide](dev-guide/packages.md)
- **Deploy to production** → [Deployment Guide](dev-guide/deployment.md)
- **Contribute code** → [Contributing Guide](dev-guide/contributing.md)

### Reference
- **API Reference** → [API Docs](reference/api-reference.md)
- **Database Schema** → [Schema Reference](reference/database-schema.md)
- **Environment Variables** → [Environment Guide](reference/environment-variables.md)
- **CLI Reference** → [CLI Docs](reference/cli-reference.md)

### Deep Dives
- **System Architecture** → [Architecture Docs](architecture/system-overview.md)
- **Message Flow** → [Message Flow](architecture/message-flow.md)
- **Data Layer** → [Data Layer Design](architecture/data-layer.md)
- **Package Design** → [Package Architecture](architecture/package-design.md)

### Strategic Reading
- **Memory Roadmap** → [10x Memory Enhancement](roadmaps/memory-roadmap.md)
- **Governance & Security** → [Governance Priorities](roadmaps/governance-priorities.md)
- **Backup & Migration** → [Backup Strategy](roadmaps/backup-and-migration.md)

### Research & Investigations
- **Claude Directory Deep Dive** → [Research](research/claude-directory-deep-dive.md)
- **Haiku Optimization** → [Research](research/haiku-optimization-opportunities.md)

---

## Documentation Structure

```
docs/
├── user-guide/          ← For end users
├── dev-guide/           ← For developers
├── reference/           ← Technical reference
├── architecture/        ← Design & architecture
├── package-guides/      ← Package-specific docs
├── roadmaps/            ← Strategic planning
└── research/            ← Investigations & findings
```

---

## Key Terms

**Not sure what something means?** See [GLOSSARY.md](GLOSSARY.md)

Common terms: lore, scratchpad, skills, watchtower, herald, manor, steward, almanac...

---

## Package Overview

| Package | Purpose | Guide |
|---------|---------|-------|
| **Herald** | Telegram bot interface | [Herald Guide](package-guides/herald.md) |
| **Manor** | Web dashboard & API | [Manor Guide](package-guides/manor.md) |
| **Steward** | Task management | [Steward Guide](package-guides/steward.md) |
| **Almanac** | Job scheduling | [Almanac Guide](package-guides/almanac.md) |
| **Common** | Shared infrastructure | [Common Guide](package-guides/common.md) |
| **Hearth** | AI personality layer | [Hearth Guide](package-guides/hearth.md) |
| **MCP-Homestead** | Model Context Protocol | [MCP Guide](package-guides/mcp-homestead.md) |

---

## Stuck?

- Check [Troubleshooting](user-guide/troubleshooting.md)
- Search this site (Ctrl+F)
- See [GLOSSARY.md](GLOSSARY.md) for terminology
- Open a GitHub issue

---

Happy learning! 🏡

```

---

## Summary

This reorganization plan transforms scattered documentation into a **navigable, maintainable knowledge base** with:

- **Single entry point** (START_HERE.md)
- **Clear hierarchy** (user-guide, dev-guide, reference, architecture, etc.)
- **Reduced duplication** (lore/base/ → templates/)
- **Consistent naming** (lowercase everywhere)
- **Growth path** (quick-start → config → architecture)
- **Better discoverability** (GLOSSARY, cross-linking)

The restructuring can be completed in **8-13 hours** with the provided checklist, following a 5-phase implementation plan.

---

**Status:** Ready to implement
**Owner:** [To be assigned]
**Timeline:** Recommend completing in next sprint or designated documentation week
**Estimated Effort:** 8-13 hours total

