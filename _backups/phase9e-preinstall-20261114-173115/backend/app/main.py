from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .config import settings
from .routes_auth import limiter, router as auth_router
from .routes_data import router as data_router
from .routes_scan import router as scan_router
from .routes_upload import router as upload_router
from .routes_reports import router as reports_router
from .routes_export import router as export_router
from .routes_analytics import router as analytics_router
from .routes_models import router as models_router
from .routes_notifications import router as notifications_router

app = FastAPI(title="Sentinel API", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(data_router)
app.include_router(scan_router)
app.include_router(upload_router)
app.include_router(reports_router)
app.include_router(export_router)
app.include_router(analytics_router)
app.include_router(models_router)
app.include_router(notifications_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
