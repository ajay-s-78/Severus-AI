import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.rag_service import rag_service

client = TestClient(app)


def test_extract_text_txt():
    text = rag_service.extract_text_from_file(b"Supervised Learning uses labeled data.", "test.txt")
    assert "Supervised Learning" in text


def test_reject_invalid_file_extension():
    with pytest.raises(ValueError) as exc:
        rag_service.extract_text_from_file(b"data", "malicious.exe")
    assert "Unsupported file extension" in exc.value.args[0]


def test_reject_oversized_file():
    big_bytes = b"0" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError) as exc:
        rag_service.extract_text_from_file(big_bytes, "big.txt")
    assert "exceeds maximum size" in exc.value.args[0]


def test_empty_document_handling():
    with pytest.raises(ValueError) as exc:
        rag_service.extract_text_from_file(b"", "empty.txt")
    assert "empty" in exc.value.args[0].lower()


def test_chunking_and_indexing():
    sample_text = "Word " * 1000
    doc = rag_service.process_and_index_document(sample_text.encode(), "sample.txt", user_id=10)
    assert doc["chunk_count"] > 1
    assert doc["user_id"] == 10


def test_document_retrieval_and_user_isolation():
    rag_service.process_and_index_document(b"Python is a popular programming language.", "python.txt", user_id=101)
    rag_service.process_and_index_document(b"Rust is a systems programming language.", "rust.txt", user_id=102)

    # User 101 retrieves Python
    chunks_101 = rag_service.retrieve_relevant_chunks("Python", user_id=101)
    assert any("Python" in c["text"] for c in chunks_101)
    assert not any("Rust" in c["text"] for c in chunks_101)

    # User 102 retrieves Rust
    chunks_102 = rag_service.retrieve_relevant_chunks("Rust", user_id=102)
    assert any("Rust" in c["text"] for c in chunks_102)
    assert not any("Python" in c["text"] for c in chunks_102)


def test_delete_document():
    doc = rag_service.process_and_index_document(b"Content to delete.", "delete.txt", user_id=200)
    doc_id = doc["id"]

    success = rag_service.delete_user_document(doc_id, user_id=200)
    assert success is True

    # List documents for user 200
    docs = rag_service.list_user_documents(user_id=200)
    assert not any(d["id"] == doc_id for d in docs)


@pytest.mark.anyio
@patch("app.services.ai_service.AIService.get_response", new_callable=AsyncMock)
async def test_rag_api_query_mocked(mock_get_response):
    mock_get_response.return_value = "Supervised learning involves learning a function mapping inputs to output labels."

    # Index document for test user
    rag_service.process_and_index_document(b"Supervised learning algorithms build a mathematical model of a set of data that contains both the inputs and the desired outputs.", "ml_notes.txt", user_id=1)

    res = client.post("/api/documents/query", json={"query": "What is supervised learning?"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Supervised learning" in data["answer"]
    assert len(data["sources"]) > 0
