"""The history collections must stay namespaced.

mnema syncs deltas out of the shared `eyesofazrael` Firestore project, which
already holds azrael's mythology documents under `events`, `figures` and
`artifacts`. Dropping the `hist_` prefix from any collection would not fail —
it would quietly merge mythology deities and their events into the history
database on the next Refresh(). That is the regression this file guards.
"""
import re
from pathlib import Path

from mnema._query import (
    HISTORY_COLLECTIONS,
    _COLLECTION_TYPES,
    _DEFAULT_PROJECT,
)

# Names that exist unprefixed in the shared project and belong to other
# domains. None of these may ever appear in a mnema collection list.
COLLIDING_NAMES = {"events", "figures", "concepts", "artifacts"}

EXPECTED = [
    "hist_events", "hist_figures", "hist_periods", "hist_cultures",
    "hist_wars", "hist_discoveries", "hist_artifacts",
]


def test_collections_are_exactly_the_prefixed_set():
    assert HISTORY_COLLECTIONS == EXPECTED


def test_every_collection_is_prefixed():
    for coll in HISTORY_COLLECTIONS:
        assert coll.startswith("hist_"), coll


def test_no_unprefixed_colliding_name_can_appear():
    assert COLLIDING_NAMES.isdisjoint(HISTORY_COLLECTIONS)
    # Also catch a name that merely *ends* with a colliding one via a
    # different separator, e.g. "history.events" or "history-figures".
    for coll in HISTORY_COLLECTIONS:
        tail = re.split(r"[^a-z]", coll)[-1]
        assert not (tail in COLLIDING_NAMES and not coll.startswith("hist_")), coll


def test_collection_types_cover_every_collection():
    assert set(_COLLECTION_TYPES) == set(HISTORY_COLLECTIONS)


def test_collection_types_map_onto_the_local_entity_types():
    """The prefix is a Firestore namespace only — baked rows and queries use
    the bare type, so a delta must land under the bare type too."""
    assert _COLLECTION_TYPES == {
        "hist_events": "event",
        "hist_figures": "figure",
        "hist_periods": "period",
        "hist_cultures": "culture",
        "hist_wars": "war",
        "hist_discoveries": "discovery",
        "hist_artifacts": "artifact",
    }
    for entity_type in _COLLECTION_TYPES.values():
        assert not entity_type.startswith("hist_")


def test_bake_script_targets_the_same_prefixed_collections():
    """A re-bake must read the same collections Refresh() does."""
    # Read rather than import: scripts/bake.py has bake-only dependencies.
    src = (Path(__file__).resolve().parents[1] / "scripts" / "bake.py").read_text(
        encoding="utf-8"
    )
    assert 'REMOTE_PREFIX = "hist_"' in src
    assert "REMOTE_PREFIX + col_name" in src


# ── the project default ───────────────────────────────────────────────────────

def test_default_project_is_the_shared_one():
    assert _DEFAULT_PROJECT == "eyesofazrael"


def test_refresh_uses_the_default_project_when_the_env_var_is_unset(monkeypatch):
    monkeypatch.delenv("CLIO_PROJECT", raising=False)
    seen = {}
    _record_refresh(monkeypatch, seen)
    from mnema._query import Refresh

    assert Refresh() == 0
    assert seen["project"] == "eyesofazrael"
    assert seen["collections"] == EXPECTED


def test_env_var_still_overrides_the_project(monkeypatch):
    monkeypatch.setenv("CLIO_PROJECT", "clio-isolated")
    seen = {}
    _record_refresh(monkeypatch, seen)
    from mnema._query import Refresh

    Refresh()
    assert seen["project"] == "clio-isolated"


def test_empty_env_var_falls_back_rather_than_querying_nothing(monkeypatch):
    """An empty override used to short-circuit Refresh() to a no-op 0."""
    monkeypatch.setenv("CLIO_PROJECT", "")
    seen = {}
    _record_refresh(monkeypatch, seen)
    from mnema._query import Refresh

    Refresh()
    assert seen["project"] == "eyesofazrael"


def _record_refresh(monkeypatch, seen: dict) -> None:
    """Stub the eyecore delta layer, capturing what Refresh() asks it for."""
    import eyecore
    import mnema._query as q_mod

    monkeypatch.setattr(q_mod, "_BASE", _StubBase())
    monkeypatch.setattr(eyecore, "get_meta", lambda conn, key:
                        "2026-08-30T11:34:20.095810Z" if key == "generated_at" else None)

    def fake_fetch(project, collections, since, api_key=""):
        seen["project"] = project
        seen["collections"] = list(collections)
        seen["since"] = since
        return []

    monkeypatch.setattr(eyecore, "fetch_deltas", fake_fetch)
    monkeypatch.setattr(eyecore, "apply_deltas",
                        lambda conn, docs, types, now: len(docs))


class _StubBase:
    conn = None
