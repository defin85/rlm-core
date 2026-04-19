from __future__ import annotations

import io
import json

from rlm_core.cli import run_cli
from rlm_core.evals import run_default_quality_evals


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


def _build_plain_quality_fixture(workspace_root):
    source_dir = workspace_root / "src"
    source_dir.mkdir(parents=True)
    (source_dir / "main.py").write_text("VALUE = 7\n", encoding="utf-8")


def _build_bsl_quality_fixture(workspace_root):
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

    document_xml = workspace_root / "Documents" / "SalesOrder" / "Ext" / "Document.xml"
    document_xml.write_text(_build_document_metadata_xml(), encoding="utf-8")

    chart_root = workspace_root / "ChartsOfCharacteristicTypes" / "CostTypes" / "Ext"
    chart_root.mkdir(parents=True, exist_ok=True)
    (chart_root / "ChartOfCharacteristicTypes.xml").write_text(_build_chart_metadata_xml(), encoding="utf-8")
    (chart_root / "Predefined.xml").write_text(_build_predefined_xml(), encoding="utf-8")


def test_quality_eval_runner_reports_repeatable_metrics(tmp_path):
    plain_root = tmp_path / "plain"
    plain_root.mkdir()
    _build_plain_quality_fixture(plain_root)

    bsl_root = tmp_path / "bsl"
    bsl_root.mkdir()
    _build_bsl_quality_fixture(bsl_root)

    report = run_default_quality_evals(plain_root=plain_root, bsl_root=bsl_root)
    payload = report.to_payload()
    cases = {item["name"]: item for item in payload["cases"]}

    assert report.passed is True
    assert payload["response_type"] == "quality_evals"
    assert payload["case_count"] == 3
    assert set(cases) == {
        "generic_runtime_roundtrip",
        "bsl_live_runtime_flow",
        "bsl_indexed_runtime_flow",
    }
    assert all(case["passed"] for case in cases.values())
    assert cases["generic_runtime_roundtrip"]["metrics"]["helper_call_count"] == 2
    assert cases["bsl_live_runtime_flow"]["checks"]["strategy_tokens_present"] is True
    assert cases["bsl_indexed_runtime_flow"]["checks"]["index_wait_completed"] is True
    assert cases["bsl_indexed_runtime_flow"]["metrics"]["helper_call_count"] == 1


def test_cli_runs_quality_evals_with_stable_json_envelope(tmp_path):
    plain_root = tmp_path / "plain"
    plain_root.mkdir()
    _build_plain_quality_fixture(plain_root)

    bsl_root = tmp_path / "bsl"
    bsl_root.mkdir()
    _build_bsl_quality_fixture(bsl_root)

    stdout = io.StringIO()
    exit_code = run_cli(
        ["evals", "--plain-root", str(plain_root), "--bsl-root", str(bsl_root)],
        stdout=stdout,
    )
    payload = json.loads(stdout.getvalue())

    assert exit_code == 0
    assert payload["tool_name"] == "rlm_quality_evals"
    assert payload["ok"] is True
    assert payload["data"]["response_type"] == "quality_evals"
    assert payload["data"]["case_count"] == 3
    assert all(case["passed"] for case in payload["data"]["cases"])
