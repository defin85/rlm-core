# rlm-core

Мультиязычное RLM-ядро для анализа репозиториев через общий runtime, adapter-owned helper-ы и единый public API.

## Что уже реализовано

- `rlm_core.runtime`:
  shared session lifecycle, sandbox execution, workspace registry, adapter selection.
- `rlm_core.index`:
  generic lifecycle orchestration, background jobs, locking, uniform unsupported semantics.
- `rlm_core.public_api` и `rlm_core.cli`:
  stable transport-neutral surface для `rlm_projects`, `rlm_start`, `rlm_execute`, `rlm_end`, `rlm_index`, `rlm_index_job`, `rlm_wait_for_index_job`.
- `rlm_core.adapters.bsl`:
  live helper-ы, prebuilt snapshot index, advanced metadata snapshot.
- `rlm_core.adapters.go`:
  live-only helper surface для package/import/declaration workflows.

## Поддерживаемые режимы

- `generic`:
  direct-path walking skeleton без language adapter. Доступны generic helper-ы, но index lifecycle явно `unsupported`.
- `bsl`:
  live navigation и prebuilt index lifecycle через adapter-owned snapshots.
- `go`:
  live navigation без prebuilt index. Lifecycle actions возвращают явный `unsupported`, а не adapter selection error.

## Принципы

- Generic core отвечает за orchestration, а не за доменную логику языка.
- Adapter-specific behavior surfaced через capability matrix и единые public semantics.
- Индекс используется как ускоритель, а не как обязательный внешний сервис.
- Unsupported behavior должен быть явным и одинаковым по форме для всех adapters.

## Быстрый старт

- Посмотреть зарегистрированные проекты:
  `uv run rlm-core projects`
- Запустить runtime на прямом пути:
  `uv run rlm-core start --root-path /path/to/repo --query "inspect repo"`
- Проверить lifecycle surface:
  `uv run rlm-core index info --root-path /path/to/repo`
- Прогнать quality evals:
  `uv run rlm-core evals --plain-root /tmp/plain --bsl-root /tmp/bsl`
- Добрать optional Go case:
  `uv run rlm-core evals --plain-root /tmp/plain --bsl-root /tmp/bsl --go-root /tmp/go`

## Статус

Текущий core и два production adapters уже в репозитории. Актуальный source of truth для архитектуры и change history лежит в `src/`, `tests/`, `docs/ARCHITECTURE.md` и `openspec/changes/`.
