import uuid
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional
from app.services.ai_service import ai_service
from app.services.csv_service import csv_service

router = APIRouter(prefix="/api", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or code query")
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")


class ChatResponse(BaseModel):
    response: str
    session_id: str


class ClearHistoryRequest(BaseModel):
    session_id: str


class ClearHistoryResponse(BaseModel):
    status: str
    session_id: str


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint for Severus Data Science AI Assistant.
    Receives user prompt, processes via LangChain and OpenAI API, and returns formatted response.
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    # Use provided session_id or create a new UUID for session
    session_id = request.session_id if request.session_id else str(uuid.uuid4())

    try:
        response_text = await ai_service.get_response(session_id=session_id, message=message)
        return ChatResponse(response=response_text, session_id=session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {str(e)}"
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


