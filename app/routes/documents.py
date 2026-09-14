from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.services.rag_service import rag_service
from app.services.ai_service import AIService
from app.core.auth import get_current_user_optional

router = APIRouter(prefix="/api/documents", tags=["Document RAG Intelligence"])
ai_service = AIService()


class QueryDocumentRequest(BaseModel):
    query: str
    session_id: Optional[str] = "rag_session"


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    user_id = current_user.get("user_id", 1) if current_user else 1
    file_bytes = await file.read()

    try:
        doc_data = rag_service.process_and_index_document(
            file_bytes=file_bytes,
            filename=file.filename or "document.txt",
            user_id=user_id
        )
        return {
            "status": "success",
            "message": f"Document '{doc_data['filename']}' successfully processed and indexed.",
            "document": doc_data
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process document: {str(e)}")


@router.get("")
def list_documents(current_user: Optional[dict] = Depends(get_current_user_optional)):
    user_id = current_user.get("user_id", 1) if current_user else 1
    docs = rag_service.list_user_documents(user_id=user_id)
    return {
        "status": "success",
        "count": len(docs),
        "documents": docs
    }


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    user_id = current_user.get("user_id", 1) if current_user else 1
    deleted = rag_service.delete_user_document(doc_id=doc_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or unauthorized.")

    return {
        "status": "success",
        "message": f"Document {doc_id} successfully deleted."
    }


@router.post("/query")
async def query_documents(
    payload: QueryDocumentRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    user_id = current_user.get("user_id", 1) if current_user else 1
    chunks = rag_service.retrieve_relevant_chunks(payload.query, user_id=user_id, top_k=3)

    if not chunks:
        return {
            "status": "success",
            "answer": "No relevant content was found in your uploaded documents for this query.",
            "sources": []
        }

    # Build context string with source references
    context_blocks = []
    sources = []
    for c in chunks:
        context_blocks.append(f"--- Document: {c['filename']} (Chunk {c['chunk_idx']+1}) ---\n{c['text']}")
        sources.append({"filename": c["filename"], "score": round(c["score"], 3)})

    context_str = "\n\n".join(context_blocks)
    prompt = f"Answer the user's question accurately using ONLY the provided document context below.\n\nDOCUMENT CONTEXT:\n{context_str}\n\nUSER QUESTION: {payload.query}"

    answer = await ai_service.get_response(session_id=payload.session_id, message=prompt)

    return {
        "status": "success",
        "answer": answer,
        "sources": sources
    }
