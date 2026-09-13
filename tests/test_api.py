import pytest
import io
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Verify /health endpoint returns HTTP 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_empty_message_validation():
    """Verify empty chat message returns 400 Bad Request error."""
    response = client.post("/api/chat", json={"message": "   "})
    assert response.status_code == 400
    assert "Message content cannot be empty" in response.json()["detail"]


def test_chat_missing_payload_validation():
    """Verify invalid request body returns 422 Unprocessable Entity."""
    response = client.post("/api/chat", json={})
    assert response.status_code == 422


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_chat_success_mocked(mock_get_response):
    """Verify POST /api/chat returns mocked AI response and valid session ID."""
    mock_get_response.return_value = "A Pandas DataFrame is a 2D tabular data structure."

    payload = {
        "message": "Explain Pandas DataFrame",
        "session_id": "test_session_123"
    }
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "A Pandas DataFrame is a 2D tabular data structure."
    assert data["session_id"] == "test_session_123"
    mock_get_response.assert_called_once_with(session_id="test_session_123", message="Explain Pandas DataFrame")


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_chat_code_correction_mocked(mock_get_response):
    """Verify POST /api/chat handles code correction prompt mocking."""
    mock_response = (
        "### Problem\n"
        "You used `df.head` without calling the method.\n\n"
        "### Corrected Code\n"
        "```python\n"
        "import pandas as pd\n"
        "df = pd.read_csv('data.csv')\n"
        "print(df.head())\n"
        "```\n\n"
        "### Explanation\n"
        "`head()` is a method and must be called with parentheses."
    )
    mock_get_response.return_value = mock_response

    code_prompt = "Correct this code:\nimport pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head)"
    response = client.post("/api/chat", json={"message": code_prompt})

    assert response.status_code == 200
    data = response.json()
    assert "### Corrected Code" in data["response"]
    assert "session_id" in data


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_general_technical_question_mocked(mock_get_response):
    """Verify Severus handles general non-Data Science technical questions gracefully."""
    mock_get_response.return_value = "Arduino is an open-source electronics platform based on easy-to-use hardware and software."
    
    response = client.post("/api/chat", json={"message": "What is Arduino?"})
    assert response.status_code == 200
    data = response.json()
    assert "Arduino" in data["response"]


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_prompt_generation_mocked(mock_get_response):
    """Verify Severus generates detailed prompts when requested."""
    mock_get_response.return_value = "Here is a detailed system prompt for exploratory data analysis (EDA)..."
    
    response = client.post("/api/chat", json={"message": "Create a prompt for EDA"})
    assert response.status_code == 200
    data = response.json()
    assert "prompt" in data["response"].lower()


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_code_explanation_mocked(mock_get_response):
    """Verify Severus explains code step by step when requested."""
    mock_get_response.return_value = "Line 1: Imports pandas module.\nLine 2: Reads data.csv into a DataFrame."
    
    response = client.post("/api/chat", json={"message": "Explain this code:\nimport pandas as pd\ndf = pd.read_csv('data.csv')"})
    assert response.status_code == 200
    data = response.json()
    assert "Line 1" in data["response"]


def test_clear_history_endpoint():
    """Verify POST /api/clear returns status cleared for given session ID."""
    response = client.post("/api/clear", json={"session_id": "test_session_123"})
    assert response.status_code == 200
    assert response.json() == {"status": "cleared", "session_id": "test_session_123"}


def test_get_history_endpoint():
    """Verify GET /api/history/{session_id} returns session messages list."""
    response = client.get("/api/history/test_session_123")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test_session_123"
    assert isinstance(data["messages"], list)


def test_upload_csv_endpoint():
    """Verify POST /api/upload-csv safely profiles uploaded CSV files."""
    csv_content = "Name,Age,Salary\nAlice,30,70000\nBob,25,50000\nCharlie,,80000\n"
    file_bytes = io.BytesIO(csv_content.encode('utf-8'))
    
    response = client.post(
        "/api/upload-csv",
        files={"file": ("test_data.csv", file_bytes, "text/csv")},
        data={"session_id": "csv_session_1"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "test_data.csv"
    assert data["analysis"]["num_rows"] == 3
    assert data["analysis"]["num_cols"] == 3
    assert "Age" in data["analysis"]["columns"]
