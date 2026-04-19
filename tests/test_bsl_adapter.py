from __future__ import annotations

from dataclasses import dataclass

from rlm_core.adapters import AdapterRegistry, HelperContext
from rlm_core.adapters.bsl import (
    BSL_ADVANCED_FEATURES,
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


def _build_document_metadata_xml(*, include_comment: bool = False) -> str:
    extra_attribute = ""
    if include_comment:
        extra_attribute = """\
      <Attribute>
        <Properties>
          <Name>Комментарий</Name>
          <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Комментарий</v8:content></v8:item></Synonym>
          <Type><v8:Type>xs:string</v8:Type></Type>
        </Properties>
      </Attribute>
"""
    return f"""\
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
  <Document>
    <Properties>
      <Name>SalesOrder</Name>
      <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Заказ покупателя</v8:content></v8:item></Synonym>
    </Properties>
    <ChildObjects>
      <Attribute>
        <Properties>
          <Name>Организация</Name>
          <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Организация</v8:content></v8:item></Synonym>
          <Type><v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:CatalogRef.Организации</v8:Type></Type>
        </Properties>
      </Attribute>
      <Attribute>
        <Properties>
          <Name>Сумма</Name>
          <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Сумма</v8:content></v8:item></Synonym>
          <Type><v8:Type>xs:decimal</v8:Type></Type>
        </Properties>
      </Attribute>
{extra_attribute}      <TabularSection>
        <Properties>
          <Name>Товары</Name>
          <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Товары</v8:content></v8:item></Synonym>
        </Properties>
        <ChildObjects>
          <Attribute>
            <Properties>
              <Name>Номенклатура</Name>
              <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Номенклатура</v8:content></v8:item></Synonym>
              <Type><v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:CatalogRef.Номенклатура</v8:Type></Type>
            </Properties>
          </Attribute>
        </ChildObjects>
      </TabularSection>
    </ChildObjects>
  </Document>
</MetaDataObject>
"""


def _build_chart_metadata_xml() -> str:
    return """\
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
  <ChartOfCharacteristicTypes>
    <Properties>
      <Name>CostTypes</Name>
      <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Виды субконто</v8:content></v8:item></Synonym>
    </Properties>
  </ChartOfCharacteristicTypes>
</MetaDataObject>
"""


def _build_predefined_xml(*, include_fixed_assets: bool = False) -> str:
    extra_item = ""
    if include_fixed_assets:
        extra_item = """\
<Item id="ccc">
    <Name>ОсновныеСредства</Name>
    <Code>00077</Code>
    <Description>Основные средства</Description>
    <Type>
        <v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:CatalogRef.ОсновныеСредства</v8:Type>
    </Type>
    <IsFolder>false</IsFolder>
</Item>
"""
    return f"""\
<ChartOfCharacteristicTypes xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
<PredefinedData>
<Item id="aaa">
    <Name>РеализуемыеАктивы</Name>
    <Code>00055</Code>
    <Description>Реализуемые активы</Description>
    <Type>
        <v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:CatalogRef.Номенклатура</v8:Type>
        <v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:CatalogRef.Контрагенты</v8:Type>
    </Type>
    <IsFolder>false</IsFolder>
</Item>
<Item id="bbb">
    <Name>ВидыДеятельности</Name>
    <Code>00010</Code>
    <Description>Виды деятельности</Description>
    <Type>
        <v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:CatalogRef.ВидыДеятельности</v8:Type>
    </Type>
    <IsFolder>true</IsFolder>
</Item>
{extra_item}</PredefinedData>
</ChartOfCharacteristicTypes>
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


def _apply_post_build_changes(workspace_root):
    object_module = workspace_root / "Documents" / "SalesOrder" / "Ext" / "ObjectModule.bsl"
    object_module.write_text(
        object_module.read_text(encoding="utf-8")
        + "\n"
        + "Процедура ДопПроверка()\n"
        + "    ПодготовитьДвижения();\n"
        + "КонецПроцедуры\n",
        encoding="utf-8",
    )

    audit_form = workspace_root / "Documents" / "SalesOrder" / "Forms" / "AuditForm" / "Ext" / "Form" / "Module.bsl"
    audit_form.parent.mkdir(parents=True)
    audit_form.write_text(
        "Процедура ПриСозданииНаСервере()\n"
        "    ПодготовитьДвижения();\n"
        "КонецПроцедуры\n",
        encoding="utf-8",
    )


def _add_advanced_cf_metadata(workspace_root):
    document_xml = workspace_root / "Documents" / "SalesOrder" / "Ext" / "Document.xml"
    document_xml.write_text(_build_document_metadata_xml(), encoding="utf-8")

    chart_root = workspace_root / "ChartsOfCharacteristicTypes" / "CostTypes" / "Ext"
    chart_root.mkdir(parents=True, exist_ok=True)
    (chart_root / "ChartOfCharacteristicTypes.xml").write_text(_build_chart_metadata_xml(), encoding="utf-8")
    (chart_root / "Predefined.xml").write_text(_build_predefined_xml(), encoding="utf-8")


def _apply_advanced_metadata_changes(workspace_root):
    document_xml = workspace_root / "Documents" / "SalesOrder" / "Ext" / "Document.xml"
    document_xml.write_text(_build_document_metadata_xml(include_comment=True), encoding="utf-8")

    predefined_xml = (
        workspace_root / "ChartsOfCharacteristicTypes" / "CostTypes" / "Ext" / "Predefined.xml"
    )
    predefined_xml.write_text(_build_predefined_xml(include_fixed_assets=True), encoding="utf-8")


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


def test_bsl_index_lifecycle_build_info_and_update_refresh_snapshot(tmp_path):
    workspace_root = tmp_path / "indexed"
    workspace_root.mkdir()
    _build_live_bsl_fixture(workspace_root)

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = BslRepositoryAdapter()
    manager = IndexManager(AdapterRegistry([adapter]))

    built = manager.build(workspace)
    status = manager.info(workspace)

    manifest_path = workspace_root / ".rlm" / "indexes" / "bsl" / "manifest.json"
    snapshot_path = workspace_root / ".rlm" / "indexes" / "bsl" / "snapshot.json"

    assert built.status is IndexOperationStatus.COMPLETED
    assert manifest_path.is_file()
    assert snapshot_path.is_file()
    assert status.available is True
    assert status.stale is False
    assert status.details["module_count"] == 4
    assert status.details["procedure_count"] == 4
    assert status.details["call_count"] == 2

    _apply_post_build_changes(workspace_root)
    updated = manager.update(workspace)
    refreshed = manager.info(workspace)

    assert updated.status is IndexOperationStatus.COMPLETED
    assert updated.details["built_at"] == built.details["built_at"]
    assert refreshed.details["module_count"] == 5
    assert refreshed.details["procedure_count"] == 6
    assert refreshed.details["call_count"] == 4


def test_bsl_indexed_helpers_stay_on_snapshot_until_index_update(tmp_path):
    workspace_root = tmp_path / "indexed-helpers"
    workspace_root.mkdir()
    object_module_path = _build_live_bsl_fixture(workspace_root)

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = BslRepositoryAdapter()
    manager = IndexManager(AdapterRegistry([adapter]))

    manager.build(workspace)
    _apply_post_build_changes(workspace_root)

    descriptor = adapter.describe_repo(workspace)
    helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))

    snapshot_modules = helpers["bsl_find_modules"]("SalesOrder")
    snapshot_procedures = helpers["bsl_extract_procedures"](object_module_path)
    snapshot_callers = helpers["bsl_find_callers"]("ПодготовитьДвижения")
    snapshot_body = helpers["bsl_read_procedure"](object_module_path, "ДопПроверка")

    assert sorted(item["module_type"] for item in snapshot_modules) == ["FormModule", "ManagerModule", "ObjectModule"]
    assert [item["name"] for item in snapshot_procedures] == ["ОбработкаПроведения"]
    assert snapshot_callers["_meta"]["total_callers"] == 1
    assert snapshot_body is None

    manager.update(workspace)
    refreshed_helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))

    refreshed_modules = refreshed_helpers["bsl_find_modules"]("SalesOrder")
    refreshed_procedures = refreshed_helpers["bsl_extract_procedures"](object_module_path)
    refreshed_callers = refreshed_helpers["bsl_find_callers"]("ПодготовитьДвижения")
    refreshed_body = refreshed_helpers["bsl_read_procedure"](object_module_path, "ДопПроверка")

    assert sorted(item["module_type"] for item in refreshed_modules) == [
        "FormModule",
        "FormModule",
        "ManagerModule",
        "ObjectModule",
    ]
    assert [item["name"] for item in refreshed_procedures] == ["ОбработкаПроведения", "ДопПроверка"]
    assert refreshed_callers["_meta"]["total_callers"] == 3
    assert refreshed_body is not None
    assert "ПодготовитьДвижения();" in refreshed_body


def test_bsl_advanced_helpers_support_live_metadata_queries(tmp_path):
    workspace_root = tmp_path / "advanced-live"
    workspace_root.mkdir()
    _build_live_bsl_fixture(workspace_root)
    _add_advanced_cf_metadata(workspace_root)

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = BslRepositoryAdapter()
    descriptor = adapter.describe_repo(workspace)
    helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))

    features = helpers["bsl_advanced_features"]()
    attrs = helpers["bsl_find_attributes"](object_name="Documents/SalesOrder")
    ts_attrs = helpers["bsl_find_attributes"](object_name="Documents/SalesOrder", kind="ts_attribute")
    predefined = helpers["bsl_find_predefined"](name="РеализуемыеАктивы")

    assert features == sorted(BSL_ADVANCED_FEATURES)
    assert [item["attr_name"] for item in attrs] == ["Организация", "Сумма", "Номенклатура"]
    assert attrs[0]["attr_type"] == ["CatalogRef.Организации"]
    assert attrs[1]["attr_type"] == ["Number"]
    assert ts_attrs == [
        {
            "object_name": "SalesOrder",
            "category": "Documents",
            "attr_name": "Номенклатура",
            "attr_synonym": "Номенклатура",
            "attr_type": ["CatalogRef.Номенклатура"],
            "attr_kind": "ts_attribute",
            "ts_name": "Товары",
        }
    ]
    assert predefined == [
        {
            "object_name": "CostTypes",
            "category": "ChartsOfCharacteristicTypes",
            "item_name": "РеализуемыеАктивы",
            "item_synonym": "Реализуемые активы",
            "item_code": "00055",
            "types": ["CatalogRef.Номенклатура", "CatalogRef.Контрагенты"],
            "is_folder": False,
        }
    ]


def test_bsl_advanced_helpers_use_index_snapshot_until_update(tmp_path):
    workspace_root = tmp_path / "advanced-indexed"
    workspace_root.mkdir()
    _build_live_bsl_fixture(workspace_root)
    _add_advanced_cf_metadata(workspace_root)

    workspace = WorkspaceRef(root_path=workspace_root, source=WorkspaceSource.DIRECT_PATH)
    adapter = BslRepositoryAdapter()
    manager = IndexManager(AdapterRegistry([adapter]))

    built = manager.build(workspace)
    status = manager.info(workspace)

    advanced_path = workspace_root / ".rlm" / "indexes" / "bsl" / "advanced.json"
    assert built.status is IndexOperationStatus.COMPLETED
    assert advanced_path.is_file()
    assert status.details["advanced_features"] == sorted(BSL_ADVANCED_FEATURES)
    assert status.details["object_attribute_count"] == 3
    assert status.details["predefined_item_count"] == 2

    _apply_advanced_metadata_changes(workspace_root)

    descriptor = adapter.describe_repo(workspace)
    helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))

    assert helpers["bsl_find_attributes"](name="Комментарий") == []
    assert helpers["bsl_find_predefined"](name="ОсновныеСредства") == []

    updated = manager.update(workspace)
    refreshed = manager.info(workspace)
    refreshed_helpers = adapter.register_helpers(HelperContext(workspace=workspace, descriptor=descriptor))

    assert updated.status is IndexOperationStatus.COMPLETED
    assert refreshed.details["object_attribute_count"] == 4
    assert refreshed.details["predefined_item_count"] == 3
    assert refreshed_helpers["bsl_find_attributes"](name="Комментарий") == [
        {
            "object_name": "SalesOrder",
            "category": "Documents",
            "attr_name": "Комментарий",
            "attr_synonym": "Комментарий",
            "attr_type": ["String"],
            "attr_kind": "attribute",
            "ts_name": None,
        }
    ]
    assert refreshed_helpers["bsl_find_predefined"](name="ОсновныеСредства") == [
        {
            "object_name": "CostTypes",
            "category": "ChartsOfCharacteristicTypes",
            "item_name": "ОсновныеСредства",
            "item_synonym": "Основные средства",
            "item_code": "00077",
            "types": ["CatalogRef.ОсновныеСредства"],
            "is_folder": False,
        }
    ]


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
