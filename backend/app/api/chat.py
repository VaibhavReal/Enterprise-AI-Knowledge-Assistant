"""
Chat API endpoints with SSE streaming for LLM responses.

The main endpoint here (POST /chats/{chat_id}/messages) implements
Server-Sent Events (SSE) streaming for progressive LLM response rendering.

Why SSE over WebSockets:
- Our use case is strictly one-directional after the user sends a question:
  the server streams the response, the client only reads.
- SSE works over plain HTTP/1.1 — no protocol upgrade needed.
- SSE has built-in reconnection logic in browsers.
- WebSockets would add bidirectional complexity we simply don't need.
- SSE is much simpler to implement, test, and debug.
- Leave WebSockets as future scope if real-time bidirectional features are added.

SSE wire format (each event):
    data: {"token": "Revenue"}\n\n
    data: {"token": " grew"}\n\n
    data: {"citations": [...], "done": true}\n\n
    data: [DONE]\n\n

How FastAPI StreamingResponse works:
- We pass an async generator function to StreamingResponse.
- FastAPI keeps the HTTP connection open and flushes each yielded string
  to the client immediately as it's produced.
- Setting media_type='text/event-stream' tells the browser this is SSE.
- The 'Cache-Control: no-cache' header prevents proxy caching.
- The 'X-Accel-Buffering: no' header prevents nginx from buffering the stream.

How the React frontend consumes this:
- Uses fetch() with a ReadableStream reader (not EventSource, because
  EventSource doesn't support custom request headers like Authorization).
- A TextDecoder parses the binary stream into text.
- The client splits on '\n\n' to get individual SSE events.
- Each event is parsed as JSON and either appended as a token or handled
  as a citation/done/error event.

Error handling during streaming:
- If the RAG pipeline fails BEFORE streaming starts: raise HTTPException normally.
- If LLM fails mid-stream: yield a JSON error event and close the generator.
- The frontend checks each event for an 'error' key and shows a user-friendly message.

Connection closing:
- The async generator exhausts naturally when the LLM response ends.
- FastAPI closes the StreamingResponse automatically when the generator is done.
- The frontend's ReadableStream reader receives a 'done' property = true on the reader.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json

from app.db.database import get_db
from app.db.models import User, Chat, Message
from app.schemas.chat import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from app.core.security import get_current_user
from app.core.config import get_settings
from app.rag.pipeline import FinancialRAGPipeline
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chats", tags=["Chat"])


@router.post("/", response_model=ChatResponse, status_code=201)
def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new research chat session.

    A chat can be optionally scoped to specific documents.
    If document_ids is None, the RAG pipeline will search across
    all of the user's uploaded documents.
    """
    new_chat = Chat(
        user_id=current_user.id,
        # Normalize empty string titles to None so auto-titling works correctly
        title=chat_data.title.strip() if chat_data.title and chat_data.title.strip() else None,
        document_ids=chat_data.document_ids,
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    logger.info(f"Created chat {new_chat.id} for user {current_user.id}")
    return new_chat


from typing import Optional, List

@router.get("/", response_model=List[ChatResponse])
def list_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all chats belonging to the current user, newest first."""
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(Chat.updated_at.desc())
        .all()
    )
    return chats


@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all messages in a chat, in chronological order.
    Returns 404 if the chat doesn't exist or belongs to another user.
    """
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id,
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return messages


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a financial research question and receive a streaming SSE response.

    This endpoint returns a StreamingResponse with media_type='text/event-stream'.
    See the module docstring at the top of this file for a full explanation of
    the SSE design decisions and wire format.
    """
    # Verify the chat exists and belongs to this user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id,
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Save the user's message to the database immediately.
    # We do this before RAG so the message is persisted even if generation fails.
    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=message_data.content,
    )
    db.add(user_message)
    db.commit()

    settings = get_settings()

    # Get recent conversation history for context.
    # We limit history to MAX_HISTORY_MESSAGES (default: 10) because:
    # 1. LLM context windows are finite and expensive
    # 2. Recent messages are most relevant for resolving follow-up questions
    # 3. Very long histories increase per-request LLM cost significantly
    # Future improvement: summarize old messages instead of dropping them.
    recent_messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(settings.MAX_HISTORY_MESSAGES)
        .all()
    )
    # Reverse to get chronological order (most recent last)
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(recent_messages)
    ]

    # The document scope for this request:
    # 1. If the user specified document_ids in this message, use those
    # 2. Otherwise, use the chat's default document scope
    # 3. If neither, the RAG pipeline searches all user documents
    effective_document_ids = message_data.document_ids or chat.document_ids

    # Capture primitives before generator execution to avoid DetachedInstanceError
    user_id = int(current_user.id)
    chat_id_val = int(chat.id)
    content_text = str(message_data.content)

    async def generate_sse_stream():
        """
        Async generator producing SSE-formatted strings.
        Uses a dedicated DB session for the lifecycle of the stream.
        """
        full_response = ""
        citations = []
        
        from app.db.database import SessionLocal
        stream_db = SessionLocal()

        try:
            pipeline = FinancialRAGPipeline(db=stream_db, user_id=user_id)

            async for event in pipeline.run(
                query=content_text,
                conversation_history=conversation_history[:-1],
                document_ids=effective_document_ids,
                stream=True,
            ):
                if "error" in event:
                    error_payload = json.dumps({"error": event.get("message", "An error occurred")})
                    yield f"data: {error_payload}\n\n"
                    return

                if "token" in event:
                    full_response += event["token"]
                    token_payload = json.dumps({"token": event["token"]})
                    yield f"data: {token_payload}\n\n"

                if event.get("done"):
                    citations = event.get("citations", [])

            # Persist the complete assistant response to the database
            assistant_message = Message(
                chat_id=chat_id_val,
                role="assistant",
                content=full_response,
                sources=citations,
            )
            stream_db.add(assistant_message)

            # Auto-title the chat from the first user question if not already titled
            chat_obj = stream_db.query(Chat).filter(Chat.id == chat_id_val).first()
            # Auto-title if title is None or an empty string
            if chat_obj and not (chat_obj.title and chat_obj.title.strip()):
                chat_obj.title = content_text[:100]

            stream_db.commit()
            logger.info(f"Saved assistant message to chat {chat_id_val} ({len(full_response)} chars, {len(citations)} citations)")

            # Send the final event with citations
            done_payload = json.dumps({"citations": citations, "done": True})
            yield f"data: {done_payload}\n\n"

            # Standard SSE stream terminator
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error for chat {chat_id_val}: {type(e).__name__}: {str(e)}")
            error_payload = json.dumps({
                "error": f"Generation notice: {str(e)}"
            })
            yield f"data: {error_payload}\n\n"
        finally:
            stream_db.close()


    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Tells nginx not to buffer SSE events — critical for streaming to work
            "X-Accel-Buffering": "no",
            # Allow cross-origin access (CORS for SSE)
            "Access-Control-Allow-Origin": "*",
        },
    )
