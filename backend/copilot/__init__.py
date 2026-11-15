"""Collapse Copilot (Spec 3), running inside the emergency service.

Ticket 02 stand-ins for Spec 1/2, behind two small interfaces. Spec 1/2 owners: read this.

1. HotSummary (Spec 2 builds it in the habitat service)
   Push one JSON object per crew member to the emergency service, either as an SSE message
   {"type": "hot_summary", "payload": {...}} or under the key "hot_summary" inside an
   alert/trigger payload. Required shape: see `HotSummary` in copilot/hot_summary.py.
   The emergency service keeps only the latest snapshot per crew (`eng.hot_summaries`).
   Consumers call `eng.hot_summaries.latest(crew)` and get a `HotSummary` or `NoHistory`
   (never an exception, never None). Replace `copilot.fixtures` with the real feed; do not
   change the field names without team agreement (add-only).

2. Condition library (Spec 1 builds the real condition records)
   `copilot.conditions.load_conditions()` returns a `ConditionLibrary`. Today it reads the
   fake `content/copilot/conditions.json`. Each condition has a prior, a mapped protocol id,
   a `simulatable` flag (Pulse can simulate it, so L1 can learn it) and cited signs with
   likelihood ratios. Every prior and ratio carries a source label. Spec 1 swaps the loader
   and keeps the `Condition` / `Sign` shape.
"""
