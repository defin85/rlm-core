"""CLI surface over the stable public API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence, TextIO

from rlm_core.index.contracts import IndexLifecycleAction
from rlm_core.public_api import (
    PublicApiSurface,
    PublicEndRequest,
    PublicExecuteRequest,
    PublicIndexJobRequest,
    PublicIndexRequest,
    PublicStartRequest,
    PublicToolResponse,
    PublicWaitForIndexJobRequest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rlm-core", description="Stable public CLI for rlm-core")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("projects", help="List registered workspaces")

    start_parser = subparsers.add_parser("start", help="Start a runtime session")
    _add_workspace_args(start_parser)
    start_parser.add_argument("--query", default="", help="Runtime query hint")

    execute_parser = subparsers.add_parser("execute", help="Execute a helper or sandbox code")
    execute_parser.add_argument("session_id", help="Runtime session ID")
    execute_parser.add_argument("--helper", help="Helper name to invoke")
    execute_parser.add_argument("--arguments-json", help="JSON payload passed as helper arguments")
    execute_parser.add_argument("--code", help="Sandbox code to execute")

    end_parser = subparsers.add_parser("end", help="End a runtime session")
    end_parser.add_argument("session_id", help="Runtime session ID")

    index_parser = subparsers.add_parser("index", help="Run an index lifecycle action")
    index_parser.add_argument(
        "action",
        choices=[action.value for action in IndexLifecycleAction],
        help="Lifecycle action",
    )
    _add_workspace_args(index_parser)
    index_parser.add_argument("--background", action="store_true", help="Run build/update in background")
    index_parser.add_argument("--confirm", action="store_true", help="Acknowledge a confirm-only mutation policy")

    index_job_parser = subparsers.add_parser("index-job", help="Read background index job status")
    index_job_parser.add_argument("job_id", help="Index job ID")

    wait_job_parser = subparsers.add_parser("wait-job", help="Wait for a background index job")
    wait_job_parser.add_argument("job_id", help="Index job ID")
    wait_job_parser.add_argument("--timeout", type=float, default=None, help="Timeout in seconds")

    return parser


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    surface: PublicApiSurface | None = None,
    stdout: TextIO | None = None,
) -> int:
    parser = build_parser()
    out = stdout or sys.stdout
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # pragma: no cover - argparse already owns formatting
        return int(exc.code)

    if args.command is None:
        parser.print_help(file=out)
        return 2

    api = surface or PublicApiSurface()
    response = _dispatch(api, args)
    out.write(json.dumps(response.to_payload(), ensure_ascii=False, sort_keys=True))
    out.write("\n")
    return 0 if response.ok else 1


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(argv)


def _dispatch(api: PublicApiSurface, args: argparse.Namespace) -> PublicToolResponse:
    if args.command == "projects":
        return api.rlm_projects()
    if args.command == "start":
        return api.rlm_start(
            PublicStartRequest(
                workspace_id=args.workspace_id,
                root_path=args.root_path,
                adapter_id=args.adapter_id,
                display_name=args.display_name,
                metadata=_parse_metadata_args(args.metadata),
                query=args.query,
            )
        )
    if args.command == "execute":
        return api.rlm_execute(
            PublicExecuteRequest(
                session_id=args.session_id,
                helper_name=args.helper,
                arguments=_parse_json_argument(args.arguments_json),
                code=args.code,
            )
        )
    if args.command == "end":
        return api.rlm_end(PublicEndRequest(session_id=args.session_id))
    if args.command == "index":
        return api.rlm_index(
            PublicIndexRequest(
                action=args.action,
                workspace_id=args.workspace_id,
                root_path=args.root_path,
                adapter_id=args.adapter_id,
                display_name=args.display_name,
                metadata=_parse_metadata_args(args.metadata),
                background=args.background,
                confirm=args.confirm,
            )
        )
    if args.command == "index-job":
        return api.rlm_index_job(PublicIndexJobRequest(job_id=args.job_id))
    if args.command == "wait-job":
        return api.rlm_wait_for_index_job(
            PublicWaitForIndexJobRequest(
                job_id=args.job_id,
                timeout_seconds=args.timeout,
            )
        )
    raise ValueError(f"Unsupported command: {args.command}")


def _add_workspace_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace-id", help="Registered workspace identifier")
    parser.add_argument("--root-path", help="Direct workspace path")
    parser.add_argument("--adapter-id", help="Preferred adapter identifier")
    parser.add_argument("--display-name", help="Optional display name for direct-path workspaces")
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Repeatable workspace metadata entry",
    )


def _parse_metadata_args(values: Sequence[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Metadata entry must use KEY=VALUE format: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Metadata key must not be empty: {item}")
        metadata[key] = value
    return metadata


def _parse_json_argument(raw: str | None) -> object | None:
    if raw is None:
        return None
    return json.loads(raw)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
