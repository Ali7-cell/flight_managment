from __future__ import annotations

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from apps.worker.graphs.live_chat import live_chat_graph, LiveChatState

router = APIRouter(prefix="/chat", tags=["Live Chat Assistant"])

class ChatMessageRequest(BaseModel):
    message: str
    booking_id: Optional[str] = None
    user_email: Optional[str] = None

class ChatMessageResponse(BaseModel):
    intent: str
    response_type: str
    reply: str
    flight_info_result: Optional[Dict[str, Any]] = None
    bookable_flights: Optional[List[Dict[str, Any]]] = None
    bookable_alternative_note: Optional[str] = None
    policy_pending: bool = False

@router.post("/message", response_model=ChatMessageResponse)
def post_chat_message(req: ChatMessageRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    init_state: LiveChatState = {
        "message": req.message,
        "booking_id": req.booking_id,
        "user_email": req.user_email,
        "intent": "other",
        "flight_info_result": None,
        "bookable_flights": None,
        "bookable_alternative_note": None,
        "policy_pending": False,
        "response_type": "other",
        "final_reply": "",
    }

    result = live_chat_graph.invoke(init_state)

    return ChatMessageResponse(
        intent=result.get("intent", "other"),
        response_type=result.get("response_type", "other"),
        reply=result.get("final_reply", ""),
        flight_info_result=result.get("flight_info_result"),
        bookable_flights=result.get("bookable_flights"),
        bookable_alternative_note=result.get("bookable_alternative_note"),
        policy_pending=result.get("policy_pending", False),
    )
