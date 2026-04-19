"""BSL adapter package."""

from .adapter import BslRepositoryAdapter
from .advanced import BslAdvancedExtension, BslAdvancedSnapshot
from .contracts import (
    BSL_ADVANCED_FEATURES,
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
    "BSL_ADVANCED_FEATURES",
    "BSL_INDEXED_FEATURES",
    "BSL_SCHEMA_EXTENSIONS",
    "BslAdvancedExtension",
    "BslAdvancedSnapshot",
    "BslConfigRole",
    "BslIndexHooks",
    "BslIndexManifest",
    "BslIndexedFeature",
    "BslRepositoryAdapter",
    "BslRepositoryDetails",
    "BslSourceFormat",
    "inspect_bsl_workspace",
]
