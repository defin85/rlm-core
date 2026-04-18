from __future__ import annotations

import pytest

from rlm_core.adapters import AdapterRegistry
from rlm_core.adapters.bsl import BslRepositoryAdapter
from rlm_core.index.contracts import IndexLifecycleAction, IndexOperationStatus
from rlm_core.runtime import CoreRuntime, MutationConfirmationError, RuntimeSessionError
from rlm_core.workspace import InMemoryWorkspaceRegistry

CF_MAIN_XML = """\
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses">
  <Configuration>
    <Properties>
      <Name>Accounting</Name>
    </Properties>
  </Configuration>
</MetaDataObject>
"""


def test_runtime_routes_start_execute_and_end_for_direct_path(tmp_path):
    workspace_root = tmp_path / "bsl"
    workspace_root.mkdir()
    (workspace_root / "Configuration.xml").write_text(CF_MAIN_XML, encoding="utf-8")
    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter()]))

    started = runtime.rlm_start(root_path=str(workspace_root), query="find forms")
    executed = runtime.rlm_execute(started.session_id, "bsl_repo_details")
    ended = runtime.rlm_end(started.session_id)

    assert started.adapter_id == "bsl"
    assert "bsl_repo_details" in started.helper_names
    assert started.strategy.startswith("bsl:find forms")
    assert executed.result["config_name"] == "Accounting"
    assert ended.adapter_id == "bsl"


def test_runtime_routes_index_actions_through_core_services(tmp_path):
    workspace_root = tmp_path / "bsl"
    workspace_root.mkdir()
    (workspace_root / "Configuration.xml").write_text(CF_MAIN_XML, encoding="utf-8")
    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter()]))

    built = runtime.rlm_index(IndexLifecycleAction.BUILD, root_path=str(workspace_root))
    status = runtime.rlm_index(IndexLifecycleAction.INFO, root_path=str(workspace_root))

    assert built.status is IndexOperationStatus.COMPLETED
    assert status.available is True
    assert status.details["adapter_id"] == "bsl"


def test_runtime_enforces_confirmation_policy_for_registry_mutations(tmp_path):
    workspace_root = tmp_path / "bsl"
    workspace_root.mkdir()
    (workspace_root / "Configuration.xml").write_text(CF_MAIN_XML, encoding="utf-8")

    workspace_registry = InMemoryWorkspaceRegistry()
    workspace_registry.register(
        "erp",
        workspace_root,
        display_name="ERP",
        adapter_hint="bsl",
        metadata={"mutation_policy": "confirm"},
    )
    runtime = CoreRuntime(
        adapter_registry=AdapterRegistry([BslRepositoryAdapter()]),
        workspace_registry=workspace_registry,
    )

    projects = runtime.rlm_projects()

    assert projects[0].workspace_id == "erp"
    with pytest.raises(MutationConfirmationError):
        runtime.rlm_index(IndexLifecycleAction.BUILD, workspace_id="erp")

    built = runtime.rlm_index(IndexLifecycleAction.BUILD, workspace_id="erp", confirm=True)
    started = runtime.rlm_start(workspace_id="erp")

    assert built.status is IndexOperationStatus.COMPLETED
    assert started.workspace.workspace_id == "erp"


def test_runtime_supports_direct_path_walking_skeleton_without_adapters(tmp_path):
    workspace_root = tmp_path / "repo"
    source_dir = workspace_root / "src"
    source_dir.mkdir(parents=True)
    (source_dir / "main.py").write_text("VALUE = 7\n", encoding="utf-8")
    (workspace_root / "README.md").write_text("# demo\n", encoding="utf-8")

    runtime = CoreRuntime()

    started = runtime.rlm_start(root_path=str(workspace_root))
    first = runtime.rlm_execute(
        started.session_id,
        code="py_files = glob_files('**/*.py')\nprint(py_files[0])\nprint(read_file(py_files[0]).strip())",
    )
    second = runtime.rlm_execute(started.session_id, code="print(len(py_files))")

    assert started.adapter_id == "generic"
    assert "glob_files" in started.helper_names
    assert first.result["error"] is None
    assert "src/main.py" in first.result["stdout"]
    assert "VALUE = 7" in first.result["stdout"]
    assert second.result["stdout"].strip() == "1"


def test_runtime_preserves_namespace_and_releases_session_on_end(tmp_path):
    workspace_root = tmp_path / "repo"
    workspace_root.mkdir()
    runtime = CoreRuntime()

    started = runtime.rlm_start(root_path=str(workspace_root))
    runtime.rlm_execute(started.session_id, code="counter = 40")
    persisted = runtime.rlm_execute(started.session_id, code="counter += 2\nprint(counter)")
    runtime.rlm_end(started.session_id)

    assert persisted.result["error"] is None
    assert persisted.result["stdout"].strip() == "42"
    assert "counter" in persisted.result["variables"]
    with pytest.raises(RuntimeSessionError):
        runtime.rlm_execute(started.session_id, code="print(counter)")
