# SEVERUS — Data Science Generative AI Assistant & Futuristic JARVIS Command Center

> **SEVERUS** is an production-ready, multi-user Data Science Generative AI Assistant and futuristic JARVIS-style Command Center powered by Google Gemini, LangChain, FastAPI, SQLite, and local acoustic speaker authorization.

---

## 🚀 1. Overview & Key Capabilities

SEVERUS transforms traditional AI assistant interaction by pairing a **futuristic JARVIS SVG AI Core HUD** with a **ChatGPT-quality conversational stream** on the same screen. It acts as an autonomous pair programmer, Data Science workspace, machine learning builder, document RAG intelligence engine, and secure desktop task manager.

### 🌟 Features Summary (Phases 1 - 18)
- 🎙️ **Voice First & Continuous Hands-Free Voice Mode**: Wake phrase recognition ("Hey Severus" / "Severus"), command prefix stripping, continuous speech recognition loops, and voice interruption (`Stop Voice`).
- 🤖 **10-Agent Modular System**: Specialized sub-agents (General, Data Science, ML, Analytics, Vision, Web Search, Document RAG, Memory, Computer Control, Voice) with timeout safeguards and retry limits.
- 📚 **RAG & Document Intelligence**: Upload and ask questions about PDF, DOCX, TXT, CSV, and XLSX documents with chunking, TF-IDF similarity retrieval, and grounded source citations.
- 🔐 **Multi-User JWT Authentication & Security Isolation**: Secure PBKDF2 password hashing, JWT access token authentication, user/admin roles, and user-isolated chat history, memories, and documents.
- 🛡️ **Owner Speaker Verification**: Local acoustic spectral embedding verification enforcing owner-only computer control and private memory protection.
- 📊 **Advanced Analytics & Visualization**: Automatic EDA, dataset profiling, correlation matrices, missing value checks, and Matplotlib chart generation (Histogram, Bar, Line, Scatter, Box, Heatmap).
- 🧠 **Machine Learning Workspace**: Automated scikit-learn training for classification and regression models (Random Forest, Logistic Regression, Decision Tree, KNN, Linear Regression) with auto-recommendation algorithms.
- 👁️ **Vision & Multimodal Understanding**: PNG, JPG, and WEBP image analysis.
- 🌐 **Real-Time Web Search**: DuckDuckGo integration for live web context.
- 💻 **Safe Computer Control**: Confirmation-gated launcher for desktop applications and web URLs with safety allowlist enforcement.
- 🐳 **Docker & Cloud Readiness**: Production Dockerfile, docker-compose.yml, liveness `/health` & readiness `/readiness` probes, rate limiting, correlation ID tracking, and security headers.

---

## 🔒 2. Security Architecture & Authorization Model

```
                         SEVERUS AI CORE
                                │
                          User Input
                                │
                       JWT & Speaker Gate
                                │
             ┌──────────────────┴──────────────────┐
             │                                     │
       AUTHORIZED OWNER                      UNAUTHORIZED / GUEST
             │                                     │
             ▼                                     ▼
    FULL CAPABILITIES                      CHAT ONLY MODE
    + Computer Control (Confirmed)         + Standard Q&A
    + Private Owner Memory                 + Public Data Science
    + User Isolated Documents              + User Isolated Documents
```

### Security Directives
1. **Never Fails Open**: If speaker verification is unavailable or un-enrolled, computer control and private owner memory queries are strictly blocked.
2. **Desktop Action Confirmation**: Desktop launcher commands ALWAYS present an explicit visual confirmation card before execution.
3. **Secret Guarding**: API keys, auth tokens, passwords, and private credentials are automatically filtered out before saving to conversation memory or logs.

---

## 🛠️ 3. Technology Stack

- **Backend**: Python 3.11+ / FastAPI
- **LLM Engine**: Google Gemini via `ChatGoogleGenerativeAI` (`langchain_google_genai`)
- **Orchestration**: LangChain & Modular Multi-Agent System
- **Authentication**: PyJWT & PBKDF2 SHA-256 password hashing
- **RAG Engine**: `pypdf`, `python-docx`, `pandas`, `openpyxl`
- **Database**: SQLite3 (`app/database/severus.db`)
- **Frontend**: Vanilla HTML5, CSS3 Cybernetic Animations, Web Speech API
- **Testing**: Pytest & FastAPI TestClient

---

## 📦 4. Setup & Running Locally

### Step 1: Virtual Environment
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### Step 2: Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Environment Configuration (`.env`)
Create or edit `.env` in the root folder:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
MODEL_NAME=gemini-3.7-flash
PORT=8001
HOST=0.0.0.0
JWT_SECRET_KEY=severus_super_secret_jwt_key_2026_change_in_prod
```

### Step 4: Run Application
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```
Open **[http://127.0.0.1:8001](http://127.0.0.1:8001)** in Google Chrome, Microsoft Edge, or Safari.

---

## 🐳 5. Docker Deployment

```bash
# Build and run containerized application
docker-compose up --build -d

# Check health probe
curl http://localhost:8001/health
curl http://localhost:8001/readiness
```

---

## 🧪 6. Automated Testing

Run the full pytest suite (all 87 unit, integration, and security tests):

```bash
.\.venv\Scripts\python.exe -m pytest -v
```

Run JavaScript syntax verification:
```bash
node --check frontend/script.js
```

---

## 📄 7. License & Credits

Created and developed by **Ajay** as a personal AI assistant application powered by Google Gemini and FastAPI.
