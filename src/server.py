"""Unified entry point: uvicorn src.server:create_app --factory.

Run `python -m src.server migrate` explicitly before the first start.
"""

import sys
from pathlib import Path

from fastapi import FastAPI

BACKEND = Path(__file__).resolve().parent / "backend"
BACKEND_SOURCE = str(BACKEND / "src")
if BACKEND_SOURCE not in sys.path:
    sys.path.insert(0, BACKEND_SOURCE)


def create_app() -> FastAPI:
    """Load the team application with exactly one news router and DB configuration."""
    from dait.main import create_app as build_app

    return build_app()


def migrate() -> None:
    """Apply versioned migrations to DATABASE_URL; never reset existing data."""
    from alembic import command
    from alembic.config import Config

    from dait.core.config import get_settings

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
    command.upgrade(config, "head")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["migrate"])
    parser.parse_args()
    migrate()
