from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import auth
from app.routers import (
    affinity,
    application,
    cluster,
    experiments,
    health,
    inventory,
    metrics,
    research,
)

app = FastAPI(
    title="CrossLayer Dashboard API",
    version="0.1.0",
    description="Research API over Prometheus and Kubernetes with a bounded experiment load controller. Never fabricates metric values.",
)

app.include_router(auth.router, prefix="/api/v1")


@app.middleware("http")
async def require_dashboard_session(request, call_next):
    path = request.url.path
    if not path.startswith("/api/v1/") or path in {
        "/api/v1/auth/session",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
    }:
        return await call_next(request)

    if not auth.auth_is_configured():
        return JSONResponse(
            status_code=503,
            content={"detail": "Dashboard authentication is not configured"},
        )
    if not auth.request_is_authenticated(request):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
        )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(cluster.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(application.router, prefix="/api/v1")
app.include_router(affinity.router, prefix="/api/v1")
app.include_router(experiments.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": "crosslayer-dashboard-api", "docs": "/docs"}
