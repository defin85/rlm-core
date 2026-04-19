from __future__ import annotations

from rlm_core.adapters import AdapterRegistry, HelperContext, StrategyContext
from rlm_core.adapters.go import GO_LIVE_FEATURES, GoRepositoryAdapter, inspect_go_workspace
from rlm_core.index.contracts import IndexOperationStatus
from rlm_core.index.manager import IndexManager
from rlm_core.workspace import WorkspaceRef, WorkspaceSource
from tests.go_fixture import GO_MODULE_PATH, build_go_fixture


def test_go_detection_reports_adapter_owned_repository_details(tmp_path):
    workspace_root = tmp_path / "go"
    workspace_root.mkdir()
    build_go_fixture(workspace_root)

    details = inspect_go_workspace(workspace_root)

    assert details is not None
    assert details.module_root == "."
    assert details.module_file == "go.mod"
    assert details.module_path == GO_MODULE_PATH
    assert details.go_version == "1.22.3"


def test_go_adapter_exposes_live_navigation_helpers_and_strategy(tmp_path):
    workspace_root = tmp_path / "go"
    workspace_root.mkdir()
    fixture = build_go_fixture(workspace_root)

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = GoRepositoryAdapter()
    descriptor = adapter.describe_repo(workspace)
    helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))
    strategy = adapter.build_strategy(
        "inspect handler flow",
        StrategyContext(workspace=workspace, descriptor=descriptor, capabilities=adapter.capabilities),
    )

    packages = helpers["go_list_packages"]()
    files = helpers["go_find_go_files"](package="service")
    declarations = helpers["go_extract_declarations"](fixture["service_file"])
    serve_http = helpers["go_read_declaration"](fixture["service_file"], "ServeHTTP")
    imports = helpers["go_find_imports"](package="service", import_path="net/http")

    assert descriptor.language == "go"
    assert descriptor.details["module_path"] == GO_MODULE_PATH
    assert helpers["go_repo_details"]()["go_version"] == "1.22.3"
    assert set(adapter.capabilities.adapter_features) == GO_LIVE_FEATURES
    assert "LIVE WORKFLOW" in strategy
    assert "go_list_packages" in strategy
    assert "go_read_declaration" in strategy
    assert {item["package"] for item in packages} == {"main", "service", "storage"}
    assert files == [
        {
            "path": fixture["service_file"],
            "directory": "internal/service",
            "package": "service",
            "is_test": False,
        }
    ]
    assert [item["name"] for item in declarations] == ["Config", "Service", "NewService", "ServeHTTP"]
    assert declarations[-1]["kind"] == "method"
    assert declarations[-1]["receiver"] == "s *Service"
    assert 'fmt.Fprintf(w, "ok")' in serve_http
    assert imports == [
        {
            "path": fixture["service_file"],
            "package": "service",
            "import": "net/http",
        }
    ]


def test_go_adapter_reports_live_only_capabilities_through_shared_index_manager(tmp_path):
    workspace_root = tmp_path / "go"
    workspace_root.mkdir()
    build_go_fixture(workspace_root)

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = GoRepositoryAdapter()
    manager = IndexManager(AdapterRegistry([adapter]))

    built = manager.build(workspace)
    info = manager.info(workspace)

    assert built.status is IndexOperationStatus.UNSUPPORTED
    assert built.details["supported_actions"] == []
    assert info.available is False
    assert info.details["unsupported_action"] == "info"
