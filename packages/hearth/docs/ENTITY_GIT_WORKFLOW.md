# Entity Git Workflow - Safe Branching Strategy

## Problem

Entity committing directly to `master` = dangerous:
- Could break production code
- No review before merge
- Difficult to rollback
- Multiple proposals could conflict

## Solution: Feature Branch Workflow

Entity creates branches for each proposal, commits there, human reviews and merges.

---

## Workflow

### 1. Proposal Created (Entity)

```bash
# Entity creates proposal
# Proposal system assigns ID: prop-001
```

### 2. Proposal Approved (Human)

```bash
# Human reviews and approves via Web UI or CLI
hearth proposals approve prop-001
```

### 3. Implementation (Entity)

Entity works in `.dev/` first:

```bash
# Plan and experiment in .dev/
cat > .dev/docs/prop-001-plan.md << 'EOF'
...planning...
EOF

# Test changes before implementing
python -c "test code here"
```

### 4. Create Feature Branch (Entity)

```bash
# Create branch for this proposal
git checkout -b proposal/prop-001-feature-name

# Make changes
nano core/some_file.py

# Test
python verify-install.py
python master.py serve  # Manual test
```

### 5. Commit to Branch (Entity)

```bash
# Commit to feature branch
git add core/some_file.py
git commit -m "feat: implement feature

Self-improvement proposal #prop-001"

# Push branch to origin (if remote configured)
git push origin proposal/prop-001-feature-name
```

### 6. Review (Human)

**Option A: Manual merge (local)**
```bash
# Human reviews the branch
git diff master..proposal/prop-001-feature-name

# Test the branch
git checkout proposal/prop-001-feature-name
python verify-install.py
hearth serve  # Test it works

# Merge if good
git checkout master
git merge proposal/prop-001-feature-name --no-ff

# Delete branch
git branch -d proposal/prop-001-feature-name
```

**Option B: Pull Request (GitHub/GitLab)**
```bash
# Entity pushes branch
git push origin proposal/prop-001-feature-name

# Entity creates PR (if gh CLI available)
gh pr create \
  --title "Self-improvement: Feature name" \
  --body "Implements proposal #prop-001"

# Human reviews PR on GitHub
# Human merges when satisfied
```

---

## Updated ProposalManager Workflow

### Auto-Branch Mode

```python
def commit_proposal(self, proposal_id: str, create_branch: bool = True):
    """
    Commit proposal to git.

    Args:
        proposal_id: Proposal ID
        create_branch: If True, create feature branch (safe, recommended)
                      If False, commit to current branch (dangerous)
    """
    if create_branch:
        # Create feature branch
        branch_name = f"proposal/{proposal_id}-{safe_title}"
        subprocess.run(['git', 'checkout', '-b', branch_name])

    # Stage and commit changes
    # ...

    # Push branch if remote exists
    subprocess.run(['git', 'push', 'origin', branch_name])
```

---

## Branch Naming Convention

```
proposal/prop-{ID}-{short-description}
```

Examples:
```
proposal/prop-001-improve-reflections
proposal/prop-002-add-memory-search
proposal/prop-003-optimize-task-queue
```

---

## Protection Rules

### For Production Repos

**Main branch protection:**
```yaml
# .github/workflows/branch-protection.yml
master:
  require_pull_request: true
  require_review: 1
  require_status_checks: true
  checks:
    - verify-install
    - test-service-starts
```

**Manual (local repo):**
```bash
# Refuse direct commits to master
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" = "master" ]; then
  echo "❌ Direct commits to master are not allowed!"
  echo "   Create a feature branch: git checkout -b proposal/prop-XXX-name"
  exit 1
fi
EOF

chmod +x .git/hooks/pre-commit
```

---

## Entity Boundaries Update

Update `soul.md`:

```markdown
## Development Workflow
I can improve myself, but with safety:
1. Plan in `.dev/` (scratch space)
2. Get approval for proposal
3. **Create feature branch** - Never commit to master directly!
4. Implement in branch
5. Test thoroughly
6. Commit to branch with clear message
7. Human reviews and merges

**Git Safety:**
- ❌ Never: `git commit` on master branch
- ✅ Always: Create branch first (`git checkout -b proposal/prop-XXX`)
- ✅ Always: Test before committing
- ✅ Always: Human reviews before merge

Read: `docs/ENTITY_GIT_WORKFLOW.md`
```

---

## CLI Commands for Human

```bash
# List entity's feature branches
git branch | grep "proposal/"

# Review a proposal branch
hearth proposals review prop-001  # Shows diff, lets you test

# Merge approved proposal
hearth proposals merge prop-001  # Tests, merges, deletes branch

# Reject proposal branch
hearth proposals reject-branch prop-001  # Deletes branch
```

---

## Rollback Strategy

### If Bad Code Gets Merged

```bash
# Revert the merge commit
git log --oneline -10  # Find merge commit
git revert -m 1 <merge-commit-sha>

# Or reset to before merge (destructive)
git reset --hard <commit-before-merge>
```

### If Entity Made Bad Commits in Branch

```bash
# Just delete the branch
git branch -D proposal/prop-XXX

# Entity can recreate from clean state
```

---

## Testing Before Merge

**Required checks:**

1. **Verification script**
   ```bash
   python verify-install.py
   ```

2. **Service starts**
   ```bash
   python master.py serve
   # Does it start without errors?
   ```

3. **Basic functionality**
   ```bash
   curl http://localhost:8420/api/health
   # Does API respond?
   ```

4. **Manual spot checks**
   - Open Web UI
   - Navigate pages
   - Test the new feature

---

## Summary

### Old (Dangerous):
```
Entity → commit to master → production breaks
```

### New (Safe):
```
Entity → create branch → commit to branch → human reviews → merge to master
```

**Key changes:**
1. Entity creates feature branches
2. Entity commits to branches, not master
3. Human reviews diffs before merge
4. Can rollback by deleting branch
5. Main branch stays stable

---

## Implementation

Update `core/proposals.py`:

```python
def commit_proposal(self, proposal_id: str) -> Optional[str]:
    """Create feature branch and commit proposal."""

    # Get proposal
    proposal = self.get_proposal(proposal_id)

    # Create branch name
    branch_name = f"proposal/{proposal_id}-{self._sanitize(proposal.title)}"

    # Check out master
    subprocess.run(['git', 'checkout', 'master'])

    # Create feature branch
    subprocess.run(['git', 'checkout', '-b', branch_name])

    # Stage files
    for file in proposal.target_files:
        subprocess.run(['git', 'add', file])

    # Commit
    commit_msg = f"""feat: {proposal.title}

{proposal.description}

Self-improvement proposal #{proposal_id}"""

    subprocess.run(['git', 'commit', '-m', commit_msg])

    # Return branch name
    return branch_name
```

**Entity never touches master. Human always reviews. Safe.**
