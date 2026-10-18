import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Depends
from backend.app.auth import get_authenticated_user_id

from backend.app.memory.memory_manager import MemoryManager
from backend.app.memory.graph_service import get_graph_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])

class MemoryFactCreateSchema(BaseModel):
    fact_type: str = Field(..., pattern="^(goal|preference|injury|habit|milestone|observation)$")
    content: str = Field(..., min_length=3, max_length=1000)
    provenance: str = Field(default="explicit_user_statement")
    confidence: float = Field(default=1.0, ge=0.1, le=1.0)
    tags: Optional[List[str]] = None

class MemoryFactUpdateSchema(BaseModel):
    content: str = Field(..., min_length=3, max_length=1000)

class MemoryFactResponseSchema(BaseModel):
    id: str
    fact_type: str
    content: str
    provenance: str
    confidence: float
    tags: List[str] = []
    status: str
    created_at: Optional[str] = None

@router.get("/facts", response_model=List[MemoryFactResponseSchema])
async def list_memories(user_id: str = Depends(get_authenticated_user_id), status: str = "active"):
    """Inspect stored memory facts for the authenticated user."""
    try:
        data = MemoryManager.list_user_memories(user_id=user_id, status=status)
        return [
            MemoryFactResponseSchema(
                id=str(row["id"]),
                fact_type=row.get("fact_type", "observation"),
                content=row.get("content", ""),
                provenance=row.get("provenance", "explicit_user_statement"),
                confidence=float(row.get("confidence", 1.0)),
                tags=row.get("tags") or [],
                status=row.get("status", "active"),
                created_at=row.get("created_at")
            )
            for row in data
        ]
    except Exception as e:
        logger.error(f"Error listing memory facts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/facts", response_model=MemoryFactResponseSchema)
async def create_memory(req: MemoryFactCreateSchema, user_id: str = Depends(get_authenticated_user_id)):
    """Explicitly save a memory fact with real Gemini embedding and FalkorDB graph node."""
    try:
        saved = MemoryManager.save_memory_fact(
            user_id=user_id,
            fact_type=req.fact_type,
            content=req.content,
            provenance=req.provenance,
            confidence=req.confidence,
            tags=req.tags
        )
        return MemoryFactResponseSchema(
            id=saved["id"],
            fact_type=saved["fact_type"],
            content=saved["content"],
            provenance=saved["provenance"],
            confidence=saved["confidence"],
            tags=saved["tags"],
            status=saved["status"]
        )
    except Exception as e:
        logger.error(f"Error creating memory fact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/facts/{fact_id}")
async def correct_memory(fact_id: str, req: MemoryFactUpdateSchema, user_id: str = Depends(get_authenticated_user_id)):
    """Correct a stored memory fact across both Supabase and FalkorDB graph memory."""
    try:
        success = MemoryManager.correct_user_memory(user_id=user_id, fact_id=fact_id, new_content=req.content)
        return {"status": "corrected", "id": fact_id, "success": success}
    except Exception as e:
        logger.error(f"Error correcting memory fact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/facts/{fact_id}")
async def delete_memory(fact_id: str, user_id: str = Depends(get_authenticated_user_id)):
    """Delete a memory fact across Supabase and FalkorDB graph memory."""
    try:
        success = MemoryManager.delete_user_memory(user_id=user_id, fact_id=fact_id)
        return {"status": "deleted", "id": fact_id, "success": success}
    except Exception as e:
        logger.error(f"Error deleting memory fact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph-stats")
async def get_graph_overview(user_id: str = Depends(get_authenticated_user_id)):
    """Return live node and edge counts in FalkorDB Cloud graph."""
    try:
        return get_graph_stats(user_id=user_id)
    except Exception as e:
        logger.error(f"Error getting graph overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{workspace}")
async def delete_conversation(workspace: str, user_id: str = Depends(get_authenticated_user_id)):
    """Delete conversation history across storage layers."""
    try:
        success = MemoryManager.delete_conversation_across_layers(user_id=user_id, workspace=workspace)
        return {"status": "cleared", "workspace": workspace, "success": success}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
