"""Go-specific repository contracts."""

from __future__ import annotations

from dataclasses import dataclass

GO_LIVE_FEATURES = frozenset(
    {
        "packages",
        "declarations",
        "imports",
    }
)


@dataclass(frozen=True, slots=True)
class GoRepositoryDetails:
    """Adapter-owned repository details for Go workspaces."""

    module_root: str = "."
    module_file: str = "go.mod"
    module_path: str | None = None
    go_version: str | None = None

    def as_mapping(self) -> dict[str, object]:
        details: dict[str, object] = {
            "module_root": self.module_root,
            "module_file": self.module_file,
        }
        if self.module_path:
            details["module_path"] = self.module_path
        if self.go_version:
            details["go_version"] = self.go_version
        return details
