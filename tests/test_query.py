"""Unit tests for mnema._query — all queries run against an in-memory SQLite DB."""
import pytest
import mnema
from mnema._query import (
    Get,
    Search,
    ByMythology,
    ByEra,
    ByType,
    Count,
    GetRandom,
    GetFuzzy,
    GetMost,
    GetAll,
)


# ---------------------------------------------------------------------------
# Get — exact / fuzzy name lookup
# ---------------------------------------------------------------------------

def test_get_exact(patch_base):
    """Get with exact name returns the matching entity."""
    result = Get("Julius Caesar")
    assert result is not None
    assert result["name"] == "Julius Caesar"


def test_get_fuzzy(patch_base):
    """Get with lowercase name still finds the entity (case-insensitive)."""
    result = Get("julius caesar")
    assert result is not None
    assert result["name"] == "Julius Caesar"


def test_get_partial(patch_base):
    """Get with a substring matches via the LIKE fallback."""
    result = Get("Caesar")
    assert result is not None
    assert result["name"] == "Julius Caesar"


def test_get_none(patch_base):
    """Get with an unknown name returns None."""
    result = Get("Nonexistent9999")
    assert result is None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def test_search(patch_base):
    """Search returns at least one result for a known entity name."""
    results = Search("Caesar")
    assert isinstance(results, list)
    assert len(results) >= 1
    names = [r["name"] for r in results]
    assert "Julius Caesar" in names


def test_search_returns_list_on_no_match(patch_base):
    """Search with a non-matching term returns an empty list, never None."""
    results = Search("xyzzy_no_match_99")
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# ByEra (alias for ByMythology using the mythology column as era/culture)
# ---------------------------------------------------------------------------

def test_by_era(patch_base):
    """ByEra('roman') returns roman entities."""
    results = ByEra("roman")
    assert len(results) >= 2
    for r in results:
        assert r["mythology"] == "roman"


def test_by_era_case_insensitive(patch_base):
    """ByEra is case-insensitive."""
    results = ByEra("ROMAN")
    assert len(results) >= 2


def test_by_mythology_alias(patch_base):
    """ByMythology is an alias for ByEra; both return same results."""
    assert ByMythology("roman") == ByEra("roman")


def test_by_era_no_results(patch_base):
    """ByEra with unknown value returns empty list."""
    results = ByEra("mesopotamian")
    assert results == []


# ---------------------------------------------------------------------------
# ByType
# ---------------------------------------------------------------------------

def test_by_type(patch_base):
    """ByType('figure') returns Caesar and Cleopatra."""
    results = ByType("figure")
    assert len(results) == 2
    names = {r["name"] for r in results}
    assert "Julius Caesar" in names
    assert "Cleopatra" in names


def test_by_type_filtered(patch_base):
    """ByType('figure', 'roman') returns only Caesar."""
    results = ByType("figure", "roman")
    assert len(results) == 1
    assert results[0]["name"] == "Julius Caesar"


def test_by_type_no_results(patch_base):
    """ByType with an absent type returns empty list."""
    results = ByType("myth")
    assert results == []


# ---------------------------------------------------------------------------
# Count
# ---------------------------------------------------------------------------

def test_count_all(patch_base):
    """Count() without filter returns total entity count (5 in test DB)."""
    assert Count() == 5


def test_count_typed(patch_base):
    """Count('figure') returns 2 (Caesar and Cleopatra)."""
    assert Count("figure") == 2


def test_count_zero_for_missing_type(patch_base):
    """Count with an absent type returns 0."""
    assert Count("myth") == 0


# ---------------------------------------------------------------------------
# GetRandom
# ---------------------------------------------------------------------------

def test_getrandom(patch_base):
    """GetRandom() returns a dict with a 'name' key."""
    result = GetRandom()
    assert result is not None
    assert isinstance(result, dict)
    assert "name" in result


def test_getrandom_typed(patch_base):
    """GetRandom('figure') returns an entity whose type is 'figure'."""
    result = GetRandom("figure")
    assert result is not None
    assert result["type"] == "figure"


def test_getrandom_era(patch_base):
    """GetRandom(era='roman') returns a roman entity."""
    result = GetRandom(era="roman")
    assert result is not None
    assert result["mythology"] == "roman"


def test_getrandom_typed_and_era(patch_base):
    """GetRandom with both type and era filters correctly."""
    result = GetRandom("figure", "roman")
    assert result is not None
    assert result["type"] == "figure"
    assert result["mythology"] == "roman"


def test_getrandom_no_match_returns_none(patch_base):
    """GetRandom for a type with no entities returns None."""
    result = GetRandom("myth")
    assert result is None


# ---------------------------------------------------------------------------
# GetFuzzy
# ---------------------------------------------------------------------------

def test_getfuzzy(patch_base):
    """GetFuzzy('Cleop') finds Cleopatra via the LIKE fallback."""
    results = GetFuzzy("Cleop")
    assert isinstance(results, list)
    assert len(results) >= 1
    names = [r["name"] for r in results]
    assert "Cleopatra" in names


def test_getfuzzy_case_insensitive(patch_base):
    """GetFuzzy is case-insensitive."""
    results = GetFuzzy("cleop")
    names = [r["name"] for r in results]
    assert "Cleopatra" in names


def test_getfuzzy_no_match(patch_base):
    """GetFuzzy with no match returns empty list."""
    results = GetFuzzy("xyzzy_nope_9999")
    assert results == []


# ---------------------------------------------------------------------------
# GetMost
# ---------------------------------------------------------------------------

def test_getmost_mythology(patch_base):
    """GetMost('mythology') returns a list that includes 'roman'."""
    results = GetMost("mythology")
    assert isinstance(results, list)
    assert len(results) >= 1
    keys = {r["mythology"] for r in results}
    assert "roman" in keys


def test_getmost_type(patch_base):
    """GetMost('type') returns a list that includes 'figure'."""
    results = GetMost("type")
    assert isinstance(results, list)
    assert len(results) >= 1
    keys = {r["type"] for r in results}
    assert "figure" in keys


def test_getmost_count_field(patch_base):
    """GetMost results each have a 'count' key with an integer value."""
    results = GetMost("mythology")
    for r in results:
        assert "count" in r
        assert isinstance(r["count"], int)
        assert r["count"] >= 1


def test_getmost_invalid_field(patch_base):
    """GetMost with an unsupported field raises ValueError."""
    with pytest.raises(ValueError):
        GetMost("name")


# ---------------------------------------------------------------------------
# GetAll
# ---------------------------------------------------------------------------

def test_getall(patch_base):
    """GetAll() without filters returns all 5 entities."""
    results = GetAll()
    assert isinstance(results, list)
    assert len(results) == 5


def test_getall_filtered_type(patch_base):
    """GetAll('figure') returns the 2 figure entities."""
    results = GetAll("figure")
    assert len(results) == 2
    for r in results:
        assert r["type"] == "figure"


def test_getall_filtered_era(patch_base):
    """GetAll(era='egyptian') returns only Cleopatra."""
    results = GetAll(era="egyptian")
    assert len(results) == 1
    assert results[0]["name"] == "Cleopatra"


def test_getall_filtered_type_and_era(patch_base):
    """GetAll('figure', 'roman') returns only Caesar."""
    results = GetAll("figure", "roman")
    assert len(results) == 1
    assert results[0]["name"] == "Julius Caesar"


def test_getall_no_match(patch_base):
    """GetAll with non-existent type returns empty list."""
    results = GetAll("myth")
    assert results == []


# ---------------------------------------------------------------------------
# Typed helpers defined in mnema.__init__
# ---------------------------------------------------------------------------

def test_getfigure(patch_base):
    """mnema.GetFigure('Julius Caesar') returns the Caesar entity."""
    result = mnema.GetFigure("Julius Caesar")
    assert result is not None
    assert result["name"] == "Julius Caesar"
    assert result["type"] == "figure"


def test_getevent(patch_base):
    """mnema.GetEvent('Marathon') finds the Battle of Marathon via LIKE."""
    result = mnema.GetEvent("Marathon")
    assert result is not None
    assert result["type"] == "event"


def test_getperiod(patch_base):
    """mnema.GetPeriod('Roman Republic') returns the period entity."""
    result = mnema.GetPeriod("Roman Republic")
    assert result is not None
    assert result["type"] == "period"


def test_getartifact(patch_base):
    """mnema.GetArtifact('Colosseum') returns the artifact entity."""
    result = mnema.GetArtifact("Colosseum")
    assert result is not None
    assert result["type"] == "artifact"


def test_getculture_returns_none_for_missing(patch_base):
    """mnema.GetCulture for a non-existent culture returns None."""
    result = mnema.GetCulture("Atlantean")
    assert result is None


def test_getwar_domain_fallback(patch_base):
    """mnema.GetWar falls back to domains_text LIKE; 'persia' is in Marathon's domains."""
    result = mnema.GetWar("persia")
    # Marathon is type 'event', not 'war', so this should return None
    # This validates that the type filter is applied correctly
    assert result is None


def test_typed_helper_wrong_type_returns_none(patch_base):
    """GetFigure with an event name returns None (type mismatch)."""
    result = mnema.GetFigure("Battle of Marathon")
    assert result is None


def test_typed_helper_domain_fallback(patch_base):
    """_typed falls back to domains_text LIKE; 'politics' is in Caesar's domains."""
    result = mnema.GetFigure("politics")
    # Caesar and Cleopatra both have 'politics' in domains; result should be one of them
    assert result is not None
    assert result["type"] == "figure"


# ---------------------------------------------------------------------------
# GetRelated and GetTopics (graph layer — empty in test DB, so verify safe returns)
# ---------------------------------------------------------------------------

def test_gettopics_no_topics(patch_base):
    """GetTopics with empty topics table returns empty list."""
    results = mnema.GetTopics()
    assert isinstance(results, list)


def test_getrelated_unknown(patch_base):
    """GetRelated for an unknown name returns empty list."""
    results = mnema.GetRelated("Nonexistent9999")
    assert results == []
