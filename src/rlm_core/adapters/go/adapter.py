"""Go adapter implementation."""

from __future__ import annotations

from rlm_core.adapters.contracts import HelperContext, RepositoryDescriptor, StrategyContext
from rlm_core.index.contracts import IndexCapabilityMatrix
from rlm_core.workspace import WorkspaceRef

from .contracts import GO_LIVE_FEATURES
from .detection import inspect_go_workspace
from .live import make_go_live_helpers


class GoRepositoryAdapter:
    """Adapter for Go repositories."""

    adapter_id = "go"
    display_name = "Go"

    def __init__(self) -> None:
        self.capabilities = IndexCapabilityMatrix(adapter_features=GO_LIVE_FEATURES)

    def detect(self, workspace: WorkspaceRef) -> bool:
        return inspect_go_workspace(workspace.root_path) is not None

    def describe_repo(self, workspace: WorkspaceRef) -> RepositoryDescriptor:
        details = inspect_go_workspace(workspace.root_path)
        if details is None:
            raise ValueError(f"Workspace {workspace.root_path} is not recognized as a Go repository")
        return RepositoryDescriptor(
            adapter_id=self.adapter_id,
            workspace_root=workspace.root_path,
            language="go",
            details=details.as_mapping(),
        )

    def register_helpers(self, context: HelperContext):
        return make_go_live_helpers(context.workspace.root_path, details=context.descriptor.details)

    def build_strategy(self, query: str, context: StrategyContext) -> str:
        feature_list = ", ".join(sorted(context.capabilities.adapter_features))
        normalized_query = query.strip() or "inspect go repository"
        return (
            f"go:{normalized_query} [adapter_features={feature_list}]\n"
            "LIVE WORKFLOW:\n"
            "- BROWSE: go_list_packages(), go_find_go_files(package='service')\n"
            "- NAVIGATE: go_extract_declarations('internal/service/service.go')\n"
            "- TRACE: go_find_imports(package='service', import_path='net/http')\n"
            "- READ: go_read_declaration('internal/service/service.go', 'ServeHTTP'), read_file('go.mod')\n"
        )

    def get_index_hooks(self):
        return None
