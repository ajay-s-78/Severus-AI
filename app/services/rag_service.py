import os
import re
import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from app.database.database import get_connection

logger = logging.getLogger("severus.rag_service")

# File storage directory
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "documents"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 # 10MB limit
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".xls"}


class RAGService:
    """
    RAG & Document Intelligence Service for SEVERUS AI.
    Handles text extraction, chunking, TF-IDF vector similarity retrieval,
    and grounded document question answering.
    Supports user document isolation.
    """

    def __init__(self):
        # Memory-backed vector chunks index: { (user_id, doc_id, chunk_idx): {text, filename, score...} }
        self.chunk_store: Dict[Tuple[int, int, int], Dict[str, Any]] = {}

    def extract_text_from_file(self, file_bytes: bytes, filename: str) -> str:
        """Extract text content safely from PDF, DOCX, TXT, CSV, or XLSX files."""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError("File exceeds maximum size limit of 10MB.")

        if len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        text_content = ""

        try:
            if ext == ".txt":
                text_content = file_bytes.decode("utf-8", errors="ignore")

            elif ext == ".pdf":
                import io
                import pypdf
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                extracted_pages = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text() or ""
                    extracted_pages.append(page_text)
                text_content = "\n".join(extracted_pages)

            elif ext == ".docx":
                import io
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                text_content = "\n".join(paragraphs)

            elif ext in [".csv", ".xlsx", ".xls"]:
                import io
                if ext == ".csv":
                    df = pd.read_csv(io.BytesIO(file_bytes))
                else:
                    df = pd.read_excel(io.BytesIO(file_bytes))
                
                # Format dataframe summary & top rows into clean text
                summary_lines = [
                    f"Dataset Name: {filename}",
                    f"Shape: {df.shape[0]} rows, {df.shape[1]} columns",
                    f"Columns: {', '.join(df.columns)}",
                    "\nSample Data Preview:\n" + df.head(20).to_string()
                ]
                text_content = "\n".join(summary_lines)

        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
            raise ValueError(f"Failed to read/parse document '{filename}': {str(e)}")

        text_content = text_content.strip()
        if not text_content:
            raise ValueError(f"No readable text could be extracted from '{filename}'.")

        return text_content

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Split document text into overlapping paragraph/sentence chunks."""
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            if end == len(words):
                break
            start += (chunk_size - overlap)

        return chunks

    def compute_similarity(self, query: str, document_chunk: str) -> float:
        """Compute term frequency overlap similarity between query and document chunk."""
        query_tokens = set(re.findall(r'\w+', query.lower()))
        chunk_tokens = re.findall(r'\w+', document_chunk.lower())
        if not query_tokens or not chunk_tokens:
            return 0.0

        matches = sum(1 for token in chunk_tokens if token in query_tokens)
        return matches / (math.sqrt(len(chunk_tokens)) + 1.0)

    def process_and_index_document(self, file_bytes: bytes, filename: str, user_id: int = 1) -> Dict[str, Any]:
        """Validates, extracts, chunks, and indexes a user document."""
        # Sanitize filename against path traversal
        clean_filename = os.path.basename(filename).replace("..", "").replace("/", "").replace("\\", "")
        if not clean_filename:
            clean_filename = "uploaded_document.txt"

        text_content = self.extract_text_from_file(file_bytes, clean_filename)
        chunks = self.chunk_text(text_content)

        # Save to database
        conn = get_connection()
        cursor = conn.cursor()
        ext = os.path.splitext(clean_filename)[1].lower()

        cursor.execute(
            """
            INSERT INTO user_documents (user_id, filename, file_type, file_size, chunk_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, clean_filename, ext, len(file_bytes), len(chunks))
        )
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()

        # Store chunks in in-memory vector index
        for idx, chunk_text in enumerate(chunks):
            self.chunk_store[(user_id, doc_id, idx)] = {
                "doc_id": doc_id,
                "user_id": user_id,
                "filename": clean_filename,
                "chunk_idx": idx,
                "text": chunk_text
            }

        return {
            "id": doc_id,
            "filename": clean_filename,
            "file_type": ext,
            "file_size": len(file_bytes),
            "chunk_count": len(chunks),
            "user_id": user_id
        }

    def retrieve_relevant_chunks(self, query: str, user_id: int = 1, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieves top-k most relevant document chunks for user_id matching query."""
        scored_chunks = []
        for (u_id, d_id, c_idx), chunk_data in self.chunk_store.items():
            if u_id == user_id:
                score = self.compute_similarity(query, chunk_data["text"])
                if score > 0.05:
                    scored_chunks.append({
                        "doc_id": d_id,
                        "filename": chunk_data["filename"],
                        "chunk_idx": c_idx,
                        "text": chunk_data["text"],
                        "score": score
                    })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]

    def list_user_documents(self, user_id: int = 1) -> List[Dict[str, Any]]:
        """List all uploaded documents belonging to user_id."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, filename, file_type, file_size, chunk_count, created_at FROM user_documents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def delete_user_document(self, doc_id: int, user_id: int = 1) -> bool:
        """Deletes document record and chunk index entries for user_id."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        count = cursor.rowcount
        conn.commit()
        conn.close()

        # Clear chunks from memory index
        to_delete = [k for k in self.chunk_store.keys() if k[0] == user_id and k[1] == doc_id]
        for k in to_delete:
            del self.chunk_store[k]

        return count > 0


rag_service = RAGService()
