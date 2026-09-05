from fastapi import APIRouter

from app.api.v1 import copilot

api_router = APIRouter()
api_router.include_router(copilot.router, tags=["copilot"])
