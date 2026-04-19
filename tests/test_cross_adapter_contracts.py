from __future__ import annotations

from rlm_core.adapters import AdapterRegistry
from rlm_core.adapters.bsl import BslRepositoryAdapter
from rlm_core.adapters.go import GoRepositoryAdapter
from rlm_core.index.contracts import IndexLifecycleAction, IndexOperationStatus
from rlm_core.public_api import PublicApiSurface, PublicIndexRequest, PublicStartRequest
from rlm_core.runtime import CoreRuntime
from tests.go_fixture import build_go_fixture


CF_MAIN_XML = """\
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses">
  <Configuration>
    <Properties>
      <Name>Accounting</Name>
    </Properties>
  </Configuration>
</MetaDataObject>
"""


def _build_bsl_repo(workspace_root) -> None:
    (workspace_root / "Configuration.xml").write_text(CF_MAIN_XML, encoding="utf-8")


def test_runtime_exposes_explicit_cross_adapter_semantics(tmp_path):
    plain_root = tmp_path / "plain"
    plain_root.mkdir()
    (plain_root / "README.md").write_text("# demo\n", encoding="utf-8")

    go_root = tmp_path / "go"
    go_root.mkdir()
    build_go_fixture(go_root)

    bsl_root = tmp_path / "bsl"
    bsl_root.mkdir()
    _build_bsl_repo(bsl_root)

    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter(), GoRepositoryAdapter()]))

    plain_started = runtime.rlm_start(root_path=str(plain_root), query="inspect repo")
    plain_build = runtime.rlm_index(IndexLifecycleAction.BUILD, root_path=str(plain_root))
    plain_info = runtime.rlm_index(IndexLifecycleAction.INFO, root_path=str(plain_root))

    go_started = runtime.rlm_start(root_path=str(go_root), query="inspect handler flow")
    go_build = runtime.rlm_index(IndexLifecycleAction.BUILD, root_path=str(go_root))
    go_info = runtime.rlm_index(IndexLifecycleAction.INFO, root_path=str(go_root))

    bsl_started = runtime.rlm_start(root_path=str(bsl_root), query="trace posting")
    bsl_build = runtime.rlm_index(IndexLifecycleAction.BUILD, root_path=str(bsl_root))
    bsl_info = runtime.rlm_index(IndexLifecycleAction.INFO, root_path=str(bsl_root))

    assert plain_started.adapter_id == "generic"
    assert "glob_files" in plain_started.helper_names
    assert "go_list_packages" not in plain_started.helper_names
    assert "bsl_repo_details" not in plain_started.helper_names
    assert plain_build.status is IndexOperationStatus.UNSUPPORTED
    assert plain_build.details == {
        "adapter_id": "generic",
        "reason": "no_adapter",
        "supported_actions": [],
    }
    assert plain_info.available is False
    assert plain_info.details == {
        "adapter_id": "generic",
        "reason": "no_adapter",
        "supported_actions": [],
        "unsupported_action": "info",
    }

    assert go_started.adapter_id == "go"
    assert "go_list_packages" in go_started.helper_names
    assert "bsl_repo_details" not in go_started.helper_names
    assert go_build.status is IndexOperationStatus.UNSUPPORTED
    assert go_build.details == {
        "adapter_id": "go",
        "reason": "capability_unsupported",
        "supported_actions": [],
    }
    assert go_info.available is False
    assert go_info.details == {
        "adapter_id": "go",
        "reason": "capability_unsupported",
        "supported_actions": [],
        "unsupported_action": "info",
    }

    assert bsl_started.adapter_id == "bsl"
    assert "bsl_repo_details" in bsl_started.helper_names
    assert "go_list_packages" not in bsl_started.helper_names
    assert bsl_build.status is IndexOperationStatus.COMPLETED
    assert bsl_info.available is True
    assert bsl_info.details["adapter_id"] == "bsl"


def test_public_api_preserves_cross_adapter_contracts(tmp_path):
    plain_root = tmp_path / "plain"
    plain_root.mkdir()

    go_root = tmp_path / "go"
    go_root.mkdir()
    build_go_fixture(go_root)

    bsl_root = tmp_path / "bsl"
    bsl_root.mkdir()
    _build_bsl_repo(bsl_root)

    surface = PublicApiSurface()

    plain_start = surface.rlm_start(PublicStartRequest(root_path=str(plain_root), query="inspect repo")).to_payload()
    plain_build = surface.rlm_index(PublicIndexRequest(action="build", root_path=str(plain_root))).to_payload()
    plain_info = surface.rlm_index(PublicIndexRequest(action="info", root_path=str(plain_root))).to_payload()

    go_start = surface.rlm_start(PublicStartRequest(root_path=str(go_root), query="inspect handler flow")).to_payload()
    go_build = surface.rlm_index(PublicIndexRequest(action="build", root_path=str(go_root))).to_payload()
    go_info = surface.rlm_index(PublicIndexRequest(action="info", root_path=str(go_root))).to_payload()

    bsl_start = surface.rlm_start(PublicStartRequest(root_path=str(bsl_root), query="trace posting")).to_payload()
    bsl_build = surface.rlm_index(PublicIndexRequest(action="build", root_path=str(bsl_root))).to_payload()
    bsl_info = surface.rlm_index(PublicIndexRequest(action="info", root_path=str(bsl_root))).to_payload()

    assert plain_start["ok"] is True
    assert plain_start["data"]["adapter_id"] == "generic"
    assert plain_start["data"]["capabilities"]["supported_actions"] == []
    assert "glob_files" in plain_start["data"]["helper_names"]
    assert "go_list_packages" not in plain_start["data"]["helper_names"]
    assert plain_build["ok"] is True
    assert plain_build["data"]["status"] == "unsupported"
    assert plain_build["data"]["details"] == {
        "adapter_id": "generic",
        "reason": "no_adapter",
        "supported_actions": [],
    }
    assert plain_info["ok"] is True
    assert plain_info["data"]["details"] == {
        "adapter_id": "generic",
        "reason": "no_adapter",
        "supported_actions": [],
        "unsupported_action": "info",
    }

    assert go_start["ok"] is True
    assert go_start["data"]["adapter_id"] == "go"
    assert go_start["data"]["capabilities"]["supported_actions"] == []
    assert "go_list_packages" in go_start["data"]["helper_names"]
    assert "bsl_repo_details" not in go_start["data"]["helper_names"]
    assert go_build["ok"] is True
    assert go_build["data"]["status"] == "unsupported"
    assert go_build["data"]["details"] == {
        "adapter_id": "go",
        "reason": "capability_unsupported",
        "supported_actions": [],
    }
    assert go_info["ok"] is True
    assert go_info["data"]["details"] == {
        "adapter_id": "go",
        "reason": "capability_unsupported",
        "supported_actions": [],
        "unsupported_action": "info",
    }

    assert bsl_start["ok"] is True
    assert bsl_start["data"]["adapter_id"] == "bsl"
    assert "bsl_repo_details" in bsl_start["data"]["helper_names"]
    assert "go_list_packages" not in bsl_start["data"]["helper_names"]
    assert bsl_build["ok"] is True
    assert bsl_build["data"]["status"] == "completed"
    assert bsl_info["ok"] is True
    assert bsl_info["data"]["available"] is True
    assert bsl_info["data"]["details"]["adapter_id"] == "bsl"
