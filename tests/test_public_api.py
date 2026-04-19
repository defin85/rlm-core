from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from threading import Event

from rlm_core.adapters import AdapterRegistry
from rlm_core.adapters.bsl import BslRepositoryAdapter, inspect_bsl_workspace
from rlm_core.cli import run_cli
from rlm_core.index.contracts import (
    IndexBuildRequest,
    IndexCapabilityMatrix,
    IndexLifecycleAction,
    IndexOperationResult,
    IndexOperationStatus,
    IndexStatus,
)
from rlm_core.public_api import (
    PublicApiSurface,
    PublicEndRequest,
    PublicExecuteRequest,
    PublicIndexJobRequest,
    PublicIndexRequest,
    PublicStartRequest,
    PublicWaitForIndexJobRequest,
)
from rlm_core.runtime import CoreRuntime
from rlm_core.workspace import WorkspaceRef
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


class BackgroundHooks:
    def __init__(self, *, gate: Event | None = None) -> None:
        self._gate = gate

    def build_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        if self._gate is not None:
            self._gate.wait(timeout=1.0)
        return IndexOperationResult(
            action=IndexLifecycleAction.BUILD,
            status=IndexOperationStatus.COMPLETED,
            details={"background": request.background},
        )

    def update_index(self, request: IndexBuildRequest) -> IndexOperationResult:
        return IndexOperationResult(
            action=IndexLifecycleAction.UPDATE,
            status=IndexOperationStatus.COMPLETED,
            details={"background": request.background},
        )

    def drop_index(self, workspace: WorkspaceRef) -> IndexOperationResult:
        return IndexOperationResult(
            action=IndexLifecycleAction.DROP,
            status=IndexOperationStatus.COMPLETED,
            details={"workspace": str(workspace.root_path)},
        )

    def get_index_status(self, workspace: WorkspaceRef) -> IndexStatus:
        return IndexStatus(available=True, stale=False, details={"workspace": str(workspace.root_path)})


@dataclass
class BackgroundAdapter:
    adapter_id: str = "background"
    display_name: str = "Background"
    capabilities: IndexCapabilityMatrix = IndexCapabilityMatrix(
        supports_prebuilt_index=True,
        supports_incremental_update=True,
        supports_background_build=True,
    )
    hooks: BackgroundHooks = field(default_factory=BackgroundHooks)

    def detect(self, workspace: WorkspaceRef) -> bool:
        return True

    def describe_repo(self, workspace: WorkspaceRef):
        raise NotImplementedError

    def register_helpers(self, context):
        return {}

    def build_strategy(self, query: str, context) -> str:
        return query

    def get_index_hooks(self):
        return self.hooks


@dataclass
class LiveOnlyAdapter:
    adapter_id: str = "live"
    display_name: str = "LiveOnly"
    capabilities: IndexCapabilityMatrix = IndexCapabilityMatrix()

    def detect(self, workspace: WorkspaceRef) -> bool:
        return inspect_bsl_workspace(workspace.root_path) is None

    def describe_repo(self, workspace: WorkspaceRef):
        raise NotImplementedError

    def register_helpers(self, context):
        return {}

    def build_strategy(self, query: str, context) -> str:
        return query

    def get_index_hooks(self):
        return None


def test_public_api_exposes_serializable_runtime_contracts(tmp_path):
    workspace_root = tmp_path / "repo"
    source_dir = workspace_root / "src"
    source_dir.mkdir(parents=True)
    (source_dir / "main.py").write_text("VALUE = 7\n", encoding="utf-8")

    surface = PublicApiSurface(runtime=CoreRuntime())

    started = surface.rlm_start(PublicStartRequest(root_path=str(workspace_root), query="explore repo"))
    started_payload = started.to_payload()

    assert started.ok is True
    assert started_payload["tool_name"] == "rlm_start"
    assert started_payload["data"]["response_type"] == "rlm_start"
    assert started_payload["data"]["workspace"]["source"] == "direct_path"
    assert started_payload["data"]["capabilities"]["generic_only"] is True
    assert started_payload["data"]["capabilities"]["supported_actions"] == []

    session_id = started_payload["data"]["session_id"]
    executed = surface.rlm_execute(
        PublicExecuteRequest(
            session_id=session_id,
            code="py_files = glob_files('**/*.py')\nprint(py_files[0])\nprint(read_file(py_files[0]).strip())",
        )
    )
    executed_payload = executed.to_payload()

    assert executed.ok is True
    assert executed_payload["data"]["response_type"] == "rlm_execute"
    assert "src/main.py" in executed_payload["data"]["result"]["stdout"]
    assert "VALUE = 7" in executed_payload["data"]["result"]["stdout"]

    ended = surface.rlm_end(PublicEndRequest(session_id=session_id))
    ended_payload = ended.to_payload()

    assert ended.ok is True
    assert ended_payload["data"]["response_type"] == "rlm_end"
    assert ended_payload["data"]["adapter_id"] == "generic"


def test_public_api_returns_structured_error_payloads():
    surface = PublicApiSurface(runtime=CoreRuntime())

    failed = surface.rlm_execute(PublicExecuteRequest(session_id="missing", code="print(1)"))
    payload = failed.to_payload()

    assert failed.ok is False
    assert payload["tool_name"] == "rlm_execute"
    assert payload["error"]["code"] == "runtime_session_error"
    assert payload["error"]["details"]["type"] == "RuntimeSessionError"


def test_public_api_tracks_background_index_jobs(tmp_path):
    workspace_root = tmp_path / "background"
    workspace_root.mkdir()
    gate = Event()
    runtime = CoreRuntime(
        adapter_registry=AdapterRegistry([BackgroundAdapter(hooks=BackgroundHooks(gate=gate))]),
    )
    surface = PublicApiSurface(runtime=runtime)

    started = surface.rlm_index(
        PublicIndexRequest(
            action=IndexLifecycleAction.BUILD,
            root_path=str(workspace_root),
            background=True,
        )
    )
    started_payload = started.to_payload()
    job_id = started_payload["data"]["details"]["job_id"]

    status = surface.rlm_index_job(PublicIndexJobRequest(job_id=job_id))
    status_payload = status.to_payload()

    assert started.ok is True
    assert started_payload["data"]["response_type"] == "index_operation"
    assert started_payload["data"]["status"] == "started"
    assert status.ok is True
    assert status_payload["data"]["response_type"] == "index_job"
    assert status_payload["data"]["status"] == "started"

    gate.set()
    completed = surface.rlm_wait_for_index_job(
        PublicWaitForIndexJobRequest(job_id=job_id, timeout_seconds=1.0)
    )
    completed_payload = completed.to_payload()

    assert completed.ok is True
    assert completed_payload["data"]["response_type"] == "index_job"
    assert completed_payload["data"]["status"] == "completed"
    assert completed_payload["data"]["details"]["background"] is True


def test_public_api_surfaces_capability_differences_consistently(tmp_path):
    bsl_root = tmp_path / "bsl"
    bsl_root.mkdir()
    (bsl_root / "Configuration.xml").write_text(CF_MAIN_XML, encoding="utf-8")

    plain_root = tmp_path / "plain"
    plain_root.mkdir()

    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter(), LiveOnlyAdapter()]))
    surface = PublicApiSurface(runtime=runtime)

    bsl_result = surface.rlm_index(PublicIndexRequest(action="build", root_path=str(bsl_root)))
    plain_result = surface.rlm_index(PublicIndexRequest(action="build", root_path=str(plain_root)))

    assert bsl_result.ok is True
    assert bsl_result.to_payload()["data"]["status"] == "completed"
    assert plain_result.ok is True
    assert plain_result.to_payload()["data"]["status"] == "unsupported"
    assert plain_result.to_payload()["data"]["details"]["supported_actions"] == []


def test_cli_emits_json_contracts_for_runtime_roundtrip(tmp_path):
    workspace_root = tmp_path / "repo"
    source_dir = workspace_root / "src"
    source_dir.mkdir(parents=True)
    (source_dir / "main.py").write_text("VALUE = 7\n", encoding="utf-8")

    surface = PublicApiSurface(runtime=CoreRuntime())

    started_stdout = io.StringIO()
    start_code = run_cli(
        ["start", "--root-path", str(workspace_root), "--query", "inspect repo"],
        surface=surface,
        stdout=started_stdout,
    )
    started_payload = json.loads(started_stdout.getvalue())
    session_id = started_payload["data"]["session_id"]

    execute_stdout = io.StringIO()
    execute_code = run_cli(
        ["execute", session_id, "--code", "print('ok')"],
        surface=surface,
        stdout=execute_stdout,
    )
    execute_payload = json.loads(execute_stdout.getvalue())

    end_stdout = io.StringIO()
    end_code = run_cli(["end", session_id], surface=surface, stdout=end_stdout)
    end_payload = json.loads(end_stdout.getvalue())

    assert start_code == 0
    assert started_payload["tool_name"] == "rlm_start"
    assert started_payload["data"]["response_type"] == "rlm_start"
    assert execute_code == 0
    assert execute_payload["tool_name"] == "rlm_execute"
    assert execute_payload["data"]["result"]["stdout"].strip() == "ok"
    assert end_code == 0
    assert end_payload["tool_name"] == "rlm_end"
    assert end_payload["data"]["response_type"] == "rlm_end"


def test_cli_surfaces_unsupported_capabilities_consistently(tmp_path):
    plain_root = tmp_path / "plain"
    plain_root.mkdir()

    surface = PublicApiSurface(
        runtime=CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter(), LiveOnlyAdapter()]))
    )
    stdout = io.StringIO()

    code = run_cli(
        ["index", "build", "--root-path", str(plain_root)],
        surface=surface,
        stdout=stdout,
    )
    payload = json.loads(stdout.getvalue())

    assert code == 0
    assert payload["tool_name"] == "rlm_index"
    assert payload["data"]["response_type"] == "index_operation"
    assert payload["data"]["status"] == "unsupported"
    assert payload["data"]["details"]["supported_actions"] == []


def test_public_api_default_runtime_supports_go_repositories(tmp_path):
    workspace_root = tmp_path / "go"
    workspace_root.mkdir()
    fixture = build_go_fixture(workspace_root)

    surface = PublicApiSurface()

    started = surface.rlm_start(PublicStartRequest(root_path=str(workspace_root), query="inspect handler flow"))
    started_payload = started.to_payload()
    session_id = started_payload["data"]["session_id"]

    executed = surface.rlm_execute(
        PublicExecuteRequest(
            session_id=session_id,
            helper_name="go_read_declaration",
            arguments={"path": fixture["service_file"], "name": "ServeHTTP"},
        )
    )
    executed_payload = executed.to_payload()
    built = surface.rlm_index(PublicIndexRequest(action="build", root_path=str(workspace_root)))
    built_payload = built.to_payload()

    assert started.ok is True
    assert started_payload["tool_name"] == "rlm_start"
    assert started_payload["data"]["response_type"] == "rlm_start"
    assert started_payload["data"]["adapter_id"] == "go"
    assert started_payload["data"]["capabilities"]["generic_only"] is False
    assert started_payload["data"]["capabilities"]["supported_actions"] == []
    assert started_payload["data"]["capabilities"]["adapter_features"] == ["declarations", "imports", "packages"]
    assert started_payload["data"]["descriptor"]["module_file"] == "go.mod"
    assert "go_list_packages" in started_payload["data"]["helper_names"]
    assert "go_read_declaration" in started_payload["data"]["helper_names"]
    assert started_payload["data"]["strategy"].startswith("go:inspect handler flow")
    assert executed.ok is True
    assert executed_payload["data"]["response_type"] == "rlm_execute"
    assert 'fmt.Fprintf(w, "ok")' in executed_payload["data"]["result"]
    assert built.ok is True
    assert built_payload["data"]["response_type"] == "index_operation"
    assert built_payload["data"]["status"] == "unsupported"
    assert built_payload["data"]["details"]["supported_actions"] == []
