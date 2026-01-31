"""
Hearth Core - Proposals System

Entities propose improvements to their own code.
Humans review and approve/reject.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
import json
import logging

from .config import Config, get_config

logger = logging.getLogger("hearth.proposals")


@dataclass
class Proposal:
    """A code improvement proposal from the entity."""
    id: str
    title: str
    description: str
    reasoning: str
    priority: str  # low, medium, high, critical
    target_files: List[str]  # Files to modify
    diffs: Dict[str, str]  # file_path -> unified diff
    test_plan: str
    rollback_plan: str
    created_at: str
    created_by: str = "entity"
    status: str = "pending"  # pending, approved, rejected, applied
    git_commit: Optional[str] = None  # Git commit SHA when applied
    applied_at: Optional[str] = None  # Timestamp when applied

    def to_dict(self) -> dict:
        return asdict(self)


class ProposalManager:
    """
    Manages code improvement proposals.

    Entities can:
    - Analyze code (read access to /opt/hearth/)
    - Create proposals (write to /home/{entity}/pending/)

    Humans can:
    - Review proposals (read from /home/{entity}/pending/)
    - Approve/reject proposals (move to approved/rejected/)
    - Apply changes (via `hearth proposals apply`)
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.pending_dir = self.config.entity_home / "pending"
        self.approved_dir = self.config.entity_home / "approved"
        self.rejected_dir = self.config.entity_home / "rejected"

        # Ensure directories exist
        for dir_path in [self.pending_dir, self.approved_dir, self.rejected_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def create_proposal(
        self,
        title: str,
        description: str,
        reasoning: str,
        target_files: List[str],
        diffs: Dict[str, str],
        priority: str = "medium",
        test_plan: str = "TODO: Add test plan",
        rollback_plan: str = "Revert via git or restore from backup"
    ) -> Proposal:
        """
        Create a new proposal.

        Args:
            title: Short title for the proposal
            description: Detailed description
            reasoning: Why this change is needed
            target_files: List of files to modify
            diffs: Dict of {file_path: unified_diff}
            priority: low, medium, high, critical
            test_plan: How to test the changes
            rollback_plan: How to rollback if needed

        Returns:
            Created Proposal object
        """
        # Generate proposal ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        proposal_id = f"prop-{timestamp}"

        proposal = Proposal(
            id=proposal_id,
            title=title,
            description=description,
            reasoning=reasoning,
            priority=priority,
            target_files=target_files,
            diffs=diffs,
            test_plan=test_plan,
            rollback_plan=rollback_plan,
            created_at=datetime.now().isoformat(),
            created_by="entity"
        )

        # Save to pending
        self._save_proposal(proposal)

        logger.info(f"Created proposal: {proposal_id} - {title}")
        return proposal

    def list_proposals(self, status: str = "pending") -> List[Proposal]:
        """List proposals by status."""
        if status == "pending":
            dir_path = self.pending_dir
        elif status == "approved":
            dir_path = self.approved_dir
        elif status == "rejected":
            dir_path = self.rejected_dir
        else:
            raise ValueError(f"Unknown status: {status}")

        proposals = []
        for file_path in sorted(dir_path.glob("prop-*.md"), reverse=True):
            try:
                proposal = self._load_proposal(file_path)
                proposals.append(proposal)
            except Exception as e:
                logger.warning(f"Failed to load proposal {file_path.name}: {e}")

        return proposals

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get a specific proposal by ID."""
        # Check all directories
        for dir_path in [self.pending_dir, self.approved_dir, self.rejected_dir]:
            file_path = dir_path / f"{proposal_id}.md"
            if file_path.exists():
                return self._load_proposal(file_path)
        return None

    def approve_proposal(self, proposal_id: str) -> bool:
        """Approve a proposal (moves to approved/)."""
        proposal = self.get_proposal(proposal_id)
        if not proposal or proposal.status != "pending":
            logger.error(f"Proposal {proposal_id} not found or not pending")
            return False

        # Move from pending to approved
        src = self.pending_dir / f"{proposal_id}.md"
        dst = self.approved_dir / f"{proposal_id}.md"

        proposal.status = "approved"
        self._save_proposal(proposal, dst)
        src.unlink()

        logger.info(f"Approved proposal: {proposal_id}")
        return True

    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """Reject a proposal (moves to rejected/)."""
        proposal = self.get_proposal(proposal_id)
        if not proposal or proposal.status != "pending":
            logger.error(f"Proposal {proposal_id} not found or not pending")
            return False

        # Move from pending to rejected
        src = self.pending_dir / f"{proposal_id}.md"
        dst = self.rejected_dir / f"{proposal_id}.md"

        proposal.status = "rejected"
        self._save_proposal(proposal, dst)

        # Add rejection reason to file
        if reason:
            with open(dst, 'a') as f:
                f.write(f"\n\n## Rejection Reason\n{reason}\n")

        src.unlink()

        logger.info(f"Rejected proposal: {proposal_id}")
        return True

    def apply_proposal(self, proposal_id: str, dry_run: bool = False) -> bool:
        """
        Apply an approved proposal to /opt/hearth/.

        Args:
            proposal_id: Proposal ID
            dry_run: If True, show what would be done without applying

        Returns:
            True if successful
        """
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            logger.error(f"Proposal {proposal_id} not found")
            return False

        if proposal.status != "approved":
            logger.error(f"Proposal {proposal_id} not approved (status: {proposal.status})")
            return False

        logger.info(f"Applying proposal: {proposal_id} - {proposal.title}")

        # Apply each diff
        for file_path, diff in proposal.diffs.items():
            target = Path(file_path)

            if dry_run:
                print(f"Would apply to: {target}")
                print(diff)
                continue

            # Backup original
            if target.exists():
                backup = target.with_suffix(target.suffix + '.bak')
                shutil.copy2(target, backup)
                logger.info(f"Backed up: {target} -> {backup}")

            # Apply diff
            try:
                # Write diff to temp file
                diff_file = Path(f"/tmp/{proposal_id}.patch")
                diff_file.write_text(diff)

                # Apply patch
                result = subprocess.run(
                    ['patch', '-p0', str(target), str(diff_file)],
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    logger.error(f"Failed to apply patch to {target}: {result.stderr}")
                    # Restore backup
                    if backup.exists():
                        shutil.move(backup, target)
                    return False

                logger.info(f"Applied changes to: {target}")

            except Exception as e:
                logger.error(f"Error applying diff to {target}: {e}")
                return False

        # Mark as applied
        proposal.status = "applied"
        proposal.applied_at = datetime.now().isoformat()
        file_path = self.approved_dir / f"{proposal_id}.md"
        self._save_proposal(proposal, file_path)

        logger.info(f"Successfully applied proposal: {proposal_id}")
        return True

    def commit_proposal(
        self,
        proposal_id: str,
        auto_commit: bool = False,
        create_branch: bool = True
    ) -> Optional[str]:
        """
        Commit an applied proposal to git repository.

        SAFE MODE (default): Creates feature branch for proposal
        - Entity commits to proposal/prop-XXX-name branch
        - Human reviews and merges when ready
        - Main branch stays safe

        DANGEROUS MODE (create_branch=False): Commits directly to current branch
        - Only use if you know what you're doing
        - Can break master if not careful

        Args:
            proposal_id: Proposal ID
            auto_commit: If True, commit automatically. If False, show commands only.
            create_branch: If True, create feature branch (safe, recommended)

        Returns:
            Branch name if successful, None otherwise
        """
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            logger.error(f"Proposal {proposal_id} not found")
            return None

        if proposal.status != "applied":
            logger.error(f"Proposal {proposal_id} not applied (status: {proposal.status})")
            return None

        # Check if we're in a git repository
        repo_path = Path("/opt/hearth")
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            logger.warning("Not in a git repository - skipping commit")
            return None

        # Generate branch name (sanitize title for branch name)
        safe_title = "".join(c if c.isalnum() or c in '-_' else '-' for c in proposal.title.lower())
        safe_title = safe_title[:40]  # Limit length
        branch_name = f"proposal/{proposal_id}-{safe_title}"

        if not auto_commit:
            # Show commands that would be run
            print(f"\n# To commit this proposal to git (SAFE MODE):")
            print(f"cd /opt/hearth")
            if create_branch:
                print(f"git checkout -b {branch_name}")
            files_list = " ".join(proposal.target_files)
            print(f"git add {files_list}")
            print(f'git commit -m "feat: {proposal.title}')
            print(f'')
            print(f'{proposal.description}')
            print(f'')
            print(f'Self-improvement proposal #{proposal_id}"')
            if create_branch:
                print(f"\n# Review and merge:")
                print(f"git diff master..{branch_name}")
                print(f"git checkout master && git merge {branch_name} --no-ff")
            print(f"\n# Or run: hearth proposals commit {proposal_id} --auto")
            return None

        try:
            # Create feature branch if requested (SAFE)
            if create_branch:
                # Make sure we're on master first
                result = subprocess.run(
                    ['git', 'checkout', 'master'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.warning(f"Could not checkout master: {result.stderr}")
                    # Continue anyway - might be on a different branch

                # Create feature branch
                result = subprocess.run(
                    ['git', 'checkout', '-b', branch_name],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"Failed to create branch {branch_name}: {result.stderr}")
                    return None

                logger.info(f"Created feature branch: {branch_name}")

            # Stage files
            for file_path in proposal.target_files:
                result = subprocess.run(
                    ['git', 'add', file_path],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"Failed to stage {file_path}: {result.stderr}")
                    return None

            # Commit
            commit_message = f"""feat: {proposal.title}

{proposal.description}

Self-improvement proposal #{proposal_id}
Applied at: {proposal.applied_at}
"""

            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to commit: {result.stderr}")
                return None

            # Get commit SHA
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                commit_sha = result.stdout.strip()
                proposal.git_commit = commit_sha

                # Update proposal with commit info
                file_path = self.approved_dir / f"{proposal_id}.md"
                self._save_proposal(proposal, file_path)

                if create_branch:
                    logger.info(f"Committed proposal {proposal_id} to branch {branch_name}: {commit_sha}")
                    logger.info(f"To merge: git checkout master && git merge {branch_name} --no-ff")
                    return branch_name
                else:
                    logger.info(f"Committed proposal {proposal_id}: {commit_sha}")
                    return commit_sha
            else:
                logger.error(f"Failed to get commit SHA: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error committing proposal: {e}")
            return None

    def _save_proposal(self, proposal: Proposal, file_path: Optional[Path] = None):
        """Save proposal as markdown."""
        if file_path is None:
            file_path = self.pending_dir / f"{proposal.id}.md"

        content = self._format_proposal(proposal)
        file_path.write_text(content)

        # Also save JSON metadata
        json_path = file_path.with_suffix('.json')
        json_path.write_text(json.dumps(proposal.to_dict(), indent=2))

    def _load_proposal(self, file_path: Path) -> Proposal:
        """Load proposal from file."""
        # Try JSON first
        json_path = file_path.with_suffix('.json')
        if json_path.exists():
            data = json.loads(json_path.read_text())
            return Proposal(**data)

        # Fallback: Parse markdown (basic implementation)
        # In production, would parse more robustly
        raise NotImplementedError("Markdown-only proposal loading not yet implemented")

    def _format_proposal(self, proposal: Proposal) -> str:
        """Format proposal as markdown."""
        git_info = ""
        if proposal.git_commit:
            git_info = f"**Git Commit:** `{proposal.git_commit[:8]}`\n"

        applied_info = ""
        if proposal.applied_at:
            applied_info = f"**Applied:** {proposal.applied_at}\n"

        return f"""# Proposal: {proposal.title}

**ID:** {proposal.id}
**Priority:** {proposal.priority}
**Status:** {proposal.status}
**Created:** {proposal.created_at}
**Created by:** {proposal.created_by}
{applied_info}{git_info}

## Description

{proposal.description}

## Reasoning

{proposal.reasoning}

## Target Files

{self._format_file_list(proposal.target_files)}

## Changes

{self._format_diffs(proposal.diffs)}

## Testing Plan

{proposal.test_plan}

## Rollback Plan

{proposal.rollback_plan}

---

**To approve:** `hearth proposals approve {proposal.id}`
**To reject:** `hearth proposals reject {proposal.id} "reason"`
**To apply:** `hearth proposals apply {proposal.id}`

---

## Review Notes
<!-- Human adds notes here -->
"""

    def _format_file_list(self, files: List[str]) -> str:
        """Format file list."""
        return "\n".join(f"- `{f}`" for f in files)

    def _format_diffs(self, diffs: Dict[str, str]) -> str:
        """Format diffs for display."""
        result = []
        for file_path, diff in diffs.items():
            result.append(f"### {file_path}\n\n```diff\n{diff}\n```\n")
        return "\n".join(result)


# Global instance
_proposal_manager: Optional[ProposalManager] = None


def get_proposal_manager(config: Optional[Config] = None) -> ProposalManager:
    """Get or create the global proposal manager."""
    global _proposal_manager
    if _proposal_manager is None:
        _proposal_manager = ProposalManager(config)
    return _proposal_manager
