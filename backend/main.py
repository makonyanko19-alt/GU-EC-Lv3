from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from carts import router as carts_router
from db import engine
from http_errors import register_error_handlers
from orders import router as orders_router
from products import router as products_router

app = FastAPI(title="GU EC API")
app.include_router(products_router)
app.include_router(carts_router)
app.include_router(orders_router)
register_error_handlers(app)


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health/db")
def database_health_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from None
    return {"status": "ok", "database": "connected"}
