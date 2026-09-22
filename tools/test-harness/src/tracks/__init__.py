"""The tracks package: one module per test track plus the registry.

The registry holds one instance per track per process, built from the
same module singletons the interim dispatch and tests reference (a
second instance would split mutable module state like _Log and the
per-run track state). The symbol re-exports keep the pre-split
`from src.tracks import ...` call sites (evaluator.py, the test suite)
working.
"""

from src.tracks.pressure import (
    PRESSURE_TRACK,
    PressureTrack,
    _pressure_union_hook,
    build_pressure_prompt,
    build_pressure_run_record,
    load_pressure_scenarios,
)
from src.tracks.retrieval import (
    RETRIEVAL_CONTROL_AGENT,
    RETRIEVAL_EVALUATOR_AGENT,
    RETRIEVAL_TRACK,
    RetrievalTrack,
    _retrieval_union_hook,
    build_run_record,
    load_retrieval_queries,
    stage_and_dispatch,
)
from src.tracks.shape import (
    SHAPE_TRACK,
    ShapeTrack,
    _shape_union_hook,
    assemble_arm_body,
    build_shape_prompt,
    build_shape_run_record,
    load_shape_entries,
    marker_triage_counts,
    verify_arm_bytes,
)
from src.tracks.track import Track, _required
from src.tracks.trigger import (
    TRIGGER_TRACK,
    TriggerTrack,
    cmd_run,
    cmd_split,
)

# Re-exported for the pre-split `from src.tracks import ...` call sites
# (evaluator.py, the test suite).
__all__ = [
    "PRESSURE_TRACK",
    "PressureTrack",
    "RETRIEVAL_CONTROL_AGENT",
    "RETRIEVAL_EVALUATOR_AGENT",
    "RETRIEVAL_TRACK",
    "RetrievalTrack",
    "SHAPE_TRACK",
    "ShapeTrack",
    "TRACKS",
    "Track",
    "TRIGGER_TRACK",
    "TriggerTrack",
    "_pressure_union_hook",
    "_required",
    "_retrieval_union_hook",
    "_shape_union_hook",
    "assemble_arm_body",
    "build_pressure_prompt",
    "build_pressure_run_record",
    "build_run_record",
    "build_shape_prompt",
    "build_shape_run_record",
    "cmd_run",
    "cmd_split",
    "load_pressure_scenarios",
    "load_retrieval_queries",
    "load_shape_entries",
    "marker_triage_counts",
    "stage_and_dispatch",
    "verify_arm_bytes",
]

TRACKS: dict[str, Track] = {
    t.name: t
    for t in (TRIGGER_TRACK, RETRIEVAL_TRACK, SHAPE_TRACK, PRESSURE_TRACK)
}
