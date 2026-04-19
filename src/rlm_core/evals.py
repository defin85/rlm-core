"""Repeatable quality evaluation workflows for runtime and lifecycle claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

from rlm_core.index.contracts import IndexLifecycleAction
from rlm_core.public_api import (
    PublicApiSurface,
    PublicEndRequest,
    PublicExecuteRequest,
    PublicIndexRequest,
    PublicStartRequest,
    PublicWaitForIndexJobRequest,
)


class QualityEvalError(RuntimeError):
    """Raised when a public runtime call cannot complete during a quality eval."""


@dataclass(frozen=True, slots=True)
class EvalBudget:
    """Upper bounds for a measurable quality-eval case."""

    max_start_ms: float | None = None
    max_execute_ms: float | None = None
    max_end_ms: float | None = None
    max_index_request_ms: float | None = None
    max_index_wait_ms: float | None = None
    max_index_info_ms: float | None = None
    max_helper_calls: int | None = None
    max_helper_elapsed_ms: float | None = None
    max_stdout_chars: int | None = None


@dataclass(frozen=True, slots=True)
class QualityEvalCase:
    """Definition of one repeatable runtime quality evaluation."""

    name: str
    root_path: str
    query: str
    code: str
    expected_adapter_id: str
    required_session_helpers: tuple[str, ...] = ()
    required_invoked_helpers: tuple[str, ...] = ()
    required_strategy_tokens: tuple[str, ...] = ()
    required_stdout_tokens: tuple[str, ...] = ()
    build_index: bool = False
    background_index: bool = False
    budget: EvalBudget = field(default_factory=EvalBudget)

    def __post_init__(self) -> None:
        object.__setattr__(self, "root_path", str(Path(self.root_path)))
        object.__setattr__(self, "required_session_helpers", tuple(self.required_session_helpers))
        object.__setattr__(self, "required_invoked_helpers", tuple(self.required_invoked_helpers))
        object.__setattr__(self, "required_strategy_tokens", tuple(self.required_strategy_tokens))
        object.__setattr__(self, "required_stdout_tokens", tuple(self.required_stdout_tokens))


@dataclass(frozen=True, slots=True)
class QualityEvalCaseResult:
    """Serializable outcome of one quality-eval case."""

    name: str
    root_path: str
    passed: bool
    adapter_id: str | None
    checks: dict[str, bool]
    failures: tuple[str, ...]
    metrics: dict[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", dict(self.checks))
        object.__setattr__(self, "failures", tuple(self.failures))
        object.__setattr__(self, "metrics", dict(self.metrics))

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "root_path": self.root_path,
            "passed": self.passed,
            "adapter_id": self.adapter_id,
            "checks": dict(self.checks),
            "failures": list(self.failures),
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True, slots=True)
class QualityEvalSuiteResult:
    """Serializable quality-eval suite summary."""

    passed: bool
    cases: tuple[QualityEvalCaseResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cases", tuple(self.cases))

    def to_payload(self) -> dict[str, object]:
        return {
            "response_type": "quality_evals",
            "passed": self.passed,
            "case_count": len(self.cases),
            "cases": [case.to_payload() for case in self.cases],
        }


@dataclass(frozen=True, slots=True)
class QualityEvalCliResponse:
    """CLI-style envelope for quality-eval runs."""

    result: QualityEvalSuiteResult

    @property
    def ok(self) -> bool:
        return self.result.passed

    def to_payload(self) -> dict[str, object]:
        return {
            "tool_name": "rlm_quality_evals",
            "ok": self.ok,
            "data": self.result.to_payload(),
        }


def build_default_quality_eval_cases(*, plain_root: str | Path, bsl_root: str | Path) -> tuple[QualityEvalCase, ...]:
    """Return the default quality gate bundle used for release-candidate checks."""

    generic_code = (
        "files = glob_files('**/*.py')\n"
        "print(files[0])\n"
        "print(read_file(files[0]).strip())\n"
    )
    bsl_live_code = (
        "modules = bsl_find_modules('SalesOrder')\n"
        "object_path = [item['path'] for item in modules if item['module_type'] == 'ObjectModule'][0]\n"
        "print(object_path)\n"
        "print(len(bsl_extract_procedures(object_path)))\n"
        "print('ПодготовитьДвижения' in bsl_read_procedure(object_path, 'ОбработкаПроведения'))\n"
    )
    bsl_indexed_code = (
        "callers = bsl_find_callers('ПодготовитьДвижения')\n"
        "print(callers['_meta']['total_callers'])\n"
    )
    return (
        QualityEvalCase(
            name="generic_runtime_roundtrip",
            root_path=str(Path(plain_root)),
            query="inspect python sources",
            code=generic_code,
            expected_adapter_id="generic",
            required_session_helpers=("glob_files", "read_file"),
            required_invoked_helpers=("glob_files", "read_file"),
            required_strategy_tokens=("generic:inspect python sources", "DISCOVER", "SEARCH"),
            required_stdout_tokens=("src/main.py", "VALUE = 7"),
            budget=EvalBudget(
                max_start_ms=5_000,
                max_execute_ms=1_000,
                max_end_ms=1_000,
                max_helper_calls=2,
                max_helper_elapsed_ms=500,
                max_stdout_chars=256,
            ),
        ),
        QualityEvalCase(
            name="bsl_live_runtime_flow",
            root_path=str(Path(bsl_root)),
            query="trace posting logic",
            code=bsl_live_code,
            expected_adapter_id="bsl",
            required_session_helpers=("bsl_find_modules", "bsl_extract_procedures", "bsl_read_procedure"),
            required_invoked_helpers=("bsl_find_modules", "bsl_extract_procedures", "bsl_read_procedure"),
            required_strategy_tokens=("bsl:trace posting logic", "LIVE WORKFLOW"),
            required_stdout_tokens=("Documents/SalesOrder/Ext/ObjectModule.bsl", "1", "True"),
            budget=EvalBudget(
                max_start_ms=5_000,
                max_execute_ms=1_500,
                max_end_ms=1_000,
                max_helper_calls=3,
                max_helper_elapsed_ms=1_000,
                max_stdout_chars=256,
            ),
        ),
        QualityEvalCase(
            name="bsl_indexed_runtime_flow",
            root_path=str(Path(bsl_root)),
            query="trace posting logic",
            code=bsl_indexed_code,
            expected_adapter_id="bsl",
            required_session_helpers=("bsl_find_callers",),
            required_invoked_helpers=("bsl_find_callers",),
            required_strategy_tokens=("bsl:trace posting logic", "INDEXED WORKFLOW"),
            required_stdout_tokens=("1",),
            build_index=True,
            background_index=True,
            budget=EvalBudget(
                max_start_ms=5_000,
                max_execute_ms=1_500,
                max_end_ms=1_000,
                max_index_request_ms=2_000,
                max_index_wait_ms=5_000,
                max_index_info_ms=2_000,
                max_helper_calls=1,
                max_helper_elapsed_ms=1_000,
                max_stdout_chars=128,
            ),
        ),
    )


def run_default_quality_evals(
    *,
    plain_root: str | Path,
    bsl_root: str | Path,
    surface: PublicApiSurface | None = None,
) -> QualityEvalSuiteResult:
    """Run the default repeatable quality suite against plain and BSL fixtures."""

    return run_quality_eval_suite(
        build_default_quality_eval_cases(plain_root=plain_root, bsl_root=bsl_root),
        surface=surface,
    )


def run_quality_eval_suite(
    cases: tuple[QualityEvalCase, ...] | list[QualityEvalCase],
    *,
    surface: PublicApiSurface | None = None,
) -> QualityEvalSuiteResult:
    """Run a repeatable runtime/lifecycle quality suite."""

    api = surface or PublicApiSurface()
    results = tuple(_run_quality_eval_case(api, case) for case in cases)
    return QualityEvalSuiteResult(passed=all(case.passed for case in results), cases=results)


def _run_quality_eval_case(surface: PublicApiSurface, case: QualityEvalCase) -> QualityEvalCaseResult:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    metrics: dict[str, object] = {}
    adapter_id: str | None = None
    session_id: str | None = None

    try:
        if case.build_index:
            index_data, index_elapsed_ms = _timed_call(
                lambda: _unwrap_response(
                    surface.rlm_index(
                        PublicIndexRequest(
                            action=IndexLifecycleAction.BUILD,
                            root_path=case.root_path,
                            background=case.background_index,
                        )
                    ),
                    "rlm_index(build)",
                )
            )
            metrics["index_request_ms"] = index_elapsed_ms
            checks["index_request_status"] = index_data["status"] in {"started", "completed"}
            if not checks["index_request_status"]:
                failures.append(f"Unexpected index request status: {index_data['status']}")

            if case.background_index:
                job_id = index_data["details"]["job_id"]
                wait_data, wait_elapsed_ms = _timed_call(
                    lambda: _unwrap_response(
                        surface.rlm_wait_for_index_job(
                            PublicWaitForIndexJobRequest(job_id=job_id, timeout_seconds=5.0)
                        ),
                        "rlm_wait_for_index_job",
                    )
                )
                metrics["index_wait_ms"] = wait_elapsed_ms
                checks["index_wait_completed"] = wait_data["status"] == "completed"
                if not checks["index_wait_completed"]:
                    failures.append(f"Background index did not complete: {wait_data['status']}")

            info_data, info_elapsed_ms = _timed_call(
                lambda: _unwrap_response(
                    surface.rlm_index(
                        PublicIndexRequest(
                            action=IndexLifecycleAction.INFO,
                            root_path=case.root_path,
                        )
                    ),
                    "rlm_index(info)",
                )
            )
            metrics["index_info_ms"] = info_elapsed_ms
            checks["index_available"] = bool(info_data["available"])
            if not checks["index_available"]:
                failures.append("Index info did not report an available index")

        start_data, start_elapsed_ms = _timed_call(
            lambda: _unwrap_response(
                surface.rlm_start(
                    PublicStartRequest(
                        root_path=case.root_path,
                        query=case.query,
                    )
                ),
                "rlm_start",
            )
        )
        session_id = start_data["session_id"]
        adapter_id = start_data["adapter_id"]
        metrics["start_ms"] = start_elapsed_ms
        checks["expected_adapter_id"] = adapter_id == case.expected_adapter_id
        if not checks["expected_adapter_id"]:
            failures.append(f"Expected adapter {case.expected_adapter_id}, got {adapter_id}")

        helper_names = set(start_data["helper_names"])
        checks["session_helpers_available"] = all(name in helper_names for name in case.required_session_helpers)
        if not checks["session_helpers_available"]:
            missing = sorted(set(case.required_session_helpers) - helper_names)
            failures.append(f"Missing session helpers: {missing}")

        strategy = start_data["strategy"]
        checks["strategy_tokens_present"] = all(token in strategy for token in case.required_strategy_tokens)
        if not checks["strategy_tokens_present"]:
            failures.append("Strategy text is missing one or more required workflow tokens")

        execute_data, execute_elapsed_ms = _timed_call(
            lambda: _unwrap_response(
                surface.rlm_execute(
                    PublicExecuteRequest(
                        session_id=session_id,
                        code=case.code,
                    )
                ),
                "rlm_execute",
            )
        )
        metrics["execute_ms"] = execute_elapsed_ms

        execute_result = execute_data["result"]
        helper_calls = execute_result["helper_calls"]
        stdout = execute_result["stdout"]
        metrics["helper_call_count"] = len(helper_calls)
        metrics["helper_elapsed_ms"] = round(sum(item["elapsed"] for item in helper_calls) * 1000, 3)
        metrics["stdout_chars"] = len(stdout)

        checks["sandbox_execute_ok"] = execute_result["error"] is None
        if not checks["sandbox_execute_ok"]:
            failures.append(f"Sandbox execution failed: {execute_result['error']}")

        invoked_helpers = {item["name"] for item in helper_calls}
        checks["invoked_helpers_present"] = all(name in invoked_helpers for name in case.required_invoked_helpers)
        if not checks["invoked_helpers_present"]:
            missing = sorted(set(case.required_invoked_helpers) - invoked_helpers)
            failures.append(f"Missing helper invocations: {missing}")

        checks["stdout_tokens_present"] = all(token in stdout for token in case.required_stdout_tokens)
        if not checks["stdout_tokens_present"]:
            failures.append("Sandbox stdout is missing one or more required tokens")

        end_data, end_elapsed_ms = _timed_call(
            lambda: _unwrap_response(
                surface.rlm_end(PublicEndRequest(session_id=session_id)),
                "rlm_end",
            )
        )
        metrics["end_ms"] = end_elapsed_ms
        checks["end_adapter_matches_start"] = end_data["adapter_id"] == adapter_id
        if not checks["end_adapter_matches_start"]:
            failures.append("Session end response returned a different adapter than session start")
    except Exception as exc:
        failures.append(str(exc))
        checks.setdefault("runtime_call_completed", False)
    else:
        checks["runtime_call_completed"] = True
    finally:
        if session_id is not None and not checks.get("end_adapter_matches_start", False):
            try:
                surface.rlm_end(PublicEndRequest(session_id=session_id))
            except Exception:
                pass

    _apply_budget("start_ms", metrics, case.budget.max_start_ms, checks, failures)
    _apply_budget("execute_ms", metrics, case.budget.max_execute_ms, checks, failures)
    _apply_budget("end_ms", metrics, case.budget.max_end_ms, checks, failures)
    _apply_budget("index_request_ms", metrics, case.budget.max_index_request_ms, checks, failures)
    _apply_budget("index_wait_ms", metrics, case.budget.max_index_wait_ms, checks, failures)
    _apply_budget("index_info_ms", metrics, case.budget.max_index_info_ms, checks, failures)
    _apply_budget("helper_call_count", metrics, case.budget.max_helper_calls, checks, failures)
    _apply_budget("helper_elapsed_ms", metrics, case.budget.max_helper_elapsed_ms, checks, failures)
    _apply_budget("stdout_chars", metrics, case.budget.max_stdout_chars, checks, failures)

    return QualityEvalCaseResult(
        name=case.name,
        root_path=case.root_path,
        passed=not failures and all(checks.values()),
        adapter_id=adapter_id,
        checks=checks,
        failures=tuple(failures),
        metrics=metrics,
    )


def _unwrap_response(response, step: str) -> dict[str, object]:
    payload = response.to_payload()
    if not response.ok:
        error = payload.get("error") or {}
        code = error.get("code", "unknown_error")
        message = error.get("message", "Unknown failure")
        raise QualityEvalError(f"{step} failed [{code}]: {message}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise QualityEvalError(f"{step} returned a non-dict payload")
    return data


def _timed_call(callback) -> tuple[dict[str, object], float]:
    started_at = perf_counter()
    data = callback()
    return data, round((perf_counter() - started_at) * 1000, 3)


def _apply_budget(
    metric_name: str,
    metrics: dict[str, object],
    limit: float | int | None,
    checks: dict[str, bool],
    failures: list[str],
) -> None:
    if limit is None or metric_name not in metrics:
        return
    value = metrics[metric_name]
    if not isinstance(value, (int, float)):
        return
    check_name = f"{metric_name}_within_budget"
    checks[check_name] = value <= limit
    if not checks[check_name]:
        failures.append(f"{metric_name} exceeded budget: {value} > {limit}")


__all__ = [
    "EvalBudget",
    "QualityEvalCase",
    "QualityEvalCaseResult",
    "QualityEvalCliResponse",
    "QualityEvalSuiteResult",
    "build_default_quality_eval_cases",
    "run_default_quality_evals",
    "run_quality_eval_suite",
]
