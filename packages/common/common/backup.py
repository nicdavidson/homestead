"""Homestead backup: export and import user data as .hpa archives.

An .hpa (Homestead Personal Archive) is a gzipped tarball containing
journal entries, scratchpad notes, skills, SQLite databases, and a
manifest.json with metadata.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_VERSION = "1.0.0"
_HOMESTEAD_VERSION = "0.1.0"


def export_backup(
    data_dir: str | Path,
    backup_dir: str | Path | None = None,
    include_logs: bool = False,
) -> dict:
    """Create a .hpa backup archive of user data.

    Returns dict with archive_path, size_bytes, and manifest.
    """
    data_dir = Path(data_dir).expanduser()
    if backup_dir is None:
        backup_dir = data_dir / "backups"
    backup_dir = Path(backup_dir).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive_name = f"homestead-backup-{ts}.hpa"
    archive_path = backup_dir / archive_name

    manifest = {
        "version": _VERSION,
        "homestead_version": _HOMESTEAD_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": os.environ.get("USER", "unknown"),
        "contents": {},
    }

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "staging"
        staging.mkdir()

        # -- Journal --
        journal_dir = data_dir / "journal"
        count = _copy_tree(journal_dir, staging / "journal", "*.md")
        manifest["contents"]["journal_entries"] = count

        # -- Scratchpad --
        scratchpad_dir = data_dir / "scratchpad"
        count = _copy_tree(scratchpad_dir, staging / "scratchpad")
        manifest["contents"]["scratchpad_files"] = count

        # -- Skills --
        skills_dir = data_dir / "skills"
        count = _copy_tree(skills_dir, staging / "skills", "*.md")
        manifest["contents"]["skills"] = count

        # -- Databases --
        db_dir = staging / "databases"
        db_dir.mkdir()
        db_count = 0
        for db_name, db_subpath in [
            ("usage.db", "usage.db"),
            ("tasks.db", "steward/tasks.db"),
            ("jobs.db", "almanac/jobs.db"),
        ]:
            src = data_dir / db_subpath
            if src.exists():
                # Use SQLite backup API for safe copy
                _safe_copy_db(src, db_dir / db_name)
                db_count += 1
        manifest["contents"]["databases"] = db_count

        # -- Config --
        config_file = data_dir / "config_overrides.json"
        if config_file.exists():
            config_dir = staging / "config"
            config_dir.mkdir()
            shutil.copy2(config_file, config_dir / "config_overrides.json")
            manifest["contents"]["config"] = True
        else:
            manifest["contents"]["config"] = False

        # -- Logs (optional) --
        if include_logs:
            log_dir = staging / "logs"
            log_dir.mkdir()
            for logfile in data_dir.glob("*.log"):
                shutil.copy2(logfile, log_dir / logfile.name)
            wt = data_dir / "watchtower.db"
            if wt.exists():
                _safe_copy_db(wt, log_dir / "watchtower.db")
            manifest["contents"]["logs"] = True

        # -- Write manifest --
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # -- Create tarball --
        with tarfile.open(archive_path, "w:gz") as tar:
            for child in staging.iterdir():
                tar.add(child, arcname=child.name)

    size = archive_path.stat().st_size
    checksum = _sha256(archive_path)

    log.info("Backup created: %s (%d bytes, sha256=%s)", archive_path, size, checksum[:12])

    return {
        "archive_path": str(archive_path),
        "size_bytes": size,
        "checksum": f"sha256:{checksum}",
        "manifest": manifest,
    }


def import_backup(
    archive_path: str | Path,
    data_dir: str | Path,
    merge_strategy: str = "skip_existing",
) -> dict:
    """Import data from a .hpa backup archive.

    merge_strategy:
      - skip_existing: Don't overwrite existing files/databases
      - overwrite: Replace existing data with imported data
    """
    archive_path = Path(archive_path)
    data_dir = Path(data_dir).expanduser()

    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    imported: dict[str, int] = {}
    skipped: list[str] = []
    errors: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = Path(tmp) / "extract"
        extract_dir.mkdir()

        # Extract
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_dir, filter="data")

        # Validate manifest
        manifest_path = extract_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("Invalid archive: missing manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        log.info("Importing backup from %s (version %s)", manifest.get("exported_at"), manifest.get("version"))

        # -- Journal --
        imported["journal_entries"] = _import_tree(
            extract_dir / "journal", data_dir / "journal", merge_strategy, skipped
        )

        # -- Scratchpad --
        imported["scratchpad_files"] = _import_tree(
            extract_dir / "scratchpad", data_dir / "scratchpad", merge_strategy, skipped
        )

        # -- Skills --
        imported["skills"] = _import_tree(
            extract_dir / "skills", data_dir / "skills", merge_strategy, skipped
        )

        # -- Databases --
        db_dir = extract_dir / "databases"
        db_count = 0
        if db_dir.exists():
            for db_name, dest_subpath in [
                ("usage.db", "usage.db"),
                ("tasks.db", "steward/tasks.db"),
                ("jobs.db", "almanac/jobs.db"),
            ]:
                src = db_dir / db_name
                dest = data_dir / dest_subpath
                if not src.exists():
                    continue
                if dest.exists() and merge_strategy == "skip_existing":
                    skipped.append(f"databases/{db_name}")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, dest)
                    db_count += 1
                except Exception as exc:
                    errors.append(f"databases/{db_name}: {exc}")
        imported["databases"] = db_count

        # -- Config --
        config_src = extract_dir / "config" / "config_overrides.json"
        if config_src.exists():
            config_dest = data_dir / "config_overrides.json"
            if config_dest.exists() and merge_strategy == "skip_existing":
                skipped.append("config_overrides.json")
            else:
                shutil.copy2(config_src, config_dest)
                imported["config"] = 1

        # -- Logs (optional) --
        logs_dir = extract_dir / "logs"
        if logs_dir.exists():
            for f in logs_dir.iterdir():
                dest = data_dir / f.name
                if dest.exists() and merge_strategy == "skip_existing":
                    skipped.append(f"logs/{f.name}")
                    continue
                shutil.copy2(f, dest)

    log.info("Import complete: %s (skipped=%d, errors=%d)", imported, len(skipped), len(errors))

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "manifest": manifest,
    }


def list_backups(backup_dir: str | Path) -> list[dict]:
    """List available .hpa backup archives."""
    backup_dir = Path(backup_dir).expanduser()
    if not backup_dir.exists():
        return []

    backups = []
    for f in sorted(backup_dir.glob("*.hpa"), reverse=True):
        entry = {
            "filename": f.name,
            "path": str(f),
            "size_bytes": f.stat().st_size,
            "created_at": f.stat().st_mtime,
        }
        # Try to read manifest
        try:
            with tarfile.open(f, "r:gz") as tar:
                member = tar.getmember("manifest.json")
                fobj = tar.extractfile(member)
                if fobj:
                    entry["manifest"] = json.loads(fobj.read().decode("utf-8"))
        except Exception:
            entry["manifest"] = None
        backups.append(entry)

    return backups


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_tree(src_dir: Path, dest_dir: Path, glob: str = "*") -> int:
    """Copy files from src_dir to dest_dir. Returns count."""
    if not src_dir.exists():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src_dir.glob(glob):
        if f.is_file():
            shutil.copy2(f, dest_dir / f.name)
            count += 1
    return count


def _import_tree(
    src_dir: Path, dest_dir: Path, merge_strategy: str, skipped: list[str]
) -> int:
    """Import files from extracted archive to data dir."""
    if not src_dir.exists():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src_dir.iterdir():
        if not f.is_file():
            continue
        dest = dest_dir / f.name
        if dest.exists() and merge_strategy == "skip_existing":
            skipped.append(f"{src_dir.name}/{f.name}")
            continue
        shutil.copy2(f, dest)
        count += 1
    return count


def _safe_copy_db(src: Path, dest: Path) -> None:
    """Copy SQLite database using the backup API for consistency."""
    try:
        src_conn = sqlite3.connect(str(src))
        dest_conn = sqlite3.connect(str(dest))
        src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()
    except Exception:
        # Fallback to file copy
        shutil.copy2(src, dest)


def _sha256(path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
