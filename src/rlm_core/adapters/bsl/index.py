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

from .advanced import BslAdvancedExtension, BslAdvancedSnapshot
from .contracts import BSL_INDEXED_FEATURES, BSL_SCHEMA_EXTENSIONS
from .detection import inspect_bsl_workspace
from .live import BslIndexSnapshot, build_bsl_index_snapshot


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
        builder_version: int = 4,
        adapter_features: frozenset[str] = BSL_INDEXED_FEATURES,
        schema_extensions: frozenset[str] = BSL_SCHEMA_EXTENSIONS,
        advanced_extension: BslAdvancedExtension | None = None,
    ) -> None:
        self._builder_version = builder_version
        self._adapter_features = frozenset(adapter_features)
        self._schema_extensions = frozenset(schema_extensions)
        self._advanced_extension = advanced_extension or BslAdvancedExtension()

    def build_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        manifest, snapshot, advanced_snapshot = self._write_index(request.workspace)
        return IndexOperationResult(
            action=IndexLifecycleAction.BUILD,
            status=IndexOperationStatus.COMPLETED,
            details=self._result_details(
                request.workspace,
                manifest,
                snapshot=snapshot,
                advanced_snapshot=advanced_snapshot,
                background=request.background,
            ),
        )

    def update_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        manifest, snapshot, advanced_snapshot = self._write_index(request.workspace, preserve_built_at=True)
        return IndexOperationResult(
            action=IndexLifecycleAction.UPDATE,
            status=IndexOperationStatus.COMPLETED,
            details=self._result_details(
                request.workspace,
                manifest,
                snapshot=snapshot,
                advanced_snapshot=advanced_snapshot,
                background=request.background,
            ),
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

        snapshot = self.load_snapshot(workspace, allow_stale=True)
        advanced_snapshot = self.load_advanced_snapshot(workspace, allow_stale=True)
        stale = manifest.builder_version != self._builder_version or snapshot is None or advanced_snapshot is None
        return IndexStatus(
            available=True,
            stale=stale,
            details=self._result_details(
                workspace,
                manifest,
                snapshot=snapshot,
                advanced_snapshot=advanced_snapshot,
                background=False,
            ),
        )

    def load_snapshot(self, workspace: WorkspaceRef, *, allow_stale: bool = False) -> BslIndexSnapshot | None:
        manifest = self._read_manifest(workspace)
        if manifest is None:
            return None
        if not allow_stale and manifest.builder_version != self._builder_version:
            return None
        snapshot_path = self._snapshot_path(workspace)
        if not snapshot_path.is_file():
            return None
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return BslIndexSnapshot.from_payload(payload)

    def load_advanced_snapshot(
        self,
        workspace: WorkspaceRef,
        *,
        allow_stale: bool = False,
    ) -> BslAdvancedSnapshot | None:
        manifest = self._read_manifest(workspace)
        if manifest is None:
            return None
        if not allow_stale and manifest.builder_version != self._builder_version:
            return None
        advanced_path = self._advanced_snapshot_path(workspace)
        if not advanced_path.is_file():
            return None
        payload = json.loads(advanced_path.read_text(encoding="utf-8"))
        return BslAdvancedSnapshot.from_payload(payload)

    def _write_index(
        self,
        workspace: WorkspaceRef,
        *,
        preserve_built_at: bool = False,
    ) -> tuple[BslIndexManifest, BslIndexSnapshot, BslAdvancedSnapshot]:
        repo_details = inspect_bsl_workspace(workspace.root_path)
        if repo_details is None:
            raise ValueError(f"Workspace {workspace.root_path} is not recognized as a BSL repository")

        existing = self._read_manifest(workspace) if preserve_built_at else None
        snapshot = build_bsl_index_snapshot(workspace.root_path)
        advanced_snapshot = self._advanced_extension.build_snapshot(workspace.root_path)
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
        index_dir = self._index_dir(workspace)
        manifest_path = self._manifest_path(workspace)
        snapshot_path = self._snapshot_path(workspace)
        advanced_path = self._advanced_snapshot_path(workspace)
        index_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(snapshot.to_payload(), indent=2, sort_keys=True), encoding="utf-8")
        advanced_path.write_text(json.dumps(advanced_snapshot.to_payload(), indent=2, sort_keys=True), encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest.to_payload(), indent=2, sort_keys=True), encoding="utf-8")
        return manifest, snapshot, advanced_snapshot

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
        snapshot: BslIndexSnapshot | None,
        advanced_snapshot: BslAdvancedSnapshot | None,
        background: bool,
    ) -> dict[str, object]:
        details: dict[str, object] = {
            "adapter_id": "bsl",
            "background": background,
            "manifest_path": str(self._manifest_path(workspace)),
            "index_dir": str(self._index_dir(workspace)),
            "snapshot_path": str(self._snapshot_path(workspace)),
            "advanced_snapshot_path": str(self._advanced_snapshot_path(workspace)),
            "builder_version": manifest.builder_version,
            "repo_details": dict(manifest.repo_details),
            "adapter_features": sorted(manifest.adapter_features),
            "schema_extensions": sorted(manifest.schema_extensions),
            "advanced_features": sorted(self._advanced_extension.feature_names),
            "built_at": manifest.built_at,
            "updated_at": manifest.updated_at,
        }
        if snapshot is not None:
            details["module_count"] = snapshot.module_count
            details["procedure_count"] = snapshot.procedure_count
            details["call_count"] = snapshot.call_count
        if advanced_snapshot is not None:
            details["object_attribute_count"] = advanced_snapshot.object_attribute_count
            details["predefined_item_count"] = advanced_snapshot.predefined_item_count
        return details

    @staticmethod
    def _index_dir(workspace: WorkspaceRef) -> Path:
        return workspace.root_path / ".rlm" / "indexes" / "bsl"

    def _manifest_path(self, workspace: WorkspaceRef) -> Path:
        return self._index_dir(workspace) / "manifest.json"

    def _snapshot_path(self, workspace: WorkspaceRef) -> Path:
        return self._index_dir(workspace) / "snapshot.json"

    def _advanced_snapshot_path(self, workspace: WorkspaceRef) -> Path:
        return self._index_dir(workspace) / "advanced.json"

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(tz=UTC).replace(microsecond=0).isoformat()
