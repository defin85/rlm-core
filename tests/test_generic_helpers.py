from __future__ import annotations

from rlm_core.adapters import AdapterRegistry
from rlm_core.adapters.bsl import BslRepositoryAdapter
from rlm_core.runtime import CoreRuntime
from rlm_core.runtime.helpers import make_runtime_helpers

CF_MAIN_XML = """\
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses">
  <Configuration>
    <Properties>
      <Name>Accounting</Name>
    </Properties>
  </Configuration>
</MetaDataObject>
"""


def test_make_runtime_helpers_exposes_generic_baseline(tmp_path):
    workspace_root = tmp_path / "repo"
    workspace_root.mkdir()

    helpers, _resolve_safe = make_runtime_helpers(workspace_root)

    assert set(helpers) == {
        "find_files",
        "glob_files",
        "grep",
        "grep_read",
        "grep_summary",
        "read_file",
        "read_files",
        "tree",
    }


def test_generic_helpers_support_compact_exploration_workflow(tmp_path):
    workspace_root = tmp_path / "repo"
    service_dir = workspace_root / "src" / "services"
    service_dir.mkdir(parents=True)
    (workspace_root / "README.md").write_text("# demo\n", encoding="utf-8")
    (service_dir / "billing.py").write_text(
        "class BillingService:\n"
        "    def charge(self):\n"
        "        return 'paid'\n",
        encoding="utf-8",
    )
    (service_dir / "audit.py").write_text(
        "def record_charge(event):\n"
        "    return event\n",
        encoding="utf-8",
    )

    runtime = CoreRuntime()
    started = runtime.rlm_start(root_path=str(workspace_root), query="trace billing")
    executed = runtime.rlm_execute(
        started.session_id,
        code=(
            "print(tree('.', max_depth=2))\n"
            "matches = find_files('billing')\n"
            "print(matches[0])\n"
            "print(read_file(matches[0]).strip())\n"
            "print(grep_summary('charge', 'src'))\n"
            "excerpt = grep_read('BillingService', 'src', context_lines=1)\n"
            "print(excerpt['summary'])\n"
            "print(excerpt['files']['src/services/billing.py'])\n"
        ),
    )

    assert started.adapter_id == "generic"
    assert "WORKFLOW" in started.strategy
    assert "find_files" in started.helper_names
    assert executed.result["error"] is None
    assert "src/services" in executed.result["stdout"]
    assert "src/services/billing.py" in executed.result["stdout"]
    assert "class BillingService" in executed.result["stdout"]
    assert "matches in 2 files" in executed.result["stdout"]
    assert "L1: class BillingService:" in executed.result["stdout"]


def test_read_file_shapes_large_outputs_and_supports_windowing(tmp_path):
    workspace_root = tmp_path / "repo"
    workspace_root.mkdir()
    large_file = workspace_root / "huge.txt"
    large_file.write_text("".join(f"line {index}\n" for index in range(1, 401)), encoding="utf-8")

    helpers, _resolve_safe = make_runtime_helpers(workspace_root)

    excerpt = helpers["read_file"]("huge.txt")
    window = helpers["read_file"]("huge.txt", start_line=150, max_lines=3)

    assert "... [excerpt:" in excerpt
    assert "line 1" in excerpt
    assert "line 220" not in excerpt
    assert "line 150" in window
    assert "line 152" in window
    assert "line 153" not in window


def test_runtime_keeps_generic_helpers_when_adapter_specific_helpers_exist(tmp_path):
    workspace_root = tmp_path / "bsl"
    workspace_root.mkdir()
    (workspace_root / "Configuration.xml").write_text(CF_MAIN_XML, encoding="utf-8")

    runtime = CoreRuntime(adapter_registry=AdapterRegistry([BslRepositoryAdapter()]))
    started = runtime.rlm_start(root_path=str(workspace_root), query="inspect repo")

    assert started.adapter_id == "bsl"
    assert "bsl_repo_details" in started.helper_names
    assert "read_file" in started.helper_names
    assert "grep_read" in started.helper_names
    assert "find_files" in started.helper_names
