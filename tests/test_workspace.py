from __future__ import annotations

import pytest

from rlm_core.workspace import (
    DuplicateWorkspaceError,
    InMemoryWorkspaceRegistry,
    WorkspaceResolutionError,
    WorkspaceSource,
)


def test_resolve_direct_path_without_registry_entry(tmp_path):
    registry = InMemoryWorkspaceRegistry()

    workspace = registry.resolve(root_path=tmp_path)

    assert workspace.root_path == tmp_path.resolve()
    assert workspace.source is WorkspaceSource.DIRECT_PATH
    assert workspace.workspace_id is None


def test_resolve_registered_workspace_by_id(tmp_path):
    registry = InMemoryWorkspaceRegistry()
    expected = registry.register(
        "demo",
        tmp_path,
        display_name="Demo Repo",
        adapter_hint="bsl",
        metadata={"owner": "tests"},
    )

    resolved = registry.resolve(workspace_id="demo")

    assert resolved == expected
    assert resolved.source is WorkspaceSource.REGISTRY
    assert resolved.adapter_hint == "bsl"


def test_register_duplicate_workspace_id_fails(tmp_path):
    registry = InMemoryWorkspaceRegistry()
    registry.register("demo", tmp_path)

    with pytest.raises(DuplicateWorkspaceError):
        registry.register("demo", tmp_path / "other")


def test_resolve_requires_exactly_one_input(tmp_path):
    registry = InMemoryWorkspaceRegistry()
    registry.register("demo", tmp_path)

    with pytest.raises(WorkspaceResolutionError):
        registry.resolve()

    with pytest.raises(WorkspaceResolutionError):
        registry.resolve(workspace_id="demo", root_path=tmp_path)
