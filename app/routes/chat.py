import uuid
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional
from app.services.ai_service import ai_service
from app.services.csv_service import csv_service
from app.services.computer_control_service import computer_control_service
from app.services.memory_service import memory_service
from app.services.vision_service import vision_service

router = APIRouter(prefix="/api", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or code query")
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    image_data: Optional[str] = Field(default=None, description="Optional base64 image data URI string")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    action_required: Optional[dict] = None


class ActionExecuteRequest(BaseModel):
    action_type: str
    target: str
    confirmed: bool = False
    session_id: Optional[str] = None


class ActionExecuteResponse(BaseModel):
    status: str
    message: str
    action_type: Optional[str] = None
    target: Optional[str] = None


class ClearHistoryRequest(BaseModel):
    session_id: str


class ClearHistoryResponse(BaseModel):
    status: str
    session_id: str


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint for Severus Data Science AI Assistant.
    Receives user prompt and optional image, checks for desktop action intents or processes via LangChain/AI service.
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    # Use provided session_id or create a new UUID for session
    session_id = request.session_id if request.session_id else str(uuid.uuid4())

    # Image Vision Data Validation
    image_bytes = None
    image_mime = None
    if request.image_data:
        image_bytes, image_mime, err_msg = vision_service.parse_data_uri(request.image_data)
        if err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg
            )

    # Detect desktop action intent
    action_intent = computer_control_service.detect_action_intent(message)
    if action_intent:
        if action_intent.get("action_type") == "blocked":
            reason = action_intent.get("reason", "Prohibited by safety policy.")
            blocked_msg = f"⚠️ **Action Blocked**: {reason}"
            return ChatResponse(response=blocked_msg, session_id=session_id)
        else:
            act_type = action_intent["action_type"]
            target = action_intent["target"]
            prompt_msg = f"🖥️ **Confirmation Required**: Would you like me to proceed with `{act_type}` on target `{target}`?"
            return ChatResponse(
                response=prompt_msg,
                session_id=session_id,
                action_required={"action_type": act_type, "target": target}
            )

    try:
        response_text = await ai_service.get_response(
            session_id=session_id,
            message=message,
            image_bytes=image_bytes,
            image_mime=image_mime
        )
        return ChatResponse(response=response_text, session_id=session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {str(e)}"
        )


@router.post("/execute-action", response_model=ActionExecuteResponse, status_code=status.HTTP_200_OK)
async def execute_action_endpoint(request: ActionExecuteRequest):
    """
    Executes a user-confirmed computer control desktop action.
    """
    result = computer_control_service.execute_action(
        action_type=request.action_type,
        target=request.target,
        confirmed=request.confirmed
    )
    return ActionExecuteResponse(
        status=result.get("status", "error"),
        message=result.get("message", ""),
        action_type=result.get("action_type"),
        target=result.get("target")
    )


@router.post("/clear", response_model=ClearHistoryResponse, status_code=status.HTTP_200_OK)
async def clear_history_endpoint(request: ClearHistoryRequest):
    """
    Clears conversation history for the given session ID.
    """
    session_id = request.session_id
    ai_service.clear_session_history(session_id)
    return ClearHistoryResponse(status="cleared", session_id=session_id)


@router.get("/history/{session_id}")
async def get_history_endpoint(session_id: str):
    """
    Retrieves conversation history for a given session ID.
    """
    messages = ai_service.get_session_messages_json(session_id)
    return {"session_id": session_id, "messages": messages}


@router.post("/upload-csv")
async def upload_csv_endpoint(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Uploads a CSV file, computes safe metadata profile, and optionally injects summary into session history.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV files (.csv) are supported."
        )

    file_bytes = await file.read()
    analysis = csv_service.analyze_csv_bytes(file_bytes, file.filename)

    if "error" in analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=analysis["error"]
        )

    sid = session_id if session_id else str(uuid.uuid4())
    
    # Prepend dataset profile summary into conversation history
    summary_msg = f"[System Context: User uploaded CSV dataset '{file.filename}']\n" + analysis["summary_markdown"]
    ai_service.get_session_history(sid)  # ensure session exists

    return {
        "status": "success",
        "session_id": sid,
        "filename": file.filename,
        "analysis": analysis,
        "summary_msg": summary_msg
    }


@router.get("/memory")
async def get_memory_endpoint():
    """
    Retrieves stored user memories across sessions.
    """
    memories = memory_service.get_all_memories()
    return {"status": "success", "memories": memories}


@router.delete("/memory")
async def clear_memory_endpoint():
    """
    Clears all stored user conversation memories.
    """
    count = memory_service.clear_all_memories()
    return {"status": "cleared", "deleted_count": count}




