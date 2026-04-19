"""Go adapter package."""

from .adapter import GoRepositoryAdapter
from .contracts import GO_LIVE_FEATURES, GoRepositoryDetails
from .detection import inspect_go_workspace

__all__ = [
    "GO_LIVE_FEATURES",
    "GoRepositoryAdapter",
    "GoRepositoryDetails",
    "inspect_go_workspace",
]
