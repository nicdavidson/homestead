"""Backup API — export and import Homestead user data."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

# Ensure common package is importable
_common_pkg = str(Path(__file__).resolve().parent.parent.parent.parent / "packages" / "common")
if _common_pkg not in sys.path:
    sys.path.insert(0, _common_pkg)

from common.backup import export_backup, import_backup, list_backups

router = APIRouter(prefix="/api/backup", tags=["backup"])


class ExportRequest(BaseModel):
    include_logs: bool = False
    backup_dir: str | None = None


class ImportRequest(BaseModel):
    archive_path: str
    merge_strategy: str = "skip_existing"


@router.post("/export")
def api_export(body: ExportRequest | None = None):
    """Create a backup archive of all user data."""
    body = body or ExportRequest()
    data_dir = str(Path(settings.homestead_data_dir).expanduser())
    backup_dir = body.backup_dir or str(Path(data_dir) / "backups")

    try:
        result = export_backup(data_dir, backup_dir=backup_dir, include_logs=body.include_logs)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/import")
def api_import(body: ImportRequest):
    """Import data from a backup archive."""
    data_dir = str(Path(settings.homestead_data_dir).expanduser())

    try:
        result = import_backup(body.archive_path, data_dir, merge_strategy=body.merge_strategy)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archive not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/list")
def api_list():
    """List available backup archives."""
    data_dir = Path(settings.homestead_data_dir).expanduser()
    backup_dir = data_dir / "backups"
    return list_backups(str(backup_dir))
