from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .settings import settings

# Schema is managed by Alembic: run `alembic upgrade head` before starting.
app = FastAPI(title="Spending API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def home():
    return {"message": "Spending API is running"}
