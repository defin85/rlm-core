from __future__ import annotations

from dataclasses import fields

from rlm_core.index import (
    AdapterMetadataRecord,
    CallRecord,
    DefinitionRecord,
    DiagnosticRecord,
    FileRecord,
    GenericIndexSnapshot,
    ImportRecord,
    InMemoryGenericIndexStore,
    IndexEntityKind,
    ReferenceRecord,
    SourceSpan,
    SymbolRecord,
)


def test_generic_index_store_persists_and_retrieves_entities():
    store = InMemoryGenericIndexStore()
    span = SourceSpan(start_line=3, start_column=5, end_line=3, end_column=20)
    snapshot = GenericIndexSnapshot(
        files=(
            FileRecord(file_id="file-1", path="src/main.py", language="python", digest="abc", line_count=20),
        ),
        symbols=(
            SymbolRecord(
                symbol_id="symbol-1",
                file_id="file-1",
                name="main",
                kind="function",
                qualified_name="main.main",
                span=span,
            ),
        ),
        definitions=(
            DefinitionRecord(definition_id="def-1", symbol_id="symbol-1", file_id="file-1", span=span),
        ),
        references=(
            ReferenceRecord(reference_id="ref-1", file_id="file-1", target_symbol_id="symbol-1", span=span),
        ),
        calls=(
            CallRecord(
                call_id="call-1",
                file_id="file-1",
                caller_symbol_id="symbol-1",
                callee_name="print",
                span=span,
            ),
        ),
        imports=(
            ImportRecord(import_id="import-1", file_id="file-1", imported_path="sys", is_resolved=True),
        ),
        diagnostics=(
            DiagnosticRecord(
                diagnostic_id="diag-1",
                file_id="file-1",
                severity="warning",
                message="demo warning",
                code="W001",
                span=span,
            ),
        ),
        metadata_extensions=(
            AdapterMetadataRecord(
                adapter_id="python",
                owner_kind=IndexEntityKind.SYMBOL,
                owner_id="symbol-1",
                payload={"decorators": ["staticmethod"]},
            ),
        ),
    )

    store.write_snapshot(snapshot)

    assert store.read_snapshot() == snapshot
    assert store.list_files() == snapshot.files
    assert store.list_symbols(file_id="file-1") == snapshot.symbols
    assert store.list_definitions(symbol_id="symbol-1") == snapshot.definitions
    assert store.list_references(symbol_id="symbol-1") == snapshot.references
    assert store.list_calls(caller_symbol_id="symbol-1") == snapshot.calls
    assert store.list_imports(file_id="file-1") == snapshot.imports
    assert store.list_diagnostics(file_id="file-1") == snapshot.diagnostics
    assert (
        store.list_metadata_extensions(
            adapter_id="python",
            owner_kind=IndexEntityKind.SYMBOL,
        )
        == snapshot.metadata_extensions
    )
    assert store.read_snapshot().entity_counts() == {
        "files": 1,
        "symbols": 1,
        "definitions": 1,
        "references": 1,
        "calls": 1,
        "imports": 1,
        "diagnostics": 1,
        "metadata_extensions": 1,
    }


def test_index_model_supports_minimal_and_richer_adapters_without_language_specific_core_fields():
    store = InMemoryGenericIndexStore()
    minimal_snapshot = GenericIndexSnapshot(
        files=(FileRecord(file_id="file-min", path="README.md"),),
        diagnostics=(
            DiagnosticRecord(
                diagnostic_id="diag-min",
                file_id="file-min",
                severity="info",
                message="indexed",
            ),
        ),
    )

    store.write_snapshot(minimal_snapshot)
    assert store.list_files() == minimal_snapshot.files
    assert store.list_symbols() == ()
    assert store.list_metadata_extensions() == ()

    richer_snapshot = GenericIndexSnapshot(
        files=(FileRecord(file_id="file-rich", path="pkg/service.go", language="go"),),
        symbols=(
            SymbolRecord(
                symbol_id="sym-rich",
                file_id="file-rich",
                name="Serve",
                kind="function",
            ),
        ),
        calls=(
            CallRecord(
                call_id="call-rich",
                file_id="file-rich",
                caller_symbol_id="sym-rich",
                callee_name="fmt.Println",
                span=SourceSpan(start_line=8),
            ),
        ),
        imports=(
            ImportRecord(
                import_id="import-rich",
                file_id="file-rich",
                imported_path="fmt",
                is_resolved=True,
            ),
        ),
        metadata_extensions=(
            AdapterMetadataRecord(
                adapter_id="go",
                owner_kind=IndexEntityKind.FILE,
                owner_id="file-rich",
                payload={"package_name": "service", "build_tags": ["linux"]},
            ),
        ),
    )

    store.write_snapshot(richer_snapshot)

    assert store.read_snapshot() == richer_snapshot
    assert store.list_metadata_extensions(adapter_id="go")[0].payload["package_name"] == "service"

    file_fields = {item.name for item in fields(FileRecord)}
    symbol_fields = {item.name for item in fields(SymbolRecord)}
    assert "adapter_id" not in file_fields
    assert "payload" not in file_fields
    assert "adapter_id" not in symbol_fields
    assert "payload" not in symbol_fields
