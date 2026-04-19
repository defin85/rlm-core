"""Generic core-owned index model, contracts, and reference store."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Protocol


class IndexEntityKind(StrEnum):
    """Generic entity kinds owned by the shared core index model."""

    FILE = "file"
    SYMBOL = "symbol"
    DEFINITION = "definition"
    REFERENCE = "reference"
    CALL = "call"
    IMPORT = "import"
    DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Generic source span used by multiple core index entities."""

    start_line: int
    start_column: int = 1
    end_line: int | None = None
    end_column: int | None = None

    def __post_init__(self) -> None:
        if self.start_line < 1 or self.start_column < 1:
            raise ValueError("SourceSpan positions must be >= 1")

        if self.end_line is None:
            object.__setattr__(self, "end_line", self.start_line)
        if self.end_column is None:
            object.__setattr__(self, "end_column", self.start_column)

        if self.end_line < self.start_line:
            raise ValueError("SourceSpan end_line must be >= start_line")
        if self.end_line == self.start_line and self.end_column < self.start_column:
            raise ValueError("SourceSpan end_column must be >= start_column on the same line")


@dataclass(frozen=True, slots=True)
class FileRecord:
    """Generic file entity emitted into the shared core index."""

    file_id: str
    path: str
    language: str | None = None
    digest: str | None = None
    size_bytes: int | None = None
    line_count: int | None = None


@dataclass(frozen=True, slots=True)
class SymbolRecord:
    """Generic symbol entity emitted into the shared core index."""

    symbol_id: str
    file_id: str
    name: str
    kind: str
    qualified_name: str | None = None
    span: SourceSpan | None = None


@dataclass(frozen=True, slots=True)
class DefinitionRecord:
    """Generic symbol definition location."""

    definition_id: str
    symbol_id: str
    file_id: str
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ReferenceRecord:
    """Generic symbol reference location."""

    reference_id: str
    file_id: str
    span: SourceSpan
    target_symbol_id: str | None = None
    target_name: str | None = None

    def __post_init__(self) -> None:
        if self.target_symbol_id is None and self.target_name is None:
            raise ValueError("ReferenceRecord requires target_symbol_id or target_name")


@dataclass(frozen=True, slots=True)
class CallRecord:
    """Generic call edge or call-site record."""

    call_id: str
    file_id: str
    span: SourceSpan
    caller_symbol_id: str | None = None
    callee_symbol_id: str | None = None
    callee_name: str | None = None

    def __post_init__(self) -> None:
        if self.callee_symbol_id is None and self.callee_name is None:
            raise ValueError("CallRecord requires callee_symbol_id or callee_name")


@dataclass(frozen=True, slots=True)
class ImportRecord:
    """Generic import/dependency edge."""

    import_id: str
    file_id: str
    imported_path: str
    imported_symbol: str | None = None
    is_resolved: bool = False


@dataclass(frozen=True, slots=True)
class DiagnosticRecord:
    """Generic diagnostic entry produced by an adapter or analyzer."""

    diagnostic_id: str
    file_id: str
    severity: str
    message: str
    code: str | None = None
    span: SourceSpan | None = None


@dataclass(frozen=True, slots=True)
class AdapterMetadataRecord:
    """Adapter-owned metadata attached to a core entity outside the shared schema."""

    adapter_id: str
    owner_kind: IndexEntityKind
    owner_id: str
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", dict(self.payload))


@dataclass(frozen=True, slots=True)
class GenericIndexSnapshot:
    """Immutable snapshot of the shared generic index state."""

    files: tuple[FileRecord, ...] = ()
    symbols: tuple[SymbolRecord, ...] = ()
    definitions: tuple[DefinitionRecord, ...] = ()
    references: tuple[ReferenceRecord, ...] = ()
    calls: tuple[CallRecord, ...] = ()
    imports: tuple[ImportRecord, ...] = ()
    diagnostics: tuple[DiagnosticRecord, ...] = ()
    metadata_extensions: tuple[AdapterMetadataRecord, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "files", tuple(self.files))
        object.__setattr__(self, "symbols", tuple(self.symbols))
        object.__setattr__(self, "definitions", tuple(self.definitions))
        object.__setattr__(self, "references", tuple(self.references))
        object.__setattr__(self, "calls", tuple(self.calls))
        object.__setattr__(self, "imports", tuple(self.imports))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "metadata_extensions", tuple(self.metadata_extensions))

    def entity_counts(self) -> dict[str, int]:
        return {
            "files": len(self.files),
            "symbols": len(self.symbols),
            "definitions": len(self.definitions),
            "references": len(self.references),
            "calls": len(self.calls),
            "imports": len(self.imports),
            "diagnostics": len(self.diagnostics),
            "metadata_extensions": len(self.metadata_extensions),
        }


class GenericIndexWriter(Protocol):
    """Write contract for shared generic index data."""

    def write_snapshot(self, snapshot: GenericIndexSnapshot) -> None:
        """Persist a complete generic index snapshot."""


class GenericIndexReader(Protocol):
    """Read contract for shared generic index data."""

    def read_snapshot(self) -> GenericIndexSnapshot:
        """Return the complete persisted generic index snapshot."""

    def list_files(self) -> tuple[FileRecord, ...]:
        """Return persisted file entities."""

    def list_symbols(self, *, file_id: str | None = None) -> tuple[SymbolRecord, ...]:
        """Return persisted symbol entities, optionally filtered by file."""

    def list_definitions(self, *, symbol_id: str | None = None) -> tuple[DefinitionRecord, ...]:
        """Return persisted definition entities, optionally filtered by symbol."""

    def list_references(self, *, symbol_id: str | None = None) -> tuple[ReferenceRecord, ...]:
        """Return persisted reference entities, optionally filtered by resolved target symbol."""

    def list_calls(self, *, caller_symbol_id: str | None = None) -> tuple[CallRecord, ...]:
        """Return persisted call entities, optionally filtered by caller symbol."""

    def list_imports(self, *, file_id: str | None = None) -> tuple[ImportRecord, ...]:
        """Return persisted import entities, optionally filtered by file."""

    def list_diagnostics(self, *, file_id: str | None = None) -> tuple[DiagnosticRecord, ...]:
        """Return persisted diagnostic entities, optionally filtered by file."""

    def list_metadata_extensions(
        self,
        *,
        adapter_id: str | None = None,
        owner_kind: IndexEntityKind | None = None,
        owner_id: str | None = None,
    ) -> tuple[AdapterMetadataRecord, ...]:
        """Return persisted adapter-owned metadata records."""


class InMemoryGenericIndexStore(GenericIndexReader, GenericIndexWriter):
    """Reference store for generic index persistence and retrieval contracts."""

    def __init__(self) -> None:
        self._snapshot = GenericIndexSnapshot()

    def write_snapshot(self, snapshot: GenericIndexSnapshot) -> None:
        self._snapshot = snapshot

    def read_snapshot(self) -> GenericIndexSnapshot:
        return self._snapshot

    def list_files(self) -> tuple[FileRecord, ...]:
        return self._snapshot.files

    def list_symbols(self, *, file_id: str | None = None) -> tuple[SymbolRecord, ...]:
        return tuple(
            record
            for record in self._snapshot.symbols
            if file_id is None or record.file_id == file_id
        )

    def list_definitions(self, *, symbol_id: str | None = None) -> tuple[DefinitionRecord, ...]:
        return tuple(
            record
            for record in self._snapshot.definitions
            if symbol_id is None or record.symbol_id == symbol_id
        )

    def list_references(self, *, symbol_id: str | None = None) -> tuple[ReferenceRecord, ...]:
        return tuple(
            record for record in self._snapshot.references if symbol_id is None or record.target_symbol_id == symbol_id
        )

    def list_calls(self, *, caller_symbol_id: str | None = None) -> tuple[CallRecord, ...]:
        return tuple(
            record
            for record in self._snapshot.calls
            if caller_symbol_id is None or record.caller_symbol_id == caller_symbol_id
        )

    def list_imports(self, *, file_id: str | None = None) -> tuple[ImportRecord, ...]:
        return tuple(
            record
            for record in self._snapshot.imports
            if file_id is None or record.file_id == file_id
        )

    def list_diagnostics(self, *, file_id: str | None = None) -> tuple[DiagnosticRecord, ...]:
        return tuple(
            record
            for record in self._snapshot.diagnostics
            if file_id is None or record.file_id == file_id
        )

    def list_metadata_extensions(
        self,
        *,
        adapter_id: str | None = None,
        owner_kind: IndexEntityKind | None = None,
        owner_id: str | None = None,
    ) -> tuple[AdapterMetadataRecord, ...]:
        return tuple(
            record
            for record in self._snapshot.metadata_extensions
            if (adapter_id is None or record.adapter_id == adapter_id)
            and (owner_kind is None or record.owner_kind == owner_kind)
            and (owner_id is None or record.owner_id == owner_id)
        )
