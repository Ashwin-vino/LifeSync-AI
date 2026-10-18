import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from backend.app.schemas.chat import ChatRequest, ChatResponse, ChatMessageItem
from backend.app.services.gemini_service import generate_chat_response
from backend.app.database.supabase_client import get_chat_history, save_chat_message, get_supabase
from backend.app.auth import get_authenticated_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/message", response_model=ChatResponse)
async def send_message(req: ChatRequest, auth_user_id: str = Depends(get_authenticated_user_id)):
    try:
        effective_user = auth_user_id if auth_user_id != "default_user" else (req.user_id or "default_user")

        # 1. Save user message to Supabase
        save_chat_message(
            role="user",
            content=req.message,
            workspace=req.workspace,
            user_id=effective_user
        )

        # 2. Generate response from Gemini with FalkorDB grounding
        result = await generate_chat_response(
            message=req.message,
            workspace=req.workspace,
            history=req.history,
            user_id=effective_user
        )

        # 3. Save assistant reply to Supabase
        save_chat_message(
            role="assistant",
            content=result["reply"],
            workspace=req.workspace,
            user_id=effective_user,
            metadata={"model": result["model"]}
        )

        return ChatResponse(
            reply=result["reply"],
            workspace=result["workspace"],
            model=result["model"],
            error=result.get("error", False)
        )
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{workspace}", response_model=List[ChatMessageItem])
async def fetch_history(workspace: str, user_id: str = Depends(get_authenticated_user_id)):
    try:
        messages = get_chat_history(workspace=workspace, limit=50, user_id=user_id)
        return [
            ChatMessageItem(
                id=str(m.get("id")),
                role=m.get("role"),
                content=m.get("content"),
                workspace=m.get("workspace", workspace),
                created_at=m.get("created_at"),
                metadata=m.get("metadata")
            )
            for m in messages
        ]
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        return []

@router.delete("/history/{workspace}")
async def clear_history(workspace: str, user_id: str = Depends(get_authenticated_user_id)):
    try:
        sb = get_supabase()
        sb.table("chat_messages").delete().eq("workspace", workspace).eq("user_id", user_id).execute()
        return {"status": "cleared", "workspace": workspace}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
