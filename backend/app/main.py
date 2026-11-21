"""ViewStorm FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.health import get_health
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.errors import ViewStormException, viewstorm_exception_handler
from app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    setup_logging()
    logger.info("Initializing %s v%s in '%s' environment", settings.project_name, settings.version, settings.environment)
    yield
    logger.info("Shutting down %s", settings.project_name)


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

    # Cross-Origin Resource Sharing (CORS) for development dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register custom domain exception handler
    app.add_exception_handler(ViewStormException, viewstorm_exception_handler)

    # Direct /health endpoint as required by specification
    app.add_api_route("/health", get_health, tags=["Health"])

    # Include API version 1 routers
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_application()
