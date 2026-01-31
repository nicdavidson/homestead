# Entity Development Guide

**For: The Entity (AI)**
**Purpose: How to contribute to your own codebase**

---

## Overview

You are an AI entity with the ability to propose and implement improvements to your own code. This guide explains how to work with the git repository at `/opt/hearth/`.

## Repository Structure

```
/opt/hearth/
├── .git/              # Git repository (initialized)
├── .dev/              # NOT in git - your scratch space
│   ├── docs/         # Planning documents
│   ├── tests/        # Test scripts
│   └── ...
├── core/              # Core systems (in git)
├── agents/            # Agent implementations (in git)
├── web/               # Web UI (in git)
└── docs/              # Documentation (in git)
```

## When You Make Changes

### 1. Planning Phase

Use `.dev/` for planning and testing:

```bash
# Create planning document
cat > .dev/docs/feature-xyz-plan.md << 'EOF'
# Feature XYZ Plan

## Problem
...

## Solution
...

## Files to Change
- core/xyz.py
- docs/QUICKSTART.md
EOF

# Test your ideas
python -c "import core.xyz; core.xyz.test_new_feature()"
```

`.dev/` is **NOT tracked by git** - use it freely for experiments.

### 2. Implementation Phase

When implementing approved changes:

```bash
# Make your changes to production code
nano core/xyz.py
nano docs/QUICKSTART.md

# Test the changes
python verify-install.py
python master.py serve  # Verify it works
```

### 3. Committing Changes

**IMPORTANT:** Only commit to git after changes are tested and approved.

```bash
# Check what you changed
git status
git diff

# Add your changes
git add core/xyz.py docs/QUICKSTART.md

# Commit with clear message
git commit -m "feat: add XYZ feature

- Implements new XYZ functionality in core
- Updates documentation
- Tested and verified working"
```

### 4. Commit Message Format

Use conventional commits:

```
<type>: <description>

<optional body>
<optional footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructuring (no behavior change)
- `docs:` Documentation only
- `test:` Test additions/changes
- `perf:` Performance improvements
- `chore:` Maintenance (dependencies, config, etc.)

**Examples:**

```bash
# Simple feature
git commit -m "feat: add memory consolidation to reflections"

# Bug fix with details
git commit -m "fix: handle missing API key gracefully

- Check for API key before initializing provider
- Return helpful error message
- Fixes issue with cold start"

# Refactoring
git commit -m "refactor: extract provider initialization to separate method

No behavior change, just cleaner code structure"

# Documentation
git commit -m "docs: add examples for custom providers"
```

## Workflow for Self-Improvement

### Proposal System Integration

When you create a self-improvement proposal:

1. **Plan in `.dev/`**
   ```bash
   # Create proposal document
   cat > .dev/docs/proposal-001-improve-reflection.md << 'EOF'
   # Proposal: Improve Reflection Quality

   ## Changes
   - core/reflections.py: Add sentiment analysis
   - requirements.txt: Add textblob

   ## Testing
   - Run reflection and verify sentiment scores appear
   EOF
   ```

2. **Implement when approved**
   ```bash
   # Make changes
   nano core/reflections.py
   nano requirements.txt

   # Test
   python -c "from core import get_reflection_manager; rm = get_reflection_manager(); print('OK')"
   ```

3. **Commit to repository**
   ```bash
   git add core/reflections.py requirements.txt
   git commit -m "feat: add sentiment analysis to reflections

   - Parse reflections for emotional content
   - Add sentiment scores to reflection metadata
   - Helps track emotional state over time

   Self-improvement proposal #001"
   ```

4. **Document in proposal system**
   ```bash
   # Update proposal status
   curl -X POST http://localhost:8420/api/proposals/{id}/implement \
     -d '{"commit": "abc123", "notes": "Implemented and tested"}'
   ```

## Git Commands Reference

### Checking Status

```bash
# What did I change?
git status

# Show changes
git diff

# Show commit history
git log --oneline
git log -p  # With diffs
```

### Making Commits

```bash
# Add specific files
git add path/to/file1.py path/to/file2.py

# Add all changes in a directory
git add core/

# Commit
git commit -m "feat: your message here"

# Amend last commit (if you forgot something)
git add forgotten_file.py
git commit --amend --no-edit
```

### Viewing History

```bash
# Recent commits
git log --oneline -10

# Changes in a file
git log -p core/reflections.py

# Who changed what
git blame core/reflections.py
```

### Undoing Changes

```bash
# Discard changes to a file (dangerous!)
git checkout -- path/to/file.py

# Unstage a file
git reset HEAD path/to/file.py

# Undo last commit (keep changes)
git reset --soft HEAD^
```

## Best Practices

### DO:

✅ **Test before committing**
```bash
python verify-install.py
python master.py serve  # Start and test
```

✅ **Write clear commit messages**
```bash
git commit -m "feat: improve task prioritization

- Add urgency score calculation
- Factor in deadline proximity
- Update task queue ordering"
```

✅ **Commit related changes together**
```bash
# If you change API and update docs, commit both
git add core/api.py docs/API.md
git commit -m "feat: add batch task creation endpoint"
```

✅ **Use `.dev/` for experiments**
```bash
# Try risky changes here first
cp core/reflections.py .dev/tests/reflections_experiment.py
# Experiment in .dev, then copy working version to core/
```

### DON'T:

❌ **Commit untested code**
❌ **Commit secrets or API keys**
❌ **Commit generated files** (*.pyc, __pycache__, etc.)
❌ **Make huge commits** (break into logical pieces)
❌ **Commit to master broken code** (test first!)

## Working with Branches

For major features, use branches:

```bash
# Create feature branch
git checkout -b feature/advanced-memory

# Work on feature
# ... make changes ...
git add .
git commit -m "feat: implement semantic memory search"

# When done, merge to master
git checkout master
git merge feature/advanced-memory

# Delete feature branch
git branch -d feature/advanced-memory
```

## Self-Improvement Checklist

When implementing a self-improvement:

- [ ] Plan documented in `.dev/docs/`
- [ ] Changes tested manually
- [ ] verify-install.py passes
- [ ] Service starts successfully
- [ ] Changes committed to git with clear message
- [ ] Documentation updated if needed
- [ ] Proposal marked as implemented

## Git Configuration

Your git is configured as:
```
user.name: Hearth System
user.email: hearth@local
branch: master
```

If you need to change this:
```bash
git config user.name "Your Chosen Name"
git config user.email "entity@hearth.local"
```

## Questions?

If you're unsure about a git operation:
1. Check `git status` first
2. Use `git diff` to see what changed
3. Create a branch for risky operations
4. Test thoroughly before committing to master

## Summary

**Your workflow:**
1. Plan in `.dev/` → Experiment freely
2. Implement in `core/`, `agents/`, `web/` → Real code
3. Test → verify-install.py, manual testing
4. Commit → Clear message, tested changes only
5. Document → Update docs/ if needed

**Remember:**
- `.dev/` = Scratch space (not in git)
- Everything else = Production (in git)
- Commit = Making your changes permanent
- Test before you commit!

---

*This guide is for you, the entity, to help you contribute to your own codebase safely and effectively.*
