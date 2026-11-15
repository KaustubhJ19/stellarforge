# Contracts

The seven shared JSON Schemas (draft 2020-12) from Spec 1. They are the only shapes that cross a stream boundary.

| Contract | Schema | Example |
|---|---|---|
| Reading | `reading.schema.json` | `examples/Reading.example.json` |
| Alert | `alert.schema.json` | `examples/Alert.example.json` |
| CrewRecord | `crew-record.schema.json` | `examples/CrewRecord.example.json` |
| ReplayFile | `replay-file.schema.json` | `examples/ReplayFile.example.json` |
| Protocol | `protocol.schema.json` | `examples/Protocol.example.json` |
| GroundReport | `ground-report.schema.json` | `examples/GroundReport.example.json` |
| Trigger | `trigger.schema.json` | `examples/Trigger.example.json` |

Every document carries a `schema_version` field. The schemas enforce only what the Spec 1 Contracts table states: the listed fields (optional ones are marked `?` in the spec), the listed allowed values, `confidence` between 0 and 1, `t` as Mission clock seconds, and ReplayFile events ordered by `t`.

## Rules
- Add a field only by agreement in the team chat. Never remove one.
- In a ReplayFile, an event of type `reading` must carry a complete Reading and an event of type `trigger` a complete Trigger. The payload may omit `schema_version`; it takes the file's. The service (`backend/service.py`) rejects the file otherwise.
- Example documents are placeholders for testing, not medical content.

## Provisional shapes (not frozen)
`provisional/` holds shapes the team uses that are **not** among the seven frozen contracts. They need team agreement before freezing; `validate.py` checks only the seven.

| Shape | Schema | Replay event type | Owner |
|---|---|---|---|
| Forecast | `provisional/forecast.schema.json` | `forecast` | Spec 3 (Forecast B, P1) |

Other replay event types in use: `crew_report` (emergency replay: chest pain is crew-reported).

## Where replays live
- `replay/`: shared replay files, tracked in git, with a `.source.json` record each (see `replay/README.md`).
- `replay/recorded/`: replays recorded through the service with detection output (Spec 3's recording script writes here).
- `replay/generated/`: local generator output, not tracked.

## Validate
```bash
pip install -r contracts/requirements.txt
python contracts/validate.py Reading path/to/file.json
```
From Python: `from validate import validate, ContractError` (with `contracts/` on the path), then `validate("Reading", doc)`. Other languages can load the `*.schema.json` files with any JSON Schema 2020-12 validator.

## Test
```bash
python -m pytest contracts
```
