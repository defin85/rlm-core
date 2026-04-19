from __future__ import annotations

from pathlib import Path


GO_MODULE_PATH = "github.com/example/shop"
GO_MODULE_FILE = """\
module github.com/example/shop

go 1.22.3
"""


def build_go_fixture(workspace_root: Path) -> dict[str, str]:
    workspace_root = Path(workspace_root)
    (workspace_root / "go.mod").write_text(GO_MODULE_FILE, encoding="utf-8")

    main_file = workspace_root / "cmd" / "api" / "main.go"
    main_file.parent.mkdir(parents=True)
    main_file.write_text(
        "package main\n\n"
        "import (\n"
        '    "log"\n'
        '    "net/http"\n\n'
        f'    "{GO_MODULE_PATH}/internal/service"\n'
        ")\n\n"
        "func main() {\n"
        '    log.Fatal(http.ListenAndServe(":8080", service.NewService()))\n'
        "}\n",
        encoding="utf-8",
    )

    service_file = workspace_root / "internal" / "service" / "service.go"
    service_file.parent.mkdir(parents=True)
    service_file.write_text(
        "package service\n\n"
        "import (\n"
        '    "fmt"\n'
        '    "net/http"\n'
        ")\n\n"
        "type Config struct {\n"
        "    Name string\n"
        "}\n\n"
        "type Service struct{}\n\n"
        "func NewService() *Service {\n"
        "    return &Service{}\n"
        "}\n\n"
        "func (s *Service) ServeHTTP(w http.ResponseWriter, r *http.Request) {\n"
        '    fmt.Fprintf(w, "ok")\n'
        "}\n",
        encoding="utf-8",
    )

    storage_file = workspace_root / "internal" / "storage" / "memory.go"
    storage_file.parent.mkdir(parents=True)
    storage_file.write_text(
        "package storage\n\n"
        "import \"sync\"\n\n"
        "type MemoryStore struct {\n"
        "    mu sync.Mutex\n"
        "}\n",
        encoding="utf-8",
    )

    service_test_file = workspace_root / "internal" / "service" / "service_test.go"
    service_test_file.write_text(
        "package service\n\n"
        "import \"testing\"\n\n"
        "func TestNewService(t *testing.T) {\n"
        "    if NewService() == nil {\n"
        "        t.Fatal(\"expected service\")\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    return {
        "main_file": main_file.relative_to(workspace_root).as_posix(),
        "service_file": service_file.relative_to(workspace_root).as_posix(),
        "storage_file": storage_file.relative_to(workspace_root).as_posix(),
        "service_test_file": service_test_file.relative_to(workspace_root).as_posix(),
    }
