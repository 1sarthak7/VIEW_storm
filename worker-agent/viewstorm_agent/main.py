"""CLI Entrypoint for ViewStorm Distributed Worker Agent."""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from viewstorm_agent.agent import WorkerAgent
from viewstorm_agent.configuration import AgentSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ViewStorm Distributed Worker Agent")
    parser.add_argument("--server-url", default=None, help="FastAPI backend server URL (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--token", default=None, help="Worker authentication token")
    parser.add_argument("--name", default=None, help="Human-readable worker name")
    parser.add_argument("--identifier", default=None, help="Unique worker node identifier")
    parser.add_argument("--capacity", type=int, default=None, help="Max virtual users capacity for this node")
    parser.add_argument("--locustfile", default=None, help="Path to simulator/locustfile.py")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    settings = AgentSettings()
    if args.server_url:
        settings.server_url = args.server_url
    if args.token:
        settings.auth_token = args.token
    if args.name:
        settings.worker_name = args.name
    if args.identifier:
        settings.worker_identifier = args.identifier
    if args.capacity:
        settings.capacity = args.capacity
    if args.locustfile:
        settings.locustfile_path = Path(args.locustfile).resolve()

    agent = WorkerAgent(settings=settings)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _signal_handler() -> None:
        logging.info("Shutdown signal received. Stopping worker agent...")
        agent.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(agent.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
