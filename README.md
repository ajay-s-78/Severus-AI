# SEVERUS — Data Science AI Assistant

> **Disclaimer**: Severus is a Data Science-focused Generative AI application built using the OpenAI API, LangChain, and FastAPI. The underlying LLM is provided through the OpenAI API and is not trained from scratch by this project.

---

## 1. Project Overview

**SEVERUS** is an AI assistant designed specifically for Data Science students, learners, analysts, and developers. Severus acts as an intelligent pair programmer and tutor, helping users learn Data Science concepts, debug Python and SQL errors, correct faulty code, explain complex algorithms, and generate production-ready Data Science snippets.

### Key Capabilities
- 🛠️ **Code Correction**: Identifies syntax, logical, and API usage errors in Python/Pandas/SQL code, presenting structured output with Problem, Corrected Code, and Explanation.
- 🔍 **Code Explanation**: Breaks down code step-by-step, detailing function calls, variables, and potential optimizations.
- 🐛 **Error Debugging**: Analyzes stack traces (e.g. `KeyError`, `ValueError`, `AttributeError`) and provides explanations and fixes.
- ⚡ **Code Generation**: Generates clean, documented Python, Pandas, NumPy, Scikit-Learn, SQL, and Deep Learning snippets.
- 🎓 **Data Science Concept Q&A**: Answers conceptual questions (e.g., overfitting, precision vs recall, CNNs, gradient descent, EDA).

---

## 2. Technology Stack

- **Backend Framework**: Python 3.11+ / FastAPI
- **AI Orchestration**: LangChain (`langchain`, `langchain-openai`)
- **LLM Provider**: OpenAI API (`gpt-4o-mini` / `gpt-3.5-turbo` / `gpt-4o`)
- **Frontend**: Vanilla HTML5, CSS3 (Modern Glassmorphism Dark Theme), JavaScript (ES6+)
- **Markdown & Code Rendering**: Marked.js + Highlight.js (Atom One Dark theme)
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest & FastAPI TestClient

---

## 3. Technology Architecture

```
User (Browser)
  │
  ▼
Severus Frontend (HTML5 / CSS3 / JS)
  │
  ▼  HTTP POST /api/chat
FastAPI Backend (app/routes/chat.py)
  │
  ▼  Session History + System Prompt
LangChain Service (app/services/ai_service.py)
  │
  ▼  API Request
OpenAI API (Generative AI Model)
  │
  ▼  Response
LangChain ──► FastAPI ──► Frontend ──► User
```

---

## 4. Project Structure

```
severus/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI entry point & static file server
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py          # Environment settings configuration
│   ├── routes/
│   │   ├── __init__.py
│   │   └── chat.py            # API routes (/api/chat, /api/clear)
│   ├── services/
│   │   ├── __init__.py
│   │   └── ai_service.py      # LangChain & OpenAI integration service
│   └── prompts/
│       ├── __init__.py
│       └── system_prompt.py   # Severus AI persona & structured directives
├── frontend/
│   ├── index.html             # Main chatbot user interface
│   ├── style.css              # Dark theme Data Science styling
│   └── script.js              # Client chat logic & markdown syntax rendering
├── tests/
│   ├── __init__.py
│   └── test_api.py            # Pytest suite with mocked AI service calls
├── .env                       # Local environment variables (git-ignored)
├── .env.example               # Template environment variables file
├── .gitignore
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker container image spec
├── docker-compose.yml         # Container orchestration manifest
└── README.md                  # Complete documentation
```

---

## 5. Installation & Setup

### Prerequisites
- Python 3.10+ installed
- Git installed
- An active OpenAI API Key

### Step 1: Clone or Navigate to Project Directory
```bash
cd "c:/Users/ELCOT/OneDrive/Desktop/Generative AI"
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure OpenAI API Key
Copy `.env.example` to `.env` and set your key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
OPENAI_API_KEY=sk-your_actual_openai_api_key_here
MODEL_NAME=gpt-4o-mini
DEBUG=True
PORT=8000
HOST=0.0.0.0
```

---

## 6. How to Run Locally

To start Severus locally using Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

Once running, open your web browser at:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 7. How to Run with Docker

### Using Docker Compose (Recommended)
```bash
# Ensure .env contains your OPENAI_API_KEY
docker-compose up --build -d
```
Access the application at `http://localhost:8000`.

To stop the container:
```bash
docker-compose down
```

### Using Standard Docker CLI
```bash
# Build Docker image
docker build -t severus-ai-app .

# Run container passing environment file
docker run -d -p 8000:8000 --env-file .env --name severus-app severus-ai-app
```

---

## 8. API Reference

### 1. Health Check
- **GET** `/health`
- **Response**:
```json
{
  "status": "ok"
}
```

### 2. Send Chat Message
- **POST** `/api/chat`
- **Request Body**:
```json
{
  "message": "Correct this code:\nimport pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head)",
  "session_id": "optional_session_uuid"
}
```
- **Response Body**:
```json
{
  "response": "### Problem\nYou used `df.head` without calling the method...\n\n### Corrected Code\n```python\nimport pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())\n```",
  "session_id": "optional_session_uuid"
}
```

### 3. Clear Session History
- **POST** `/api/clear`
- **Request Body**:
```json
{
  "session_id": "session_uuid"
}
```
- **Response Body**:
```json
{
  "status": "cleared",
  "session_id": "session_uuid"
}
```

---

## 9. Example Test Questions for Severus

1. **Code Correction**:
   ```python
   import pandas as pd
   df = pd.read_csv("data.csv")
   print(df.head)
   ```
2. **Debugging**:
   "I ran `df['Age']` and got `KeyError: 'Age'`. Why did this happen and how do I fix it?"
3. **Code Generation**:
   "Write Python code using Pandas to group sales data by product category and aggregate sum."
4. **Data Science Concept**:
   "What is the difference between precision and recall, and when should I optimize for recall?"
5. **SQL Query**:
   "Write SQL to find the top 5 customers with highest total order amount."

---

## 10. Automated Testing

Run unit tests using pytest:

```bash
pytest tests/ -v
```

The tests mock external OpenAI API calls so test execution completes instantly offline.

---

## 11. Security & Limitations

- **API Key Security**: `OPENAI_API_KEY` is kept strictly on the backend inside `.env` and is never sent to or exposed in the frontend.
- **Code Execution Disclaimer**: Severus does not execute arbitrary Python or SQL code directly on the host machine. Severus will never pretend code was executed unless an isolated execution sandbox is implemented.
- **In-Memory History**: Session conversation history is maintained in memory. Restarting the backend server resets session memory.

---

## 12. Future Enhancements

- 📊 **CSV & Dataset Upload**: Allow users to drag-and-drop CSV files for automated profiling.
- 📈 **Automated Visualization Engine**: Generate dynamic Plotly/Matplotlib visual charts directly in chat.
- 💾 **Persistent Database Memory**: Integrate Redis or PostgreSQL for multi-device chat storage.
