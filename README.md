# mnema

Historical encyclopedia for Python — figures, events, periods, cultures, wars, and artifacts from across recorded history.

## Features

- Historical figures, events, periods, cultures, wars, and artifacts
- Full-text search with FTS5 fallback to LIKE
- Era-based browsing (ancient, medieval, modern, etc.)
- Fuzzy name matching and random sampling
- Topic graph for related entry discovery
- On-demand corpus checkout from Project Gutenberg (downloaded once, cached locally)
- Optional LLM integration for intelligent queries

## Installation

```bash
pip install mnema
```

## Quick start

```python
import mnema

# Look up by type
figure  = mnema.GetFigure("Julius Caesar")
event   = mnema.GetEvent("Battle of Thermopylae")
period  = mnema.GetPeriod("Roman Republic")
culture = mnema.GetCulture("Byzantine")
war     = mnema.GetWar("Peloponnesian War")

# Generic lookup and full-text search
entry   = mnema.Get("Hannibal")
results = mnema.Search("Roman Empire")

# Browse by era or type
ancient = mnema.ByEra("ancient")
figures = mnema.ByType("figure", "medieval")
all_fig = mnema.AllFigures("roman")
events  = mnema.AllEvents("ancient")

# Random, fuzzy, and statistics
random_ = mnema.GetRandom("figure")
matches = mnema.GetFuzzy("caesar")
popular = mnema.GetMost("mythology")   # 'mythology' column = era
total   = mnema.Count()

# Topic graph
related = mnema.GetRelated("Julius Caesar")
topics  = mnema.GetTopics("roman")
tree    = mnema.GetTopicTree("ancient-rome")

# Corpus — downloads from Project Gutenberg on first use
mnema.FetchCorpus("gutenberg-plutarch")
hits    = mnema.SearchCorpus("assassination")
sources = mnema.ListCorpuses()
```

## Available corpuses

| Corpus ID | Text |
|---|---|
| `gutenberg-herodotus` | Herodotus's Histories |
| `gutenberg-thucydides` | Thucydides's History of the Peloponnesian War |
| `gutenberg-plutarch` | Plutarch's Lives |
| `gutenberg-caesar` | Julius Caesar's Gallic Wars |
| `gutenberg-tacitus` | Tacitus's Annals |
| `gutenberg-livy` | Livy's History of Rome |
| `gutenberg-sun-tzu` | Sun Tzu's The Art of War |
| `gutenberg-machiavelli` | Machiavelli's The Prince |
| `gutenberg-gibbon` | Gibbon's Decline and Fall of the Roman Empire |
| `gutenberg-marco-polo` | Marco Polo's Travels |
| `gutenberg-federalist` | The Federalist Papers |
| `gutenberg-common-sense` | Thomas Paine's Common Sense |
| `gutenberg-darwin` | Darwin's On the Origin of Species |
| `gutenberg-wealth-of-nations` | Adam Smith's The Wealth of Nations |

## Part of the Eyes of Azrael suite

| Package | Description |
|---|---|
| [`eyecore`](https://github.com/EyesOfAzrael/eyecore) | Shared foundation (DB, graph, corpus, LLM) |
| [`azrael`](https://github.com/EyesOfAzrael/azrael) | Mythology encyclopedia |
| [`apocrypha`](https://github.com/EyesOfAzrael/apocrypha) | Conspiracy theories and hidden histories |
| [`augur`](https://github.com/EyesOfAzrael/augur) | News aggregation and topic analysis |

## License

MIT — see [LICENSE](LICENSE)
