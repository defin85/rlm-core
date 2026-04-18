"""BSL adapter-owned index hooks and manifest handling."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rlm_core.index.contracts import (
    IndexBuildRequest,
    IndexLifecycleAction,
    IndexOperationResult,
    IndexOperationStatus,
    IndexStatus,
)
from rlm_core.workspace import WorkspaceRef

from .contracts import BSL_INDEXED_FEATURES, BSL_SCHEMA_EXTENSIONS
from .detection import inspect_bsl_workspace


@dataclass(frozen=True, slots=True)
class BslIndexManifest:
    """Persistent adapter-owned description of a built BSL index."""

    builder_version: int
    workspace_root: str
    built_at: str
    updated_at: str
    repo_details: dict[str, object]
    adapter_features: frozenset[str]
    schema_extensions: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "repo_details", dict(self.repo_details))
        object.__setattr__(self, "adapter_features", frozenset(self.adapter_features))
        object.__setattr__(self, "schema_extensions", frozenset(self.schema_extensions))

    def to_payload(self) -> dict[str, object]:
        return {
            "builder_version": self.builder_version,
            "workspace_root": self.workspace_root,
            "built_at": self.built_at,
            "updated_at": self.updated_at,
            "repo_details": dict(self.repo_details),
            "adapter_features": sorted(self.adapter_features),
            "schema_extensions": sorted(self.schema_extensions),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BslIndexManifest":
        return cls(
            builder_version=int(payload["builder_version"]),
            workspace_root=str(payload["workspace_root"]),
            built_at=str(payload["built_at"]),
            updated_at=str(payload["updated_at"]),
            repo_details=dict(payload.get("repo_details", {})),
            adapter_features=frozenset(str(item) for item in payload.get("adapter_features", [])),
            schema_extensions=frozenset(str(item) for item in payload.get("schema_extensions", [])),
        )


class BslIndexHooks:
    """Adapter-owned lifecycle implementation for the BSL index."""

    def __init__(
        self,
        *,
        builder_version: int = 1,
        adapter_features: frozenset[str] = BSL_INDEXED_FEATURES,
        schema_extensions: frozenset[str] = BSL_SCHEMA_EXTENSIONS,
    ) -> None:
        self._builder_version = builder_version
        self._adapter_features = frozenset(adapter_features)
        self._schema_extensions = frozenset(schema_extensions)

    def build_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        manifest = self._write_manifest(request.workspace)
        return IndexOperationResult(
            action=IndexLifecycleAction.BUILD,
            status=IndexOperationStatus.COMPLETED,
            details=self._result_details(request.workspace, manifest, background=request.background),
        )

    def update_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        manifest = self._write_manifest(request.workspace, preserve_built_at=True)
        return IndexOperationResult(
            action=IndexLifecycleAction.UPDATE,
            status=IndexOperationStatus.COMPLETED,
            details=self._result_details(request.workspace, manifest, background=request.background),
        )

    def drop_index(self, workspace: WorkspaceRef) -> IndexOperationResult:
        shutil.rmtree(self._index_dir(workspace), ignore_errors=True)
        return IndexOperationResult(
            action=IndexLifecycleAction.DROP,
            status=IndexOperationStatus.COMPLETED,
            details={"index_dir": str(self._index_dir(workspace))},
        )

    def get_index_status(self, workspace: WorkspaceRef) -> IndexStatus:
        manifest = self._read_manifest(workspace)
        if manifest is None:
            return IndexStatus(
                available=False,
                stale=None,
                details={"index_dir": str(self._index_dir(workspace)), "adapter_id": "bsl"},
            )

        stale = manifest.builder_version != self._builder_version
        return IndexStatus(
            available=True,
            stale=stale,
            details=self._result_details(workspace, manifest, background=False),
        )

    def _write_manifest(self, workspace: WorkspaceRef, *, preserve_built_at: bool = False) -> BslIndexManifest:
        repo_details = inspect_bsl_workspace(workspace.root_path)
        if repo_details is None:
            raise ValueError(f"Workspace {workspace.root_path} is not recognized as a BSL repository")

        existing = self._read_manifest(workspace) if preserve_built_at else None
        timestamp = self._timestamp()
        manifest = BslIndexManifest(
            builder_version=self._builder_version,
            workspace_root=str(workspace.root_path),
            built_at=existing.built_at if existing is not None else timestamp,
            updated_at=timestamp,
            repo_details=repo_details.as_mapping(),
            adapter_features=self._adapter_features,
            schema_extensions=self._schema_extensions,
        )
        manifest_path = self._manifest_path(workspace)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest.to_payload(), indent=2, sort_keys=True), encoding="utf-8")
        return manifest

    def _read_manifest(self, workspace: WorkspaceRef) -> BslIndexManifest | None:
        manifest_path = self._manifest_path(workspace)
        if not manifest_path.is_file():
            return None
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return BslIndexManifest.from_payload(payload)

    def _result_details(
        self,
        workspace: WorkspaceRef,
        manifest: BslIndexManifest,
        *,
        background: bool,
    ) -> dict[str, object]:
        return {
            "adapter_id": "bsl",
            "background": background,
            "manifest_path": str(self._manifest_path(workspace)),
            "index_dir": str(self._index_dir(workspace)),
            "builder_version": manifest.builder_version,
            "repo_details": dict(manifest.repo_details),
            "adapter_features": sorted(manifest.adapter_features),
            "schema_extensions": sorted(manifest.schema_extensions),
            "built_at": manifest.built_at,
            "updated_at": manifest.updated_at,
        }

    @staticmethod
    def _index_dir(workspace: WorkspaceRef) -> Path:
        return workspace.root_path / ".rlm" / "indexes" / "bsl"

    def _manifest_path(self, workspace: WorkspaceRef) -> Path:
        return self._index_dir(workspace) / "manifest.json"

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
