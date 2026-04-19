from __future__ import annotations

import pytest

from rlm_core.adapters import AdapterRegistry
from rlm_core.adapters.bsl import BslRepositoryAdapter
from rlm_core.adapters.go import GoRepositoryAdapter
from rlm_core.index.contracts import IndexLifecycleAction, IndexOperationStatus
from rlm_core.runtime import CoreRuntime, MutationConfirmationError, RuntimeSessionError
from rlm_core.workspace import InMemoryWorkspaceRegistry
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


def _build_document_metadata_xml() -> str:
    return """\
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
    </ChildObjects>
  </Document>
</MetaDataObject>
"""


def _build_predefined_xml() -> str:
    return """\
<ChartOfCharacteristicTypes xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core">
<PredefinedData>
<Item id="aaa">
    <Name>РеализуемыеАктивы</Name>
    <Code>00055</Code>
    <Description>Реализуемые активы</Description>
    <Type>
        <v8:Type xmlns:d4p1="http://v8.1c.ru/8.1/data/enterprise/current-config">d4p1:CatalogRef.Номенклатура</v8:Type>
    </Type>
    <IsFolder>false</IsFolder>
</Item>
</PredefinedData>
</ChartOfCharacteristicTypes>
"""


def _build_bsl_live_fixture(workspace_root):
    (workspace_root / "Configuration.xml").write_text(CF_MAIN_XML, encoding="utf-8")

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

    common_module = workspace_root / "CommonModules" / "CommonServer" / "Ext" / "Module.bsl"
    common_module.parent.mkdir(parents=True)
    common_module.write_text(
        "Процедура ПодготовитьДвижения() Экспорт\n"
        "КонецПроцедуры\n",
        encoding="utf-8",
    )

    return object_module.relative_to(workspace_root).as_posix()


def _apply_index_only_changes(workspace_root):
    object_module = workspace_root / "Documents" / "SalesOrder" / "Ext" / "ObjectModule.bsl"
    object_module.write_text(
        object_module.read_text(encoding="utf-8")
        + "\n"
        + "Процедура ДопПроверка()\n"
        + "    ПодготовитьДвижения();\n"
        + "КонецПроцедуры\n",
        encoding="utf-8",
    )


def _add_advanced_cf_metadata(workspace_root):
    document_xml = workspace_root / "Documents" / "SalesOrder" / "Ext" / "Document.xml"
    document_xml.write_text(_build_document_metadata_xml(), encoding="utf-8")

    chart_root = workspace_root / "ChartsOfCharacteristicTypes" / "CostTypes" / "Ext"
    chart_root.mkdir(parents=True, exist_ok=True)
    (chart_root / "Predefined.xml").write_text(_build_predefined_xml(), encoding="utf-8")


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


def test_runtime_supports_bsl_live_helper_flow_without_prebuilt_index(tmp_path):
    workspace_root = tmp_path / "bsl-live"
    workspace_root.mkdir()
    object_module_path = _build_bsl_live_fixture(workspace_root)
    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter()]))

    started = runtime.rlm_start(root_path=str(workspace_root), query="trace posting logic")
    modules = runtime.rlm_execute(started.session_id, "bsl_find_modules", {"name": "SalesOrder"})
    procedures = runtime.rlm_execute(
        started.session_id,
        "bsl_extract_procedures",
        {"path": object_module_path},
    )
    procedure_body = runtime.rlm_execute(
        started.session_id,
        "bsl_read_procedure",
        {"path": object_module_path, "name": "ОбработкаПроведения"},
    )

    assert not (workspace_root / ".rlm" / "indexes" / "bsl" / "manifest.json").exists()
    assert "bsl_find_modules" in started.helper_names
    assert "bsl_extract_procedures" in started.helper_names
    assert "bsl_read_procedure" in started.helper_names
    assert started.strategy.startswith("bsl:trace posting logic")
    assert "LIVE WORKFLOW" in started.strategy
    assert {item["module_type"] for item in modules.result} == {"ManagerModule", "ObjectModule"}
    assert procedures.result[0]["name"] == "ОбработкаПроведения"
    assert "ПодготовитьДвижения();" in procedure_body.result


def test_runtime_surfaces_advanced_bsl_helpers_via_adapter_layer(tmp_path):
    workspace_root = tmp_path / "bsl-advanced"
    workspace_root.mkdir()
    _build_bsl_live_fixture(workspace_root)
    _add_advanced_cf_metadata(workspace_root)
    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter()]))

    started = runtime.rlm_start(root_path=str(workspace_root), query="inspect advanced metadata")
    advanced_features = runtime.rlm_execute(started.session_id, "bsl_advanced_features")
    attrs = runtime.rlm_execute(started.session_id, "bsl_find_attributes", {"name": "Организация"})
    predefined = runtime.rlm_execute(started.session_id, "bsl_find_predefined", {"name": "РеализуемыеАктивы"})

    assert "bsl_advanced_features" in started.helper_names
    assert "bsl_find_attributes" in started.helper_names
    assert "bsl_find_predefined" in started.helper_names
    assert "LIVE WORKFLOW" in started.strategy
    assert advanced_features.result == ["object_attributes", "predefined_items"]
    assert attrs.result == [
        {
            "object_name": "SalesOrder",
            "category": "Documents",
            "attr_name": "Организация",
            "attr_synonym": "Организация",
            "attr_type": ["CatalogRef.Организации"],
            "attr_kind": "attribute",
            "ts_name": None,
        }
    ]
    assert predefined.result == [
        {
            "object_name": "CostTypes",
            "category": "ChartsOfCharacteristicTypes",
            "item_name": "РеализуемыеАктивы",
            "item_synonym": "Реализуемые активы",
            "item_code": "00055",
            "types": ["CatalogRef.Номенклатура"],
            "is_folder": False,
        }
    ]


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


def test_runtime_prefers_indexed_bsl_workflow_after_prebuilt_build(tmp_path):
    workspace_root = tmp_path / "bsl-indexed"
    workspace_root.mkdir()
    object_module_path = _build_bsl_live_fixture(workspace_root)
    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter()]))

    built = runtime.rlm_index(IndexLifecycleAction.BUILD, root_path=str(workspace_root))
    _apply_index_only_changes(workspace_root)
    started = runtime.rlm_start(root_path=str(workspace_root), query="trace posting logic")
    procedures = runtime.rlm_execute(
        started.session_id,
        "bsl_extract_procedures",
        {"path": object_module_path},
    )
    callers = runtime.rlm_execute(
        started.session_id,
        "bsl_find_callers",
        {"name": "ПодготовитьДвижения"},
    )

    assert built.status is IndexOperationStatus.COMPLETED
    assert "bsl_find_callers" in started.helper_names
    assert "INDEXED WORKFLOW" in started.strategy
    assert [item["name"] for item in procedures.result] == ["ОбработкаПроведения"]
    assert callers.result["_meta"]["total_callers"] == 1


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
    assert "bsl_find_attributes" not in started.helper_names
    assert "bsl_find_predefined" not in started.helper_names
    assert first.result["error"] is None
    assert "src/main.py" in first.result["stdout"]
    assert "VALUE = 7" in first.result["stdout"]
    assert second.result["stdout"].strip() == "1"


def test_runtime_routes_go_workflows_through_shared_runtime_and_lifecycle(tmp_path):
    workspace_root = tmp_path / "go"
    workspace_root.mkdir()
    fixture = build_go_fixture(workspace_root)

    workspace_registry = InMemoryWorkspaceRegistry()
    workspace_registry.register(
        "shop",
        workspace_root,
        display_name="Shop",
        adapter_hint="go",
    )
    runtime = CoreRuntime(
        adapter_registry=AdapterRegistry([GoRepositoryAdapter()]),
        workspace_registry=workspace_registry,
    )

    started = runtime.rlm_start(workspace_id="shop", query="inspect handler flow")
    packages = runtime.rlm_execute(started.session_id, "go_list_packages")
    declarations = runtime.rlm_execute(
        started.session_id,
        "go_extract_declarations",
        {"path": fixture["service_file"]},
    )
    serve_http = runtime.rlm_execute(
        started.session_id,
        "go_read_declaration",
        {"path": fixture["service_file"], "name": "ServeHTTP"},
    )
    built = runtime.rlm_index(IndexLifecycleAction.BUILD, workspace_id="shop")

    assert started.workspace.workspace_id == "shop"
    assert started.adapter_id == "go"
    assert started.capabilities.supported_actions == frozenset()
    assert sorted(started.capabilities.adapter_features) == ["declarations", "imports", "packages"]
    assert "go_list_packages" in started.helper_names
    assert "go_extract_declarations" in started.helper_names
    assert started.strategy.startswith("go:inspect handler flow")
    assert "LIVE WORKFLOW" in started.strategy
    assert {item["package"] for item in packages.result} == {"main", "service", "storage"}
    assert [item["name"] for item in declarations.result] == ["Config", "Service", "NewService", "ServeHTTP"]
    assert 'fmt.Fprintf(w, "ok")' in serve_http.result
    assert built.status is IndexOperationStatus.UNSUPPORTED
    assert built.details["supported_actions"] == []


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
