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
    mock_get_response.assert_called_once_with(
        session_id="test_session_123",
        message="Explain Pandas DataFrame",
        image_bytes=None,
        image_mime=None
    )


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


def test_search_service_classifier():
    """Verify search_service accurately identifies queries requiring real-time web search."""
    from app.services.search_service import search_service

    assert search_service.should_search("Explain Pandas DataFrame") is False
    assert search_service.should_search("How to fix KeyError in Python?") is False
    assert search_service.should_search("What is the latest release of Python?") is True
    assert search_service.should_search("Recent news about artificial intelligence in 2026") is True


@patch("app.services.search_service.search_service.search")
@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_web_search_query_mocked(mock_get_response, mock_search):
    """Verify web search results are retrieved and sources cited when real-time info is requested."""
    mock_search.return_value = [
        {
            "title": "Python 3.14 Release Notes",
            "snippet": "Python 3.14 includes performance improvements and new typing features.",
            "url": "https://docs.python.org/3.14/"
        }
    ]
    mock_get_response.return_value = (
        "Python 3.14 is the latest release...\n\n"
        "### Sources\n"
        "- [Python 3.14 Release Notes](https://docs.python.org/3.14/)"
    )

    response = client.post("/api/chat", json={"message": "What is the latest release of Python?"})
    assert response.status_code == 200
    data = response.json()
    assert "Python 3.14" in data["response"]
    assert "### Sources" in data["response"]


def test_computer_control_intent_detection():
    """Verify ComputerControlService detects open URL, app, path, and blocked actions."""
    from app.services.computer_control_service import computer_control_service

    # URL Intent
    intent = computer_control_service.detect_action_intent("open https://google.com")
    assert intent is not None
    assert intent["action_type"] == "open_url"
    assert intent["target"] == "https://google.com"

    # Allowlisted App Intent
    intent = computer_control_service.detect_action_intent("open notepad")
    assert intent is not None
    assert intent["action_type"] == "open_app"
    assert intent["target"] == "notepad"

    # Blocked Shell / Admin App Intent
    intent = computer_control_service.detect_action_intent("open regedit")
    assert intent is not None
    assert intent["action_type"] == "blocked"

    # Prohibited dangerous pattern
    intent = computer_control_service.detect_action_intent("open cmd /c rm -rf C:/")
    assert intent is not None
    assert intent["action_type"] == "blocked"


def test_computer_control_confirmation_required():
    """Verify executing actions without user confirmation returns status confirmation_required."""
    from app.services.computer_control_service import computer_control_service

    res = computer_control_service.execute_action(action_type="open_app", target="notepad", confirmed=False)
    assert res["status"] == "confirmation_required"
    assert "Confirmation required" in res["message"]


def test_computer_control_blocked_execution():
    """Verify forbidden app or shell execution is strictly blocked even if confirmed is True."""
    from app.services.computer_control_service import computer_control_service

    res = computer_control_service.execute_action(action_type="open_app", target="regedit", confirmed=True)
    assert res["status"] == "blocked"

    res = computer_control_service.execute_action(action_type="blocked", target="rm -rf /", confirmed=True)
    assert res["status"] == "blocked"


@patch("webbrowser.open")
def test_execute_action_endpoint_success(mock_web_open):
    """Verify POST /api/execute-action endpoint executes confirmed URL action."""
    mock_web_open.return_value = True

    response = client.post("/api/execute-action", json={
        "action_type": "open_url",
        "target": "https://python.org",
        "confirmed": True,
        "speaker_auth": "AUTHORIZED_OWNER"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "python.org" in data["target"]
    mock_web_open.assert_called_once_with("https://python.org")


def test_memory_service_save_and_retrieve():
    """Verify MemoryService saves and retrieves user memories across sessions."""
    from app.services.memory_service import memory_service

    memory_service.clear_all_memories()
    assert memory_service.save_memory(key="user_framework", value="FastAPI", category="preference") is True

    memories = memory_service.get_relevant_memories("framework")
    assert len(memories) >= 1
    keys = [m["key"] for m in memories]
    assert "user_framework" in keys


def test_memory_service_secret_filtering():
    """Verify MemoryService strictly filters out API keys, passwords, and tokens."""
    from app.services.memory_service import memory_service

    # Check secret detection regex
    assert memory_service.contains_secret("AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5") is True
    assert memory_service.contains_secret("sk-proj-1234567890abcdef1234567890") is True
    assert memory_service.contains_secret("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9") is True
    assert memory_service.contains_secret("api_key=secret_value_123") is True

    # Check saving secrets is rejected
    saved = memory_service.save_memory(key="api_key", value="AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5")
    assert saved is False

    memories = memory_service.get_all_memories()
    for m in memories:
        assert "AIzaSy" not in m["value"]
        assert "sk-" not in m["value"]


def test_memory_service_fact_extraction():
    """Verify automatic fact extraction from user prompt statements."""
    from app.services.memory_service import memory_service

    memory_service.clear_all_memories()

    saved_keys = memory_service.extract_and_save_facts("My name is SeverusTester and I prefer dark mode theme.")
    assert "user_name" in saved_keys
    assert "user_preference" in saved_keys

    memories = memory_service.get_all_memories()
    memory_dict = {m["key"]: m["value"] for m in memories}
    assert memory_dict.get("user_name") == "SeverusTester"
    assert "dark mode" in memory_dict.get("user_preference", "")


def test_memory_service_clear():
    """Verify clearing memories removes all entries from user_memories table."""
    from app.services.memory_service import memory_service

    memory_service.save_memory("test_key", "test_val")
    assert len(memory_service.get_all_memories()) > 0

    count = memory_service.clear_all_memories()
    assert count >= 1
    assert len(memory_service.get_all_memories()) == 0


def test_memory_api_endpoints():
    """Verify GET /api/memory and DELETE /api/memory endpoints."""
    from app.services.memory_service import memory_service
    memory_service.clear_all_memories()
    memory_service.save_memory("favorite_lang", "Python")

    # GET /api/memory
    get_res = client.get("/api/memory")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["status"] == "success"
    assert any(m["key"] == "favorite_lang" for m in data["memories"])

    # DELETE /api/memory
    del_res = client.delete("/api/memory")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "cleared"
    assert del_data["deleted_count"] >= 1


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_vision_valid_image_mocked(mock_get_response):
    """Verify POST /api/chat handles image understanding requests with mocked Gemini."""
    mock_get_response.return_value = "The image shows a bar chart representing monthly revenue growth."

    # 1x1 transparent PNG base64
    valid_png_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    payload = {
        "message": "What is in this image?",
        "session_id": "vision_session_1",
        "image_data": valid_png_base64
    }

    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "bar chart" in data["response"]
    assert data["session_id"] == "vision_session_1"
    assert mock_get_response.called


def test_vision_invalid_file_type():
    """Verify POST /api/chat rejects unsupported image file formats with 400 Bad Request."""
    invalid_gif_base64 = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

    payload = {
        "message": "Analyze this GIF image",
        "image_data": invalid_gif_base64
    }

    response = client.post("/api/chat", json=payload)
    assert response.status_code == 400
    assert "Unsupported MIME type" in response.json()["detail"]


def test_vision_oversized_file():
    """Verify VisionService rejects images larger than 10 MB."""
    from app.services.vision_service import vision_service

    # Create dummy 11 MB bytes
    oversized_bytes = b"0" * (11 * 1024 * 1024)
    err = vision_service.validate_image_bytes(oversized_bytes, "large_photo.jpg")
    assert err is not None
    assert "exceeds maximum allowed limit of 10 MB" in err


def test_vision_missing_or_corrupt_data():
    """Verify VisionService handles invalid base64 data URIs gracefully."""
    from app.services.vision_service import vision_service

    bytes_out, mime_out, err = vision_service.parse_data_uri("data:image/png;base64,NOT_VALID_BASE64_!!!")
    assert bytes_out is None
    assert err is not None


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_vision_text_chat_preservation(mock_get_response):
    """Verify normal text-only chat requests remain unaffected by vision feature integration."""
    mock_get_response.return_value = "Standard text response without image."

    response = client.post("/api/chat", json={"message": "Hello Severus"})
    assert response.status_code == 200
    assert response.json()["response"] == "Standard text response without image."


def test_jarvis_intent_classification():
    """Verify JarvisOrchestrator accurately classifies intents across capabilities."""
    from app.services.jarvis_orchestrator import jarvis_orchestrator

    # Computer Control Intent
    intent = jarvis_orchestrator.classify_intent("open notepad")
    assert intent["primary_intent"] == "computer_control"
    assert intent["action_intent"] is not None

    # Web Search Intent
    intent = jarvis_orchestrator.classify_intent("What is the latest release of Python?")
    assert intent["primary_intent"] == "web_search"
    assert intent["needs_search"] is True

    # Memory Intent
    intent = jarvis_orchestrator.classify_intent("Remember that my name is Alice")
    assert intent["primary_intent"] == "memory"
    assert intent["is_memory_query"] is True

    # Vision Intent
    intent = jarvis_orchestrator.classify_intent("Describe image", has_image=True)
    assert intent["primary_intent"] == "vision"
    assert intent["has_image"] is True

    # Combined Vision + Search Intent
    intent = jarvis_orchestrator.classify_intent("What is the latest news about this chart image?", has_image=True)
    assert intent["primary_intent"] == "vision_search"


@patch("app.services.jarvis_orchestrator.ai_service.get_response", new_callable=AsyncMock)
def test_jarvis_orchestrate_routing(mock_get_response):
    """Verify JarvisOrchestrator orchestrates AI responses with status indicators."""
    import asyncio
    from app.services.jarvis_orchestrator import jarvis_orchestrator

    mock_get_response.return_value = "At your service."

    result = asyncio.run(jarvis_orchestrator.orchestrate(session_id="s1", message="Hello Severus"))
    assert result["response"] == "At your service."
    assert result["intent"] == "general"
    assert result["status_text"] == "Ready"


def test_jarvis_orchestrate_computer_control_safety():
    """Verify JarvisOrchestrator preserves mandatory two-step confirmation for desktop actions."""
    import asyncio
    from app.services.jarvis_orchestrator import jarvis_orchestrator

    result = asyncio.run(jarvis_orchestrator.orchestrate(session_id="s1", message="open calculator", speaker_status="AUTHORIZED_OWNER"))
    assert result["intent"] == "computer_control"
    assert result["status_text"] == "Awaiting Confirmation"
    assert result["action_required"]["action_type"] == "open_app"
    assert result["action_required"]["target"] == "calculator"


def test_data_analysis_service_csv():
    """Verify DataAnalysisService parses CSV datasets, missing values, duplicates, and correlations."""
    from app.services.data_analysis_service import data_analysis_service

    csv_data = "Age,Salary,Score\n25,50000,80\n30,70000,90\n25,50000,80\n35,,95\n"
    res = data_analysis_service.analyze_dataset_bytes(csv_data.encode("utf-8"), "test.csv")

    assert "error" not in res
    assert res["num_rows"] == 4
    assert res["num_cols"] == 3
    assert res["duplicate_rows"] == 1
    assert res["missing_counts"]["Salary"] == 1
    assert len(res["numeric_columns"]) == 3
    assert len(res["correlations"]) >= 1


def test_data_analysis_service_excel():
    """Verify DataAnalysisService parses Excel (.xlsx) dataset bytes."""
    import pandas as pd
    from app.services.data_analysis_service import data_analysis_service

    df = pd.DataFrame({"Feature1": [1, 2, 3], "Feature2": [10.5, 20.5, 30.5]})
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_bytes = excel_buffer.getvalue()

    res = data_analysis_service.analyze_dataset_bytes(excel_bytes, "data.xlsx")
    assert "error" not in res
    assert res["num_rows"] == 3
    assert res["num_cols"] == 2
    assert "Feature1" in res["columns"]


def test_data_analysis_service_json():
    """Verify DataAnalysisService parses JSON dataset bytes."""
    from app.services.data_analysis_service import data_analysis_service

    json_str = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
    res = data_analysis_service.analyze_dataset_bytes(json_str.encode("utf-8"), "users.json")

    assert "error" not in res
    assert res["num_rows"] == 2
    assert res["num_cols"] == 2
    assert "age" in res["columns"]


def test_data_analysis_service_txt():
    """Verify DataAnalysisService parses TXT dataset bytes."""
    from app.services.data_analysis_service import data_analysis_service

    txt_data = "ID,Val\n1,10\n2,20\n"
    res = data_analysis_service.analyze_dataset_bytes(txt_data.encode("utf-8"), "log.txt")

    assert "error" not in res
    assert res["num_rows"] >= 2


def test_data_analysis_service_invalid_extension():
    """Verify DataAnalysisService rejects unsupported file formats."""
    from app.services.data_analysis_service import data_analysis_service

    res = data_analysis_service.analyze_dataset_bytes(b"content", "script.py")
    assert "error" in res
    assert "Unsupported file format" in res["error"]


def test_data_analysis_service_oversized():
    """Verify DataAnalysisService rejects datasets > 15 MB."""
    from app.services.data_analysis_service import data_analysis_service

    large_bytes = b"0" * (16 * 1024 * 1024)
    res = data_analysis_service.analyze_dataset_bytes(large_bytes, "big.csv")
    assert "error" in res
    assert "exceeds maximum allowed limit of 15 MB" in res["error"]


def test_data_analysis_service_corrupt():
    """Verify DataAnalysisService handles corrupt unparseable data gracefully."""
    from app.services.data_analysis_service import data_analysis_service

    res = data_analysis_service.analyze_dataset_bytes(b"CORRUPT_NOT_EXCEL", "corrupt.xlsx")
    assert "error" in res
    assert "Failed to analyze dataset" in res["error"]


def test_jarvis_data_analysis_intent():
    """Verify JarvisOrchestrator detects data_analysis intent for dataset queries."""
    from app.services.jarvis_orchestrator import jarvis_orchestrator

    intent = jarvis_orchestrator.classify_intent("Which columns have missing values in the dataset?")
    assert intent["primary_intent"] == "data_analysis"
    assert intent["is_ds_query"] is True


def test_upload_dataset_endpoint():
    """Verify POST /api/upload-dataset endpoint handles multi-format uploads."""
    json_str = '[{"a": 1, "b": 2}, {"a": 3, "b": 4}]'
    file_bytes = io.BytesIO(json_str.encode("utf-8"))

    response = client.post(
        "/api/upload-dataset",
        files={"file": ("dataset.json", file_bytes, "application/json")},
        data={"session_id": "ds_session_1"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "dataset.json"
    assert data["analysis"]["num_rows"] == 2


# ==============================================================================
# PHASE 9: ADVANCED MACHINE LEARNING WORKSPACE TESTS
# ==============================================================================

def test_ml_service_classification_algorithms():
    """Verify MLService trains and evaluates all supported classification algorithms."""
    from app.services.ml_service import ml_service

    # Create dummy classification dataset
    csv_data = (
        "Age,Income,Category,Churn\n"
        "25,50000,Low,0\n"
        "45,120000,High,1\n"
        "35,80000,Medium,0\n"
        "50,140000,High,1\n"
        "23,30000,Low,0\n"
        "38,95000,Medium,1\n"
        "29,62000,Low,0\n"
        "48,130000,High,1\n"
        "31,71000,Medium,0\n"
        "55,150000,High,1\n"
    )
    file_bytes = csv_data.encode("utf-8")

    algos = ["logistic_regression", "decision_tree", "random_forest", "knn"]
    for algo in algos:
        res = ml_service.train_and_evaluate(
            file_bytes=file_bytes,
            filename="churn.csv",
            target_col="Churn",
            algorithm=algo,
            problem_type="classification"
        )
        assert "error" not in res, f"Failed for algorithm {algo}: {res.get('error')}"
        assert res["status"] == "success"
        assert res["problem_type"] == "classification"
        metrics = res["metrics"]
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "confusion_matrix" in metrics
        assert isinstance(metrics["confusion_matrix"], list)


def test_ml_service_regression_algorithms():
    """Verify MLService trains and evaluates all supported regression algorithms."""
    from app.services.ml_service import ml_service

    csv_data = (
        "Area,Bedrooms,Age,Price\n"
        "1000,2,10,250000\n"
        "1500,3,5,380000\n"
        "800,1,15,180000\n"
        "2000,4,2,500000\n"
        "1200,2,8,300000\n"
        "1800,3,3,450000\n"
        "950,2,12,220000\n"
        "2200,4,1,550000\n"
        "1100,2,7,280000\n"
        "1600,3,4,410000\n"
    )
    file_bytes = csv_data.encode("utf-8")

    algos = ["linear_regression", "decision_tree_regressor", "random_forest_regressor"]
    for algo in algos:
        res = ml_service.train_and_evaluate(
            file_bytes=file_bytes,
            filename="housing.csv",
            target_col="Price",
            algorithm=algo,
            problem_type="regression"
        )
        assert "error" not in res, f"Failed for algorithm {algo}: {res.get('error')}"
        assert res["status"] == "success"
        assert res["problem_type"] == "regression"
        metrics = res["metrics"]
        assert "mae" in metrics
        assert "mse" in metrics
        assert "rmse" in metrics
        assert "r2_score" in metrics


def test_ml_service_auto_recommendation():
    """Verify MLService automatically recommends algorithm based on task and dataset."""
    import pandas as pd
    from app.services.ml_service import ml_service

    # Classification dataset
    df_class = pd.DataFrame({
        "Feature1": [1, 2, 3, 4, 5, 6],
        "City": ["A", "B", "A", "B", "A", "B"],
        "Target": ["Yes", "No", "Yes", "No", "Yes", "No"]
    })
    rec_class = ml_service.recommend_model(df_class, target_col="Target")
    assert rec_class["status"] == "success"
    assert rec_class["problem_type"] == "classification"
    assert "recommended_algorithm" in rec_class
    assert "rationale" in rec_class

    # Regression dataset
    df_reg = pd.DataFrame({
        "Size": [10, 20, 30, 40, 50, 60],
        "Weight": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
        "Score": [10.2, 20.4, 30.1, 40.8, 50.2, 60.9]
    })
    rec_reg = ml_service.recommend_model(df_reg, target_col="Score")
    assert rec_reg["status"] == "success"
    assert rec_reg["problem_type"] == "regression"


def test_ml_service_invalid_target():
    """Verify MLService handles invalid or missing target column gracefully."""
    from app.services.ml_service import ml_service

    csv_data = "A,B\n1,2\n3,4\n5,6\n7,8\n9,10\n"
    res = ml_service.train_and_evaluate(
        file_bytes=csv_data.encode("utf-8"),
        filename="test.csv",
        target_col="NonExistentCol"
    )
    assert "error" in res
    assert "Target column 'NonExistentCol' not found" in res["error"]


def test_ml_service_unsupported_algorithm():
    """Verify MLService rejects unsupported algorithms not in allowlist."""
    from app.services.ml_service import ml_service

    csv_data = "A,B,Target\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n9,10,0\n"
    res = ml_service.train_and_evaluate(
        file_bytes=csv_data.encode("utf-8"),
        filename="test.csv",
        target_col="Target",
        algorithm="unsupported_xgboost_exec"
    )
    assert "error" in res
    assert "Unsupported classification algorithm" in res["error"]


def test_ml_service_insufficient_or_single_class_data():
    """Verify MLService detects single class target or insufficient data rows."""
    from app.services.ml_service import ml_service

    # Single class target
    single_class_csv = "Feature,Target\n10,1\n20,1\n30,1\n40,1\n50,1\n"
    res = ml_service.train_and_evaluate(
        file_bytes=single_class_csv.encode("utf-8"),
        filename="single.csv",
        target_col="Target",
        problem_type="classification"
    )
    assert "error" in res
    assert "at least 2 distinct classes" in res["error"]


def test_ml_service_secret_protection():
    """Verify MLService output does not expose API keys or passwords."""
    from app.services.ml_service import ml_service

    assert ml_service.contains_secret("AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5") is True
    assert ml_service.contains_secret("GOOGLE_API_KEY=12345") is True

    csv_data = "A,B,Target\n1,2,0\n3,4,1\n5,6,0\n7,8,1\n9,10,0\n"
    res = ml_service.train_and_evaluate(
        file_bytes=csv_data.encode("utf-8"),
        filename="clean.csv",
        target_col="Target"
    )
    assert "AIzaSy" not in res["summary_markdown"]
    assert "GOOGLE_API_KEY" not in res["summary_markdown"]


def test_ml_no_arbitrary_code_execution():
    """Verify MLService does not execute arbitrary code or string evaluations."""
    from app.services.ml_service import ml_service
    import inspect

    source = inspect.getsource(ml_service.__class__)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "__import__" not in source


def test_jarvis_machine_learning_intent():
    """Verify JarvisOrchestrator detects machine_learning intent for ML queries."""
    from app.services.jarvis_orchestrator import jarvis_orchestrator

    intent1 = jarvis_orchestrator.classify_intent("Build a classification model for this dataset.")
    assert intent1["primary_intent"] == "machine_learning"
    assert intent1["is_ml_query"] is True

    intent2 = jarvis_orchestrator.classify_intent("Predict whether a customer will churn.")
    assert intent2["primary_intent"] == "machine_learning"

    intent3 = jarvis_orchestrator.classify_intent("Which algorithm should I use?")
    assert intent3["primary_intent"] == "machine_learning"


def test_api_train_ml_model_endpoint():
    """Verify POST /api/train-ml-model endpoint trains model and injects summary into session."""
    csv_data = "Age,Score,Class\n20,80,A\n30,90,B\n40,85,A\n50,95,B\n25,82,A\n35,92,B\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))

    response = client.post(
        "/api/train-ml-model",
        files={"file": ("dataset.csv", file_bytes, "text/csv")},
        data={
            "target_col": "Class",
            "algorithm": "random_forest",
            "problem_type": "classification",
            "session_id": "ml_test_session"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["session_id"] == "ml_test_session"
    assert data["result"]["algorithm"] == "random_forest"
    assert "accuracy" in data["result"]["metrics"]


def test_api_ml_recommendation_endpoint():
    """Verify POST /api/ml-recommendation endpoint returns algorithm recommendations."""
    csv_data = "Feature1,Feature2,Target\n1,10,0\n2,20,1\n3,30,0\n4,40,1\n5,50,0\n6,60,1\n"
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))

    response = client.post(
        "/api/ml-recommendation",
        files={"file": ("recommend.csv", file_bytes, "text/csv")},
        data={"target_col": "Target"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["target_column"] == "Target"
    assert "recommended_algorithm" in data
def test_analytics_service_basic_analysis():
    import pandas as pd
    from app.services.analytics_service import analytics_service

    df = pd.DataFrame({
        "Age": [20, 25, 30, 35, 40],
        "Salary": [20000, 30000, 40000, 50000, 60000],
        "Department": ["IT", "HR", "IT", "Sales", "HR"]
    })

    result = analytics_service.analyze_dataframe(df)

    assert "error" not in result
    assert result["dataset_shape"]["rows"] == 5
    assert result["dataset_shape"]["columns"] == 3
    assert "missing_values" in result
    assert "duplicate_rows" in result

def test_analytics_correlation_analysis():
    import pandas as pd
    from app.services.analytics_service import analytics_service

    df = pd.DataFrame({
        "Age": [20, 25, 30, 35, 40],
        "Salary": [20000, 30000, 40000, 50000, 60000]
    })

    result = analytics_service.analyze_correlations(df)

    assert result["available"] is True
    assert "matrix" in result
    assert "Age" in result["matrix"]
    assert "Salary" in result["matrix"]["Age"]


# =========================================================================
# PHASE 11: PERSONAL JARVIS SECURITY & SPEAKER AUTHORIZATION TESTS
# =========================================================================

def test_speaker_enrollment_and_status_endpoints():
    """Verify owner speaker enrollment, status check, and profile clearance."""
    from app.services.speaker_verification_service import speaker_verification_service

    # Clear profile before starting
    speaker_verification_service.clear_speaker_profile()
    status_res = client.get("/api/speaker/status")
    assert status_res.status_code == 200
    assert status_res.json()["enrolled"] is False

    # Enroll owner speaker with sample base64 WAV
    sample_b64 = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
    enroll_res = client.post("/api/speaker/enroll", json={"audio_samples": [sample_b64]})
    assert enroll_res.status_code == 200
    assert enroll_res.json()["status"] == "success"
    assert enroll_res.json()["enrolled"] is True

    # Re-check status
    status_res2 = client.get("/api/speaker/status")
    assert status_res2.status_code == 200
    assert status_res2.json()["enrolled"] is True

    # Clean up profile
    clear_res = client.delete("/api/speaker/enroll")
    assert clear_res.status_code == 200
    assert clear_res.json()["enrolled"] is False


def test_unauthorized_speaker_cannot_execute_computer_control():
    """Verify unauthorized speaker is blocked from executing computer control desktop actions."""
    # 1. Chat intent check with unauthorized status
    res = client.post(
        "/api/chat",
        json={
            "message": "open notepad",
            "speaker_auth": "UNAUTHORIZED_SPEAKER"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "Access Restricted" in data["response"]
    assert data["action_required"] is None
    assert data["speaker_status"] == "UNAUTHORIZED_SPEAKER"

    # 2. Direct execute endpoint check with unauthorized status
    exec_res = client.post(
        "/api/execute-action",
        json={
            "action_type": "open_app",
            "target": "notepad",
            "confirmed": True,
            "speaker_auth": "UNAUTHORIZED_SPEAKER"
        }
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "blocked"
    assert "restricted to the verified owner" in exec_data["message"]


def test_verification_unavailable_cannot_execute_computer_control():
    """Verify computer control fails safe when speaker verification is unavailable."""
    from app.services.speaker_verification_service import speaker_verification_service
    speaker_verification_service.clear_speaker_profile()

    res = client.post(
        "/api/chat",
        json={
            "message": "open https://google.com"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "Access Restricted" in data["response"]
    assert data["action_required"] is None
    assert data["speaker_status"] == "VERIFICATION_UNAVAILABLE"


def test_authorized_speaker_can_reach_permitted_computer_control():
    """Verify authorized owner speaker reaches confirmation for permitted desktop actions."""
    res = client.post(
        "/api/chat",
        json={
            "message": "Severus, open notepad",
            "speaker_auth": "AUTHORIZED_OWNER"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["speaker_status"] == "AUTHORIZED_OWNER"
    assert data["action_required"] is not None
    assert data["action_required"]["action_type"] == "open_app"
    assert data["action_required"]["target"] == "notepad"


def test_sensitive_action_requires_confirmation():
    """Verify sensitive desktop actions require explicit confirmation even for verified owner."""
    exec_res = client.post(
        "/api/execute-action",
        json={
            "action_type": "open_app",
            "target": "notepad",
            "confirmed": False,
            "speaker_auth": "AUTHORIZED_OWNER"
        }
    )
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["status"] == "confirmation_required"


def test_unauthorized_user_cannot_retrieve_private_owner_memory():
    """Verify unauthorized user cannot query or retrieve private owner memories."""
    res = client.post(
        "/api/chat",
        json={
            "message": "What do you know about Ajay?",
            "speaker_auth": "UNAUTHORIZED_SPEAKER"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "Privacy Restriction" in data["response"]
    assert "verified owner" in data["response"]


@patch("app.routes.chat.ai_service.get_response", new_callable=AsyncMock)
def test_authorized_owner_can_retrieve_personal_memory(mock_get_response):
    """Verify authorized owner can ask about their personal memory."""
    mock_get_response.return_value = "You prefer Python and your project is Severus."

    res = client.post(
        "/api/chat",
        json={
            "message": "What do you remember about me?",
            "speaker_auth": "AUTHORIZED_OWNER"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["speaker_status"] == "AUTHORIZED_OWNER"
    assert "Severus" in data["response"]


def test_secret_filtering_prevents_saving_credentials():
    """Verify secrets and API keys are blocked from memory storage."""
    from app.services.memory_service import memory_service

    assert memory_service.contains_secret("sk-1234567890abcdef1234567890") is True
    assert memory_service.contains_secret("AIzaSy1234567890abcdef1234567890abcdef") is True
    assert memory_service.contains_secret("bearer token_abc123") is True

    save_result = memory_service.save_memory("test_secret", "sk-1234567890abcdef1234567890")
    assert save_result is False