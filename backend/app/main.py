import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.app.config import settings
from backend.app.database.falkordb_client import init_graph
from backend.app.memory.memory_manager import MemoryManager
from backend.app.routers import health, chat, workout, nutrition, recovery, profile, memory, home

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lifesync_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing LifeSync AI backend...")
    try:
        MemoryManager.initialize()
        logger.info("FalkorDB persistent cross-agent memory graph & vector index verified.")
    except Exception as e:
        logger.warning(f"Memory graph init warning: {e}")
    yield
    logger.info("LifeSync AI backend shutting down.")

app = FastAPI(
    title="LifeSync AI Engine",
    description="Production-minded personal wellness platform API supporting Home, Workout, Nutrition, and Recovery workspaces.",
    version="1.0.0",
    lifespan=lifespan
)

# Maximum allowed request payload size: 25 MB
MAX_UPLOAD_SIZE = 25 * 1024 * 1024

class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_UPLOAD_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Payload exceeds maximum allowed limit of 25 MB."}
                    )
            except ValueError:
                pass
        return await call_next(request)

app.add_middleware(ContentSizeLimitMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def safe_exception_handler(request: Request, exc: Exception):
    """Ensure raw tracebacks, database passwords, and secrets are never leaked to clients."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

# Register routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(workout.router)
app.include_router(nutrition.router)
app.include_router(recovery.router)
app.include_router(profile.router)
app.include_router(memory.router)
app.include_router(home.router)

@app.get("/")
def read_root():
    return {
        "project": "LifeSync AI",
        "status": "online",
        "workspaces": ["home", "workout", "nutrition", "recovery"],
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
