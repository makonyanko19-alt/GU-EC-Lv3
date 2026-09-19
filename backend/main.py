from fastapi import FastAPI

app = FastAPI(title="GU EC API")


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
