"""BSL adapter package."""

from .adapter import BslRepositoryAdapter
from .contracts import (
    BSL_INDEXED_FEATURES,
    BSL_SCHEMA_EXTENSIONS,
    BslConfigRole,
    BslIndexedFeature,
    BslRepositoryDetails,
    BslSourceFormat,
)
from .detection import inspect_bsl_workspace
from .index import BslIndexHooks, BslIndexManifest

__all__ = [
    "BSL_INDEXED_FEATURES",
    "BSL_SCHEMA_EXTENSIONS",
    "BslConfigRole",
    "BslIndexHooks",
    "BslIndexManifest",
    "BslIndexedFeature",
    "BslRepositoryAdapter",
    "BslRepositoryDetails",
    "BslSourceFormat",
    "inspect_bsl_workspace",
]
