"""Structured Logging Setup for ViewStorm."""

import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """Configure standard application logging format."""
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

logger = logging.getLogger("viewstorm")
