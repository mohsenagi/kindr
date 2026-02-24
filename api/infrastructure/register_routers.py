"""Router registry for automatic route inclusion."""

import importlib
import inspect
from pathlib import Path

from fastapi import APIRouter, FastAPI


def register_routers(app: FastAPI) -> None:
    """Automatically discover and include APIRouter instances from api.endpoints."""
    endpoints_dir = Path(__file__).parent.parent / "endpoints"

    for file_path in endpoints_dir.glob("*.py"):
        if file_path.name.startswith("__"):
            continue

        module_name = f"api.endpoints.{file_path.stem}"
        module = importlib.import_module(module_name)

        for _, obj in inspect.getmembers(module):
            if isinstance(obj, APIRouter):
                app.include_router(obj)
