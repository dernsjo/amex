import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import router
from .settings import settings

logger = logging.getLogger(__name__)

# Schema is managed by Alembic: run `alembic upgrade head` before starting.
app = FastAPI(title="Spending API")


# Starlette answers an unhandled exception outside every middleware, so that 500
# carries no CORS headers and the browser reports a bare "Network Error". Catching
# it here, inside CORSMiddleware (added below, so it wraps this), lets the client
# see a real 500. The traceback still goes to the server log; the client gets none.
@app.middleware("http")
async def unhandled_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Please try again."})


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
