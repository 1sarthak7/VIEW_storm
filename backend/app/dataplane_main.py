"""ViewStorm Dedicated Data-Plane (Playback Event Ingestion API) Entrypoint."""

import os
from app.core.config import settings
from app.main import create_application

# Force service mode to data_plane
settings.service_mode = "data_plane"
os.environ["VIEWSTORM_SERVICE_MODE"] = "data_plane"

app = create_application(service_mode="data_plane")
