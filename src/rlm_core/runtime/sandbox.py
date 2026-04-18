"""Persistent read-only Python sandbox for the runtime walking skeleton."""

from __future__ import annotations

import builtins
import contextlib
import functools
import io
import pathlib
import signal
import threading
import time as time_module
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

ALLOWED_MODULES = frozenset(
    {
        "collections",
        "difflib",
        "fnmatch",
        "functools",
        "itertools",
        "json",
        "math",
        "operator",
        "pathlib",
        "re",
        "statistics",
        "string",
        "textwrap",
    }
)

BLOCKED_BUILTINS = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "exit",
        "input",
        "quit",
    }
)


@dataclass(frozen=True, slots=True)
class HelperCall:
    """Instrumentation record for helper invocations made inside the sandbox."""

    name: str
    elapsed: float


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    """Result of executing code inside the persistent sandbox."""

    stdout: str
    error: str | None
    variables: tuple[str, ...]
    helper_calls: tuple[HelperCall, ...]


def _make_restricted_import(allowed: frozenset[str]):
    original_import = builtins.__import__

    def restricted_import(name, *args, **kwargs):
        top_level = name.split(".")[0]
        if name not in allowed and top_level not in allowed:
            raise ImportError(f"Import of '{name}' is not allowed in the sandbox")
        return original_import(name, *args, **kwargs)

    return restricted_import


class RuntimeSandbox:
    """Persistent Python sandbox with a read-only repository-scoped helper set."""

    def __init__(
        self,
        *,
        base_path: str | pathlib.Path,
        helpers: dict[str, Callable[..., object]],
        resolve_safe: Callable[[str], pathlib.Path],
        max_output_chars: int = 15_000,
        execution_timeout_seconds: int = 30,
    ) -> None:
        self._base_path = pathlib.Path(base_path).expanduser().resolve()
        self._resolve_safe = resolve_safe
        self._max_output_chars = max_output_chars
        self._execution_timeout_seconds = execution_timeout_seconds
        self._helper_calls: list[HelperCall] = []
        self._namespace: dict[str, object] = {}
        self._helpers = self._wrap_helpers(helpers)
        self._setup_namespace()

    @property
    def helpers(self) -> dict[str, object]:
        """Return helper callables registered in the sandbox namespace."""
        return dict(self._helpers)

    def execute(self, code: str) -> SandboxExecutionResult:
        self._helper_calls.clear()
        stdout_capture = io.StringIO()
        error = None

        try:
            with contextlib.redirect_stdout(stdout_capture):
                with self._execution_timeout():
                    exec(code, self._namespace)
        except Exception:
            error = self._add_error_hints(traceback.format_exc())

        stdout = stdout_capture.getvalue()
        if len(stdout) > self._max_output_chars:
            stdout = stdout[: self._max_output_chars] + "\n... [output truncated]"

        return SandboxExecutionResult(
            stdout=stdout,
            error=error,
            variables=tuple(self.list_variables()),
            helper_calls=tuple(self._helper_calls),
        )

    def list_variables(self) -> list[str]:
        return sorted(name for name in self._namespace if not name.startswith("_") and name != "__builtins__")

    def _setup_namespace(self) -> None:
        safe_builtins = {name: value for name, value in builtins.__dict__.items() if name not in BLOCKED_BUILTINS}
        safe_builtins["__import__"] = _make_restricted_import(ALLOWED_MODULES)

        original_open = builtins.open

        def restricted_open(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                raise PermissionError(f"Write access denied in sandbox (mode='{mode}')")
            if isinstance(file, int):
                raise PermissionError("File descriptor access is not allowed in sandbox")
            safe_path = self._resolve_safe(str(pathlib.Path(file)))
            return original_open(safe_path, mode, *args, **kwargs)

        safe_builtins["open"] = restricted_open

        self._namespace["__builtins__"] = safe_builtins
        self._namespace["Path"] = pathlib.Path
        self._namespace["root_path"] = self._base_path
        self._namespace.update(self._helpers)

    def _wrap_helpers(self, helpers: dict[str, Callable[..., object]]) -> dict[str, Callable[..., object]]:
        wrapped: dict[str, Callable[..., object]] = {}
        for name, helper in helpers.items():
            if not callable(helper):
                continue

            @functools.wraps(helper)
            def timed(*args, _helper=helper, _name=name, **kwargs):
                started_at = time_module.monotonic()
                try:
                    return _helper(*args, **kwargs)
                finally:
                    self._helper_calls.append(HelperCall(_name, time_module.monotonic() - started_at))

            wrapped[name] = timed
        return wrapped

    @contextmanager
    def _execution_timeout(self):
        if self._execution_timeout_seconds <= 0:
            yield
            return

        if threading.current_thread() is threading.main_thread() and hasattr(signal, "SIGALRM"):

            def raise_timeout(_signum, _frame):
                raise TimeoutError(f"Execution timed out after {self._execution_timeout_seconds} seconds")

            previous_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, raise_timeout)
            signal.setitimer(signal.ITIMER_REAL, self._execution_timeout_seconds)
            try:
                yield
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)
            return

        import ctypes

        timed_out = threading.Event()
        target_tid = threading.current_thread().ident

        def timeout_watchdog():
            timed_out.set()
            if target_tid is not None:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(target_tid), ctypes.py_object(TimeoutError))

        timer = threading.Timer(self._execution_timeout_seconds, timeout_watchdog)
        timer.daemon = True
        timer.start()
        try:
            yield
        finally:
            timer.cancel()
            if timed_out.is_set():
                raise TimeoutError(f"Execution timed out after {self._execution_timeout_seconds} seconds")

    @staticmethod
    def _add_error_hints(error: str) -> str:
        hints: list[str] = []
        if "NameError" in error:
            hints.append("HINT: Variables persist between rlm_execute calls; use print() to inspect current values.")
        if "ImportError" in error and "allowed" in error:
            hints.append("HINT: Only a small standard-library subset is allowed in the walking skeleton sandbox.")
        if "PermissionError" in error:
            hints.append("HINT: The walking skeleton sandbox is read-only and blocks writes outside repository helpers.")
        if hints:
            return error.rstrip() + "\n\n" + "\n".join(hints)
        return error
