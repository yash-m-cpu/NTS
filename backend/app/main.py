from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import custom_exception_handler, validation_exception_handler

app = FastAPI(
    title="NTS Platform API",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Exception handlers
app.add_exception_handler(Exception, custom_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}

@app.get("/health/ready", tags=["system"])
async def ready_check():
    # In future, add db connectivity check here
    return {"status": "ready"}

app.include_router(api_router, prefix="/api/v1")
