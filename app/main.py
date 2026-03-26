from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers.job_rule import router as job_rule_router
from app.routers.resumes import router as resumes_router
from app.routers.screenings import router as screenings_router
from app.config import BASE_DIR
from app.services.bootstrap import bootstrap_storage


def create_app():
    bootstrap_storage()
    static_dir = BASE_DIR / "app" / "static"

    app = FastAPI(
        title="Java Backend Resume Screener MVP",
        version="0.1.0",
        description="MVP backend for screening Java backend engineer resumes.",
    )
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static_dir / "index.html")

    app.include_router(job_rule_router, prefix="/api/v1")
    app.include_router(resumes_router, prefix="/api/v1")
    app.include_router(screenings_router, prefix="/api/v1")
    return app


app = create_app()
