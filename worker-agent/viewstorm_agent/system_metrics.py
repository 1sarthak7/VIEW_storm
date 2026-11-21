"""System and Environment Metrics Collector for Worker Agent."""

import platform
from typing import Dict, Any
import locust
import psutil


def collect_system_info() -> Dict[str, Any]:
    """Collect hardware and platform environment specs for registration."""
    mem = psutil.virtual_memory()
    return {
        "hostname": platform.node(),
        "platform": f"{platform.system()} {platform.release()}",
        "cpu_cores": psutil.cpu_count(logical=True) or 1,
        "total_memory_bytes": mem.total,
        "available_memory_bytes": mem.available,
        "locust_version": getattr(locust, "__version__", "2.47.0"),
        "software_version": "1.0.0",
        "build_identifier": "release",
    }


def collect_utilization() -> Dict[str, Any]:
    """Collect real-time CPU and RAM utilization for heartbeats."""
    mem = psutil.virtual_memory()
    return {
        "cpu_utilization": psutil.cpu_percent(interval=None),
        "ram_utilization": mem.percent,
        "available_memory_bytes": mem.available,
    }
