import uuid
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List
from langchain_core.messages import HumanMessage
from app.services.ai_service import ai_service
from app.services.csv_service import csv_service
from app.services.computer_control_service import computer_control_service
from app.services.memory_service import memory_service
from app.services.vision_service import vision_service
from app.services.jarvis_orchestrator import jarvis_orchestrator
from app.services.data_analysis_service import data_analysis_service
from app.services.ml_service import ml_service
from app.services.analytics_service import analytics_service
from app.services.speaker_verification_service import speaker_verification_service

router = APIRouter(prefix="/api", tags=["Chat & Security"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or code query")
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    image_data: Optional[str] = Field(default=None, description="Optional base64 image data URI string")
    audio_data: Optional[str] = Field(default=None, description="Optional base64 audio string for speaker verification")
    speaker_auth: Optional[str] = Field(default=None, description="Optional speaker authorization token or status")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    action_required: Optional[dict] = None
    speaker_status: Optional[str] = Field(default="VERIFICATION_UNAVAILABLE", description="Speaker identity verification result")


class ActionExecuteRequest(BaseModel):
    action_type: str
    target: str
    confirmed: bool = False
    session_id: Optional[str] = None
    audio_data: Optional[str] = None
    speaker_auth: Optional[str] = None


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


class EnrollSpeakerRequest(BaseModel):
    audio_samples: List[str] = Field(..., min_length=1, description="List of base64 voice audio samples for owner enrollment")


class VerifySpeakerRequest(BaseModel):
    audio_data: str = Field(..., description="Base64 audio string to verify against owner profile")


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint for Severus Data Science AI Assistant.
    Receives user prompt, image, and optional voice audio for speaker verification.
    Enforces Phase 11 owner security decisions on backend.
    """
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty."
        )

    # Session ID management
    session_id = request.session_id if request.session_id else str(uuid.uuid4())

    # Image Vision Data Parsing
    image_bytes = None
    image_mime = None
    if request.image_data:
        image_bytes, image_mime, err_msg = vision_service.parse_data_uri(request.image_data)
        if err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg
            )

    # Phase 11 Backend Speaker Identity Verification
    speaker_status = speaker_verification_service.verify_request(
        audio_data=request.audio_data,
        speaker_auth=request.speaker_auth
    )

    try:
        orch_res = await jarvis_orchestrator.orchestrate(
            session_id=session_id,
            message=message,
            image_bytes=image_bytes,
            image_mime=image_mime,
            speaker_status=speaker_status
        )
        return ChatResponse(
            response=orch_res["response"],
            session_id=orch_res["session_id"],
            action_required=orch_res.get("action_required"),
            speaker_status=speaker_status
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {str(e)}"
        )


@router.post("/execute-action", response_model=ActionExecuteResponse, status_code=status.HTTP_200_OK)
async def execute_action_endpoint(request: ActionExecuteRequest):
    """
    Executes a user-confirmed computer control desktop action.
    Strictly verifies backend owner speaker authorization before executing desktop control.
    """
    # Verify Backend Speaker Authorization
    speaker_status = speaker_verification_service.verify_request(
        audio_data=request.audio_data,
        speaker_auth=request.speaker_auth
    )

    if speaker_status != "AUTHORIZED_OWNER":
        return ActionExecuteResponse(
            status="blocked",
            message=f"Action Blocked: Desktop computer control execution is restricted to the verified owner. (Status: {speaker_status})",
            action_type=request.action_type,
            target=request.target
        )

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


# ---------------------------------------------------------
# Phase 11 Speaker Enrollment & Authorization Endpoints
# ---------------------------------------------------------

@router.post("/speaker/enroll", status_code=status.HTTP_200_OK)
async def enroll_speaker_endpoint(request: EnrollSpeakerRequest):
    """
    Enrolls owner speaker profile from voice audio samples.
    """
    res = speaker_verification_service.enroll_speaker(request.audio_samples)
    if res.get("status") == "error":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res.get("message"))
    return res


@router.get("/speaker/status", status_code=status.HTTP_200_OK)
async def get_speaker_status_endpoint():
    """
    Retrieves current owner speaker profile status.
    """
    return speaker_verification_service.get_speaker_status()


@router.delete("/speaker/enroll", status_code=status.HTTP_200_OK)
async def clear_speaker_profile_endpoint():
    """
    Clears current owner speaker profile.
    """
    return speaker_verification_service.clear_speaker_profile()


@router.post("/speaker/verify", status_code=status.HTTP_200_OK)
async def verify_speaker_endpoint(request: VerifySpeakerRequest):
    """
    Verifies an audio sample against stored owner speaker profile.
    """
    status_result = speaker_verification_service.verify_speaker(audio_data=request.audio_data)
    return {"speaker_status": status_result}


# ---------------------------------------------------------
# Session & Dataset Workspace Endpoints
# ---------------------------------------------------------

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
@router.post("/upload-dataset")
async def upload_dataset_endpoint(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Uploads a dataset (CSV, Excel .xlsx, JSON, TXT), performs data science workspace analysis,
    and injects structured summary into session history.
    """
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    allowed = {".csv", ".xlsx", ".xls", ".json", ".txt"}
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format '{ext}'. Supported dataset formats: CSV, Excel (.xlsx), JSON, TXT."
        )

    file_bytes = await file.read()
    analysis = data_analysis_service.analyze_dataset_bytes(file_bytes, file.filename)

    if "error" in analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=analysis["error"]
        )

    sid = session_id if session_id else str(uuid.uuid4())
    
    summary_msg = f"[System Context: User uploaded dataset '{file.filename}']\n" + analysis["summary_markdown"]
    history = ai_service.get_session_history(sid)
    history.append(HumanMessage(content=summary_msg))
    ai_service.save_message(session_id=sid, role="user", content=summary_msg)

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


@router.post("/train-ml-model")
async def train_ml_model_endpoint(
    file: UploadFile = File(...),
    target_col: str = Form(...),
    algorithm: str = Form("random_forest"),
    problem_type: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Trains a safe scikit-learn Machine Learning model (Classification or Regression)
    on an uploaded dataset and returns evaluation metrics.
    """
    file_bytes = await file.read()
    res = ml_service.train_and_evaluate(
        file_bytes=file_bytes,
        filename=file.filename,
        target_col=target_col,
        algorithm=algorithm,
        problem_type=problem_type
    )

    if "error" in res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res["error"]
        )

    sid = session_id if session_id else str(uuid.uuid4())
    summary_msg = f"[System Context: ML Model Training Result for '{file.filename}']\n" + res["summary_markdown"]
    history = ai_service.get_session_history(sid)
    history.append(HumanMessage(content=summary_msg))
    ai_service.save_message(session_id=sid, role="user", content=summary_msg)

    return {
        "status": "success",
        "session_id": sid,
        "result": res
    }


@router.post("/ml-recommendation")
async def ml_recommendation_endpoint(
    file: UploadFile = File(...),
    target_col: Optional[str] = Form(None)
):
    """
    Analyzes dataset properties and recommends optimal machine learning algorithm.
    """
    file_bytes = await file.read()
    validation_err = data_analysis_service.validate_dataset(file_bytes, file.filename)
    if validation_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_err
        )

    try:
        df = data_analysis_service.read_dataframe(file_bytes, file.filename)
        res = ml_service.recommend_model(df, target_col)
        if "error" in res:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res["error"]
            )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process dataset for recommendation: {str(e)}"
        )


@router.post("/analytics/analyze")
async def analytics_analyze_endpoint(
    file: UploadFile = File(...),
):
    file_bytes = await file.read()

    result = analytics_service.analyze_file(
        file_bytes,
        file.filename
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return {
        "status": "success",
        "filename": file.filename,
        "analysis": result
    }


@router.post("/analytics/chart")
async def analytics_chart_endpoint(
    file: UploadFile = File(...),
    chart_type: str = Form(...),
    x_column: Optional[str] = Form(None),
    y_column: Optional[str] = Form(None),
):
    file_bytes = await file.read()

    columns = [column for column in [x_column, y_column] if column]

    try:
        chart_res = analytics_service.generate_chart_from_file(
            file_bytes=file_bytes,
            filename=file.filename,
            chart_type=chart_type,
            columns=columns or None,
        )

        if isinstance(chart_res, tuple) and len(chart_res) == 2:
            img_bytes, title = chart_res
            import base64
            b64_img = base64.b64encode(img_bytes).decode("utf-8")
            chart_data = {"image_base64": b64_img, "title": title}
        elif isinstance(chart_res, dict) and "error" in chart_res:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=chart_res["error"]
            )
        else:
            chart_data = chart_res

        return {
            "status": "success",
            "filename": file.filename,
            "chart": chart_data
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chart generation failed: {str(e)}"
        )
