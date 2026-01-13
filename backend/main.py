from fastapi import FastAPI
from backend.api import health, risk

app = FastAPI(title="Aadhaar CIIM Risk Engine")

app.include_router(health.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
