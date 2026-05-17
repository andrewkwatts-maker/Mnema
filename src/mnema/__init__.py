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

try:
    from ._core import tokenize, highlight_snippet, score_entry
    _RUST_CORE = True
except ImportError:
    _RUST_CORE = False

    def tokenize(text: str, min_len: int) -> list:
        return [
            "".join(c for c in w if c.isalpha()).lower()
            for w in text.split()
            if len("".join(c for c in w if c.isalpha())) >= min_len
        ]

    def highlight_snippet(text: str, query: str, context: int) -> str:
        tl = text.lower()
        ql = query.lower()
        pos = tl.find(ql)
        if pos == -1:
            return text[: context * 2]
        start = max(0, pos - context)
        end = min(len(text), pos + len(ql) + context)
        snippet = text[start:end]
        return ("…" + snippet) if start > 0 else snippet

    def score_entry(title: str, body: str, query: str) -> float:
        q = query.lower()
        t = title.lower()
        if not q:
            return 0.0
        score = 0.0
        if t.startswith(q):
            score += 1000.0
        elif q in t:
            score += 500.0
        if q in body.lower():
            score += 150.0
        return score

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


__version__ = "1.0.0"

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
    "_RUST_CORE",
]
