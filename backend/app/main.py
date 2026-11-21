"""ViewStorm FastAPI Application Entrypoint."""

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.health import get_health
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.errors import ViewStormException, viewstorm_exception_handler
from app.core.logging import logger, setup_logging
from app.core.metrics import (
    CONTENT_TYPE_LATEST,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    get_metrics_payload,
)
from app.database.redis import redis_pool
from app.database.session import AsyncSessionLocal, engine
from app.services.auth_service import auth_service
from app.services.lifecycle_reconciliation_service import (
    lifecycle_reconciliation_service,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and graceful shutdown lifecycle management."""
    setup_logging(level=settings.log_level)
    logger.info(
        "Initializing %s v%s in '%s' environment",
        settings.project_name,
        settings.version,
        settings.environment,
    )

    # Startup reconciliation and admin bootstrap
    try:
        async with AsyncSessionLocal() as session:
            await auth_service.bootstrap_admin(session)
            await lifecycle_reconciliation_service.reconcile_interrupted_runs(session)
    except Exception as e:
        logger.warning("Startup reconciliation or bootstrap deferred: %s", e)

    yield

    logger.info("Closing database engine and Redis connection pool...")
    await engine.dispose()
    await redis_pool.disconnect()
    logger.info("Shutdown complete for %s", settings.project_name)


def create_application() -> FastAPI:
    """Factory function to build and configure the FastAPI app."""
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description=(
            "Distributed virtual-viewer simulation and performance engineering platform. "
            "Simulates high-throughput synthetic playback events for authorized testing environments."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ViewStormException, viewstorm_exception_handler)

    @app.middleware("http")
    async def observability_and_metrics_middleware(request: Request, call_next):
        """Track request timing, Prometheus metrics, and distributed tracing headers."""
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id

        # Normalize path for Prometheus endpoint label to avoid cardinality explosion
        path = request.url.path
        if "/runs/" in path:
            path = "/api/v1/runs/:id"
        elif "/worker-nodes/" in path:
            path = "/api/v1/worker-nodes/:id"
        elif "/users/" in path:
            path = "/api/v1/auth/users/:id"

        try:
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                endpoint=path,
            ).observe(duration)
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=path,
                status_code=str(response.status_code),
            ).inc()
        except Exception:
            pass

        return response

    # Root health endpoint
    app.add_api_route("/health", get_health, tags=["Health"])

    # Prometheus metrics exposition
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        """Prometheus metrics endpoint for cluster scraping."""
        return Response(content=get_metrics_payload(), media_type=CONTENT_TYPE_LATEST)

    # API v1 routes
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_application()
