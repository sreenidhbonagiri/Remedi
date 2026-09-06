from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1 import api_router
from app.db.base import Base
from app.db.migrate import apply_sqlite_additions
from app.db.seed import seed_database
from app.db.session import SessionLocal, engine

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_application: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_sqlite_additions(engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Patient Assistance Copilot",
        description=(
            "Affordable Medication Sourcing Copilot — 2026 FPL screening, AB-rated "
            "generic savings, LangGraph triage, and manufacturer PAP PDF export."
        ),
        version="6.0.0",
        lifespan=lifespan,
    )
    application.include_router(api_router, prefix="/api/v1")
    application.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

    @application.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("index.html", {"request": request})

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
