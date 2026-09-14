# SEVERUS — Data Science AI Assistant & Personal JARVIS Workspace

> **Disclaimer**: Severus is a Data Science & Personal AI Assistant application built using OpenAI API, LangChain, FastAPI, and local SciPy acoustic speaker authorization.

---

## 1. Project Overview

**SEVERUS** is a ChatGPT-style personal AI assistant with JARVIS-style capabilities designed for Data Science learners, analysts, and developers. Severus acts as an intelligent pair programmer, tutor, desktop computer controller, machine learning builder, and dataset analyst.

### Key Capabilities
- 🛠️ **Code Correction & Debugging**: Identifies syntax, logical, and API usage errors in Python/Pandas/SQL code.
- 🎙️ **Voice Input & Voice Output**: Integrated Web Speech API speech-to-text recognition and text-to-speech auto read-aloud.
- 🔐 **Owner Speaker Verification & Identity Authorization**: Local acoustic speaker verification (`speaker_verification_service.py`) enforcing backend owner security decisions.
- 💻 **Safe Desktop Computer Control**: Safe application launcher, website opener, and file explorer with two-step confirmation and strict allowlists.
- 🔒 **Private Owner Memory Protection**: SQLite persistent memory service filtering secrets, API keys, passwords, and restricting owner private memories to verified speakers.
- 🤖 **Machine Learning Workspace**: Automated scikit-learn model training (Random Forest, Logistic Regression, Decision Tree, KNN) with metrics evaluation.
- 📊 **Advanced Analytics & Visualization**: Automatic EDA, dataset profiling, correlation heatmaps, histograms, scatter plots, and box plots.
- 👁️ **Vision & Multimodal Image Understanding**: PNG, JPG, and WEBP image analysis.
- 🌐 **Real-Time Web Search**: Free, zero-config web search retrieval via DuckDuckGo & optional Tavily integration.

---

## 2. Security Architecture & Authorization Policy

```
                    SEVERUS
                       │
                 Voice Command
                       │
             Speaker Verification
                       │
             ┌─────────┴─────────┐
             │                   │
       OWNER VERIFIED       NOT VERIFIED
             │                   │
             ▼                   ▼
      FULL PERMITTED          CHAT ONLY
       CAPABILITIES             MODE
             │
             ├─ Web Search
             ├─ Computer Control (Confirmed)
             ├─ Desktop Apps & Files
             ├─ Data Science Workspace
             ├─ Machine Learning
             ├─ Analytics & Charts
             ├─ Vision & Multimodal
             └─ Private Owner Memory
```

### Authorization Modes
1. **AUTHORIZED_OWNER**:
   - Full access to permitted computer control capabilities (subject to mandatory two-step confirmation).
   - Access to personal owner memory and preferences.
2. **UNAUTHORIZED_SPEAKER / VERIFICATION_UNAVAILABLE**:
   - Normal conversational AI and general Data Science Q&A allowed.
   - **Computer Control Disabled**: Cannot launch applications, open URLs, or access file paths.
   - **Private Memory Protection**: Cannot retrieve private owner information or stored personal memories.
   - Never fails open.

---

## 3. Technology Stack

- **Backend Framework**: Python 3.11+ / FastAPI
- **AI Orchestration**: LangChain (`langchain`, `langchain-openai`)
- **LLM Provider**: OpenAI API (`gpt-4o-mini` / `gpt-4o`)
- **Speaker Verification**: Local SciPy & NumPy FFT spectral cepstral embedding matching (cosine similarity)
- **Data Science & ML**: Pandas, NumPy, Scikit-Learn, Matplotlib, Seaborn
- **Frontend**: Vanilla HTML5, CSS3 (Modern Dark Theme), JavaScript (ES6+)
- **Markdown & Code Syntax**: Marked.js + Highlight.js (Atom One Dark theme)
- **Testing**: Pytest & FastAPI TestClient

---

## 4. Setup & Running Locally

### Step 1: Virtual Environment Setup
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Create or edit `.env` in the project root:
```env
OPENAI_API_KEY=sk-your_real_openai_api_key_here
MODEL_NAME=gpt-4o-mini
DEBUG=True
PORT=8001
HOST=127.0.0.1
```

### Step 4: Run Severus Server
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```
Open your web browser at **[http://127.0.0.1:8001](http://127.0.0.1:8001)**.

---

## 5. Automated Testing

Run the full pytest suite (all 60 unit tests):

```bash
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 6. Speaker Verification Limitations & Security Notice

- **Local Feature Extraction**: Speaker verification extracts 32-dimensional acoustic spectral feature embeddings locally. No voice recordings are uploaded to third-party services.
- **Data Persistence**: Only normalized float embeddings are stored in `data/owner_speaker_profile.json`. Raw audio is never saved.
- **Security Limitations**: Local acoustic speaker verification provides an initial authorization layer but is not foolproof against high-quality voice imitation, audio replaying, or synthetic voice cloning. Dangerous desktop commands are strictly prohibited by allowlist policies and always require secondary explicit user confirmation.
