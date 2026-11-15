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
- 2026-11-15, team agreement (Spec 1): Protocol gains optional `condition_ids`; steps gain optional `status`, `drafted_by`, `approved_by`, `approved_on`, `approved_hash`.
- In a ReplayFile, an event of type `reading` must carry a complete Reading and an event of type `trigger` a complete Trigger. The payload may omit `schema_version`; it takes the file's. The service (`backend/service.py`) rejects the file otherwise.
- Example documents are placeholders for testing, not medical content.

## Provisional shapes (not frozen)
`provisional/` holds shapes the team uses that are **not** among the seven frozen contracts. They need team agreement before freezing; `validate.py` checks only the seven.

| Shape | Schema | Replay event type | Owner |
|---|---|---|---|
| Forecast | `provisional/forecast.schema.json` | `forecast` | Spec 3 (Forecast B, P1) |
| CrewForm | `provisional/crew-form.schema.json` | `form` | Spec 2 (post-EVA form, meal, crew note) |
| CrewLocation | `provisional/crew-location.schema.json` | `location` | Spec 2 (crew-location timeline for per-person exposure) |

Other replay event types in use: `crew_report` (emergency replay: chest pain is crew-reported).
Glucose is an ordinary Reading (indicator `glucose`), not a new shape.

Messages the habitat service pushes for Spec 2 (not stored contracts): `plan` (an action plan opened for an Alert),
`plan_result` (reversed / not reversed at the follow-up), and a `hot_summary` object beside the `payload` of every
`alert` and `trigger` message (the HotSummary, `backend/features.py`). The envelope is not a contract, so the
seven contracts are unchanged.

## Proposed Alert additions (Spec 2, pending team agreement, add-only)
The frozen Alert schema allows extra properties, so these already validate; they are listed here so the team can
agree them before they are written into `alert.schema.json`. No field is removed or changed.

| Field | When | Shape |
|---|---|---|
| `pattern` | joint-pattern drift alert | `"joint"` |
| `indicators` | with `pattern` | list of the indicators involved, largest share first (`indicator` is the first) |
| `escalation` | urgency `ESCALATE_TO_GROUND` because home-side actions failed | `{"reason", "plans_tried": [{"plan_id", "action", "opened_t", "follow_up_due_t", "result"}], "next_plan"}` |

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
