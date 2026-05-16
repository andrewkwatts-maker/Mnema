"""
mnema — Historical events, figures, periods, and civilizations.

Quick start:
    import mnema
    figure   = mnema.GetFigure("Julius Caesar")
    results  = mnema.Search("Roman Empire")
    ancient  = mnema.ByEra("ancient")
    figures  = mnema.AllFigures("roman")
    related  = mnema.GetRelated("caesar")
    mnema.FetchCorpus("gutenberg-plutarch")   # download Plutarch's Lives
    excerpts = mnema.SearchCorpus("assassination")
"""
from __future__ import annotations

from ._query import (
    Get,
    Search,
    ByEra,
    ByType,
    AllFigures,
    AllEvents,
    AllPeriods,
    Count,
    GetRandom,
    GetFuzzy,
    GetMost,
    GetAll,
    GetTopics,
    GetRelated,
    GetTopicTree,
    SearchCorpus,
    FetchCorpus,
    ListCorpuses,
    _typed,
)


def GetEvent(query: str) -> dict | None:
    """Return a historical event by name."""
    return _typed(query, "event")


def GetFigure(query: str) -> dict | None:
    """Return a historical figure by name."""
    return _typed(query, "figure")


def GetPeriod(query: str) -> dict | None:
    """Return a historical period by name."""
    return _typed(query, "period")


def GetCulture(query: str) -> dict | None:
    """Return a culture or civilization by name."""
    return _typed(query, "culture")


def GetWar(query: str) -> dict | None:
    """Return a war by name."""
    return _typed(query, "war")


def GetArtifact(query: str) -> dict | None:
    """Return an artifact by name."""
    return _typed(query, "artifact")


__version__ = "1.0.0a0"

__all__ = [
    "Get",
    "GetEvent",
    "GetFigure",
    "GetPeriod",
    "GetCulture",
    "GetWar",
    "GetArtifact",
    "Search",
    "ByEra",
    "ByType",
    "AllFigures",
    "AllEvents",
    "AllPeriods",
    "Count",
    "GetRandom",
    "GetFuzzy",
    "GetMost",
    "GetAll",
    "GetTopics",
    "GetRelated",
    "GetTopicTree",
    "SearchCorpus",
    "FetchCorpus",
    "ListCorpuses",
]
