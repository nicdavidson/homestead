"""Cronicle memory search and index management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..memory import get_memory_index

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/search")
def search_memory(
    q: str = Query(..., min_length=1),
    source: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Full-text search across all indexed documents."""
    idx = get_memory_index()
    results = idx.search(q, source=source, limit=limit)
    return [
        {
            "id": r.id,
            "source": r.source,
            "path": r.path,
            "title": r.title,
            "snippet": r.snippet,
            "rank": r.rank,
            "updated_at": r.updated_at,
        }
        for r in results
    ]


@router.get("/context")
def get_context(q: str = Query(..., min_length=1)):
    """Get formatted context string for prompt injection."""
    idx = get_memory_index()
    context = idx.get_context_for_query(q)
    return {"context": context}


@router.post("/reindex")
def reindex():
    """Full reindex of all knowledge stores."""
    idx = get_memory_index()
    stats = idx.reindex_all()
    return {"status": "ok", **stats}


@router.get("/stats")
def get_stats():
    """Get index statistics."""
    idx = get_memory_index()
    stats = idx.get_stats()
    return {
        "total_documents": stats.total_documents,
        "by_source": stats.by_source,
        "last_reindex_at": stats.last_reindex_at,
    }
