from __future__ import annotations

from dataclasses import dataclass

from rlm_core.adapters import AdapterRegistry, HelperContext
from rlm_core.adapters.bsl import (
    BSL_SCHEMA_EXTENSIONS,
    BslConfigRole,
    BslRepositoryAdapter,
    BslSourceFormat,
    inspect_bsl_workspace,
)
from rlm_core.index.contracts import IndexCapabilityMatrix, IndexOperationStatus
from rlm_core.index.manager import IndexManager
from rlm_core.workspace import WorkspaceRef, WorkspaceSource


CF_EXTENSION_XML = """\
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses">
  <Configuration>
    <Properties>
      <Name>AccountingExtension</Name>
      <NamePrefix>Ext</NamePrefix>
      <ConfigurationExtensionPurpose>AddOn</ConfigurationExtensionPurpose>
    </Properties>
  </Configuration>
</MetaDataObject>
"""

EDT_MAIN_MDO = """\
<mdclass:Configuration xmlns:mdclass="http://g5.1c.ru/v8/dt/metadata/mdclass">
  <name>Accounting</name>
</mdclass:Configuration>
"""


def _build_live_bsl_fixture(workspace_root):
    (workspace_root / "Configuration.xml").write_text(CF_EXTENSION_XML, encoding="utf-8")

    object_module = workspace_root / "Documents" / "SalesOrder" / "Ext" / "ObjectModule.bsl"
    object_module.parent.mkdir(parents=True)
    object_module.write_text(
        "Процедура ОбработкаПроведения(Отказ, РежимПроведения)\n"
        "    ПодготовитьДвижения();\n"
        "КонецПроцедуры\n",
        encoding="utf-8",
    )

    manager_module = workspace_root / "Documents" / "SalesOrder" / "Ext" / "ManagerModule.bsl"
    manager_module.write_text(
        "Функция ВерсияДокумента() Экспорт\n"
        "    Возврат \"1.0\";\n"
        "КонецФункции\n",
        encoding="utf-8",
    )

    form_module = workspace_root / "Documents" / "SalesOrder" / "Forms" / "DocumentForm" / "Ext" / "Form" / "Module.bsl"
    form_module.parent.mkdir(parents=True)
    form_module.write_text(
        "Процедура ПриОткрытии()\n"
        "    ОбновитьКоманды();\n"
        "КонецПроцедуры\n",
        encoding="utf-8",
    )

    common_module = workspace_root / "CommonModules" / "CommonServer" / "Ext" / "Module.bsl"
    common_module.parent.mkdir(parents=True)
    common_module.write_text(
        "Процедура ПодготовитьДвижения() Экспорт\n"
        "КонецПроцедуры\n",
        encoding="utf-8",
    )

    return object_module.relative_to(workspace_root).as_posix()


def test_bsl_detection_reports_adapter_owned_repository_details(tmp_path):
    workspace_root = tmp_path / "wrapper"
    config_root = workspace_root / "src"
    config_root.mkdir(parents=True)
    (config_root / "Configuration.xml").write_text(CF_EXTENSION_XML, encoding="utf-8")

    details = inspect_bsl_workspace(workspace_root)

    assert details is not None
    assert details.source_format is BslSourceFormat.CF
    assert details.config_role is BslConfigRole.EXTENSION
    assert details.config_root == "src"
    assert details.config_file == "src/Configuration.xml"
    assert details.config_name == "AccountingExtension"
    assert details.extension_prefix == "Ext"
    assert details.extension_purpose == "AddOn"


def test_bsl_adapter_builds_manifest_with_schema_extensions(tmp_path):
    workspace_root = tmp_path / "workspace"
    config_dir = workspace_root / "Configuration"
    config_dir.mkdir(parents=True)
    (config_dir / "Configuration.mdo").write_text(EDT_MAIN_MDO, encoding="utf-8")

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = BslRepositoryAdapter()
    manager = IndexManager(AdapterRegistry([adapter]))

    result = manager.build(workspace)
    status = manager.info(workspace)
    descriptor = adapter.describe_repo(workspace)
    helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))

    assert result.status is IndexOperationStatus.COMPLETED
    assert status.available is True
    assert status.details["repo_details"]["source_format"] == "edt"
    assert status.details["repo_details"]["config_role"] == "main"
    assert set(status.details["schema_extensions"]) == BSL_SCHEMA_EXTENSIONS
    assert sorted(helpers["bsl_index_features"]()) == sorted(adapter.capabilities.adapter_features)


def test_bsl_live_helpers_support_navigation_and_targeted_code_reading(tmp_path):
    workspace_root = tmp_path / "live"
    workspace_root.mkdir()
    object_module_path = _build_live_bsl_fixture(workspace_root)

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = BslRepositoryAdapter()
    descriptor = adapter.describe_repo(workspace)
    helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))

    by_name = helpers["bsl_find_modules"]("SalesOrder")
    by_type = helpers["bsl_find_by_type"]("Документ")
    procedures = helpers["bsl_extract_procedures"](object_module_path)
    procedure_body = helpers["bsl_read_procedure"](object_module_path, "ОбработкаПроведения")

    assert sorted(item["module_type"] for item in by_name) == ["FormModule", "ManagerModule", "ObjectModule"]
    assert len(by_type) == 3
    assert all(item["category"] == "Documents" for item in by_type)
    assert [item["name"] for item in procedures] == ["ОбработкаПроведения"]
    assert procedures[0]["line"] == 1
    assert procedure_body is not None
    assert "ПодготовитьДвижения();" in procedure_body


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


def test_capability_negotiation_distinguishes_bsl_index_from_live_only_adapter(tmp_path):
    bsl_root = tmp_path / "bsl"
    bsl_root.mkdir()
    (bsl_root / "Configuration.xml").write_text(CF_EXTENSION_XML, encoding="utf-8")
    plain_root = tmp_path / "plain"
    plain_root.mkdir()

    registry = AdapterRegistry([BslRepositoryAdapter(), LiveOnlyAdapter()])
    manager = IndexManager(registry)

    bsl_result = manager.build(WorkspaceRef(root_path=bsl_root, source=WorkspaceSource.DIRECT_PATH))
    live_result = manager.build(WorkspaceRef(root_path=plain_root, source=WorkspaceSource.DIRECT_PATH))

    assert bsl_result.status is IndexOperationStatus.COMPLETED
    assert live_result.status is IndexOperationStatus.UNSUPPORTED
    assert live_result.details["supported_actions"] == []
