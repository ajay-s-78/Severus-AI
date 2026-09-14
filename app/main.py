import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes.chat import router as chat_router
from app.routes.auth import router as auth_router
from app.routes.documents import router as documents_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="SEVERUS - Data Science AI Assistant powered by FastAPI, LangChain, and Google Gemini API",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness health check endpoint."""
    return {"status": "ok"}


@app.get("/readiness", tags=["Health"])
async def readiness_check():
    """Readiness probe endpoint checking database connection."""
    try:
        from app.database.database import get_connection
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "unready", "database": str(e)}


# Mount static frontend assets if directory exists
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/", tags=["Frontend"])
    async def serve_index():
        """Serve frontend SPA index.html."""
        index_file = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found."}
