"""ViewStorm Dedicated Control-Plane (FastAPI Orchestration & Web Management) Entrypoint."""

import os
from app.core.config import settings
from app.main import create_application

# Force service mode to control_plane
settings.service_mode = "control_plane"
os.environ["VIEWSTORM_SERVICE_MODE"] = "control_plane"

app = create_application(service_mode="control_plane")
