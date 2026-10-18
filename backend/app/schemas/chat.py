from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatMessageItem(BaseModel):
    id: Optional[str] = None
    role: str
    content: str
    workspace: str = "home"
    created_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    workspace: str = Field("home", pattern="^(home|workout|nutrition|recovery)$")
    user_id: str = "default_user"
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    reply: str
    workspace: str
    model: str
    error: bool = False
