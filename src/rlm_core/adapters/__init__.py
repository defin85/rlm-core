"""Adapter contracts and registry for language-specific integrations."""

from .contracts import HelperContext, RepositoryAdapter, RepositoryDescriptor, StrategyContext
from .registry import AdapterRegistry, AdapterSelectionError

__all__ = [
    "AdapterRegistry",
    "AdapterSelectionError",
    "HelperContext",
    "RepositoryAdapter",
    "RepositoryDescriptor",
    "StrategyContext",
]
