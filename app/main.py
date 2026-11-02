from fastapi import FastAPI

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
