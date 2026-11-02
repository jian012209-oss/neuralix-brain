
from fastapi import FastAPI
from app.db import check_database

app = FastAPI(
    title="Neuralix Brain",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "name": "Neuralix Brain",
        "status": "online",
        "mode": "cloud"
    }


@app.get("/health")
def health():
    return {"healthy": True}


@app.get("/db-health")
def database_health():
    connected = check_database()

    return {
        "database": "connected" if connected else "disconnected",
        "healthy": connected
    }
