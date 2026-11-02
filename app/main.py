
from fastapi import FastAPI
from app.db import check_database
from app.api.memory import router as memory_router
from app.api.knowledge import router as knowledge_router

app = FastAPI(
    title="Neuralix Brain",
    description="Independent AI Brain API",
    version="1.0.0"
)

# Register API routers
app.include_router(memory_router)
app.include_router(knowledge_router)


@app.get("/")
def home():
    return {
        "name": "Neuralix Brain",
        "status": "online",
        "mode": "cloud"
    }


@app.get("/health")
def health():
    return {
        "healthy": True
    }


@app.get("/db-health")
def database_health():
    connected = check_database()

    return {
        "database": "connected" if connected else "disconnected",
        "healthy": connected
    }
