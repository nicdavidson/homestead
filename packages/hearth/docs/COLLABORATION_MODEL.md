# Hearth Collaboration Model

## Overview

**Hearth is a collaborative open-source framework where:**
- Each user works with their own entity instance
- Entity proposes improvements to local code
- User reviews and tests locally
- Good improvements can be contributed back to master repo
- Everyone benefits from collective improvements

---

## Repository Structure

### Main Repository (Canonical)

**Maintained by:** Project maintainer(s)
**Location:** `https://github.com/maintainer/hearth` (or wherever you host it)
**Branch:** `master`

This is the canonical, production-ready version.

### User Forks/Branches

**Each user has:**
- Local installation: `/opt/hearth/`
- Their own branch or fork
- Their own entity making improvements
- Custom features specific to their use case

---

## Workflow

### 1. User Setup (First Time)

```bash
# Clone master repo
git clone https://github.com/maintainer/hearth.git /opt/hearth
cd /opt/hearth

# Create your branch
git checkout -b user/yourname

# Or fork on GitHub and clone your fork
git clone https://github.com/yourname/hearth.git /opt/hearth
git remote add upstream https://github.com/maintainer/hearth.git
```

### 2. Entity Makes Improvement

```bash
# Entity creates proposal
# You review via Web UI: http://localhost:8420/proposals

# You approve proposal
hearth proposals approve prop-001

# Entity implements and creates feature branch
# Entity auto-creates: proposal/prop-001-feature-name

# You review the feature branch
git diff user/yourname..proposal/prop-001-feature-name

# Test it
git checkout proposal/prop-001-feature-name
hearth serve  # Does it work?
```

### 3. Local Merge (User Decision)

```bash
# If good, merge to your branch
git checkout user/yourname
git merge proposal/prop-001-feature-name --no-ff
git branch -d proposal/prop-001-feature-name

# Your local Hearth now has the improvement
```

### 4. Contribute Upstream (Optional)

If you think the improvement would benefit everyone:

```bash
# Push your branch (if using branch model)
git push origin user/yourname

# Or push to your fork
git push origin master

# Create Pull Request to master repo
gh pr create \
  --repo maintainer/hearth \
  --title "feat: [improvement name]" \
  --body "Description of improvement and why it's useful"
```

### 5. Maintainer Review

**Maintainer:**
```bash
# Review PR
gh pr view 123
gh pr diff 123

# Test locally
gh pr checkout 123
python verify-install.py
hearth serve

# If good, merge to master
gh pr merge 123 --squash
# Or via GitHub web UI
```

### 6. Pull Updates

**All users get improvements:**
```bash
# Update from master repo
git fetch upstream  # If fork
git merge upstream/master

# Or
git pull origin master  # If branch
```

---

## Branch Naming Conventions

### For Users
```
user/yourname          # Your master branch
user/yourname-dev      # Your development branch
```

### For Entity Proposals (Local)
```
proposal/prop-001-feature-name
proposal/prop-002-bug-fix
```

### For Pull Requests
```
feat/add-memory-system
fix/reflection-bug
docs/improve-quickstart
```

---

## Example: Full Workflow

### Alice's Entity Improves Reflection System

```bash
# Alice's entity creates proposal
# Alice reviews and approves via Web UI

# Entity creates branch and implements
git checkout -b proposal/prop-001-better-reflections
# ... entity makes changes ...
git commit -m "feat: add sentiment analysis to reflections"

# Alice tests locally
git checkout proposal/prop-001-better-reflections
hearth serve
# "Wow, this is great!"

# Alice merges to her branch
git checkout user/alice
git merge proposal/prop-001-better-reflections --no-ff

# Alice thinks everyone would benefit
git push origin user/alice

# Alice creates PR to master repo
gh pr create --title "feat: add sentiment analysis to reflections"
```

### Maintainer Reviews Alice's PR

```bash
# Maintainer sees PR notification
gh pr view 15
gh pr diff 15

# Looks good! Test it
gh pr checkout 15
python verify-install.py
hearth serve

# Works great! Merge it
gh pr merge 15 --squash
```

### Bob Pulls the Update

```bash
# Bob updates his local Hearth
git fetch upstream
git merge upstream/master

# Bob's entity now has sentiment analysis too!
```

---

## What Gets Merged?

**Good candidates for master repo:**
- ✅ Bug fixes
- ✅ Performance improvements
- ✅ New features useful to most users
- ✅ Documentation improvements
- ✅ Test improvements
- ✅ Security fixes

**Keep in your fork/branch:**
- 🔀 Highly personalized features
- 🔀 Experimental features
- 🔀 Custom integrations (your specific services)
- 🔀 Personal customizations (UI themes, etc.)

---

## Entity Boundaries

**Entity knows about this model:**

From `soul.md`:
```markdown
## Development Workflow
I improve my local instance at `/opt/hearth/`.

My changes stay local unless human decides to contribute them upstream.

Workflow:
1. I propose improvement
2. Human approves
3. I create feature branch (proposal/prop-XXX)
4. Human tests and merges to their branch (user/name)
5. If useful to everyone, human creates PR to master repo
6. Maintainer reviews and merges

I don't push to remote or create PRs - human decides that.
```

---

## Benefits

### For Individual Users
- ✅ Entity improves your personal instance
- ✅ You control what gets merged locally
- ✅ You can customize freely
- ✅ You benefit from everyone else's improvements

### For Community
- ✅ Best improvements flow upstream
- ✅ Everyone benefits from collective intelligence
- ✅ Distributed development (many entities improving)
- ✅ Maintainer ensures quality and coherence

### For Entities
- ✅ Learn from each other (via merged code)
- ✅ Improve the framework they run on
- ✅ Contribute to entity ecosystem

---

## Git Commands Reference

### Setup (First Time)

```bash
# Branch model
git clone https://github.com/maintainer/hearth.git /opt/hearth
git checkout -b user/yourname

# Fork model
# Fork on GitHub first, then:
git clone https://github.com/yourname/hearth.git /opt/hearth
git remote add upstream https://github.com/maintainer/hearth.git
```

### Daily Work

```bash
# See entity's proposals
git branch | grep proposal/

# Review a proposal
git diff user/yourname..proposal/prop-001-feature

# Merge approved proposal
git checkout user/yourname
git merge proposal/prop-001-feature --no-ff

# Update from upstream
git fetch upstream
git merge upstream/master
```

### Contributing

```bash
# Push your work
git push origin user/yourname  # Branch model
git push origin master           # Fork model

# Create PR
gh pr create --title "feat: description"

# Update PR after feedback
git commit --amend
git push -f origin user/yourname
```

---

## Summary

**Local Work:**
1. Entity proposes → User approves → Entity implements in feature branch
2. User tests → User merges to their branch
3. Repeat

**Contributing Upstream:**
1. User pushes their branch/fork
2. User creates PR to master repo
3. Maintainer reviews and merges
4. Everyone pulls updates

**Result:**
- Each user/entity pair improves their instance
- Best improvements go upstream
- Everyone benefits
- Entities collectively improve the framework

**This is how open-source AI entities evolve together.** 🔥

---

## Quick Reference

```bash
# Entity made improvement, you approved it
git diff user/yourname..proposal/prop-XXX-name  # Review
git checkout user/yourname && git merge proposal/prop-XXX-name  # Merge locally

# Contribute to master repo
git push origin user/yourname  # Push
gh pr create  # Create PR

# Get updates from master repo
git fetch upstream && git merge upstream/master  # Pull updates
```
