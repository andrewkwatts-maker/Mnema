#!/usr/bin/env python3
"""Bake history data into clio.db (SQLite) via the Firestore REST API.

Usage:
    python scripts/bake.py                          # pull from Firebase
    python scripts/bake.py --source /path/to/dir   # use local JSON export
    python scripts/bake.py --project PROJECT_ID --api-key KEY
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from eyecore import compress_db, GRAPH_SCHEMA

try:
    import requests
except ImportError:
    sys.exit("Install bake deps: pip install 'clio[bake]'")

ROOT = Path(__file__).parent.parent
DATA_OUT = ROOT / "src" / "clio" / "_data" / "clio.db"

# Set CLIO_PROJECT and CLIO_API_KEY env vars when the Firebase project is ready
DEFAULT_PROJECT = os.getenv("CLIO_PROJECT", "")
DEFAULT_API_KEY = os.getenv("CLIO_API_KEY", os.getenv("FIREBASE_API_KEY", ""))

COLLECTIONS: dict[str, str] = {
    "events": "event",
    "figures": "figure",
    "periods": "period",
    "cultures": "culture",
    "wars": "war",
    "discoveries": "discovery",
    "artifacts": "artifact",
}

TYPE_FIXES: dict[str, str] = {}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    mythology TEXT,
    domains_text TEXT,
    search_text TEXT,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_name ON entities(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_mythology ON entities(mythology COLLATE NOCASE);
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    id UNINDEXED,
    search_text,
    tokenize='unicode61 remove_diacritics 1'
);
CREATE TABLE IF NOT EXISTS entity_topics (
    entity_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    PRIMARY KEY (entity_id, topic_id),
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    FOREIGN KEY (topic_id) REFERENCES topics(id)
);
CREATE INDEX IF NOT EXISTS idx_entity_topics_entity ON entity_topics(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_topics_topic ON entity_topics(topic_id);
"""


# ── Firestore REST helpers ────────────────────────────────────────────────────

def _parse_value(val: dict):
    if "stringValue" in val:
        return val["stringValue"]
    if "integerValue" in val:
        return int(val["integerValue"])
    if "doubleValue" in val:
        return float(val["doubleValue"])
    if "booleanValue" in val:
        return val["booleanValue"]
    if "nullValue" in val:
        return None
    if "timestampValue" in val:
        return val["timestampValue"]
    if "arrayValue" in val:
        return [_parse_value(v) for v in val["arrayValue"].get("values", [])]
    if "mapValue" in val:
        return {k: _parse_value(v) for k, v in val["mapValue"].get("fields", {}).items()}
    return None


def _doc_to_dict(doc: dict) -> dict:
    result = {k: _parse_value(v) for k, v in doc.get("fields", {}).items()}
    result["id"] = doc["name"].rsplit("/", 1)[-1]
    return result


def _fetch_collection(session: requests.Session, base_url: str,
                      collection: str, api_key: str) -> list[dict]:
    url = f"{base_url}/{collection}"
    docs: list[dict] = []
    page_token: str | None = None
    while True:
        params: dict = {"key": api_key, "pageSize": 300}
        if page_token:
            params["pageToken"] = page_token
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for doc in data.get("documents", []):
            docs.append(_doc_to_dict(doc))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return docs


# ── DB helpers ────────────────────────────────────────────────────────────────

def _coerce_type(raw: str | None, fallback: str) -> str:
    if not raw:
        return fallback
    return TYPE_FIXES.get(raw, raw)


def _str_list(val) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        return " ".join(str(v) for v in val if v)
    return str(val)


def _domains_text(e: dict) -> str:
    parts = [
        _str_list(e.get("domains")),
        _str_list(e.get("attributes")),
        _str_list(e.get("significance")),
        _str_list(e.get("tags")),
    ]
    return " ".join(p for p in parts if p).lower()


def _search_text(e: dict) -> str:
    parts = [
        e.get("name", ""),
        e.get("era", "") or e.get("period", ""),
        e.get("description") or e.get("shortDescription") or e.get("longDescription", ""),
        _str_list(e.get("tags")),
        e.get("subtitle", ""),
    ]
    return " ".join(p for p in parts if p)


def _init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    db = sqlite3.connect(str(db_path))
    for stmt in CREATE_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            db.execute(s)
    for stmt in GRAPH_SCHEMA.strip().split(";"):
        s = stmt.strip()
        if s:
            db.execute(s)
    db.commit()
    return db


def _insert_batch(db: sqlite3.Connection, rows: list, fts_rows: list) -> None:
    db.executemany(
        "INSERT OR REPLACE INTO entities"
        "(id, name, type, mythology, domains_text, search_text, data) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    db.executemany(
        "INSERT INTO entities_fts(id, search_text) VALUES (?,?)",
        fts_rows,
    )
    db.commit()


# ── Topic graph builder ───────────────────────────────────────────────────────

def _build_topic_graph(db: sqlite3.Connection, all_rows: list) -> None:
    """Build era/type topic nodes and entity_topic links from inserted entity rows.

    all_rows items: (id, name, type, mythology, domains_text, search_text, data)
    """
    from eyecore import TopicGraph

    graph = TopicGraph(db)

    # Collect unique eras and types with co-occurrence tracking
    era_entities: dict[str, list[str]] = {}   # era -> [entity_id, ...]
    type_entities: dict[str, list[str]] = {}  # type -> [entity_id, ...]
    # era -> set of types present in that era
    era_type_pairs: dict[str, set[str]] = {}

    for row in all_rows:
        eid, name, etype, era, *_ = row
        if era:
            era_entities.setdefault(era, []).append(eid)
            era_type_pairs.setdefault(era, set()).add(etype)
        type_entities.setdefault(etype, []).append(eid)

    # Upsert era topics (root level — no parent)
    for era in era_entities:
        graph.upsert_topic(
            id=f"era:{era}",
            name=era,
            type="era",
            description=f"Historical era or period: {era}",
        )

    # Upsert type topics (root level — no parent)
    for etype in type_entities:
        graph.upsert_topic(
            id=f"type:{etype}",
            name=etype,
            type="entity_type",
            description=f"Entity type: {etype}",
        )

    # Link types -> eras where they co-occur
    for era, types in era_type_pairs.items():
        for etype in types:
            graph.upsert_link(
                from_id=f"type:{etype}",
                to_id=f"era:{era}",
                relation="appears_in",
                weight=len([
                    eid for eid in type_entities.get(etype, [])
                    if eid in era_entities.get(era, [])
                ]),
            )

    graph.commit()

    # Insert entity_topics rows
    entity_topic_rows = []
    for row in all_rows:
        eid, name, etype, era, *_ = row
        if era:
            entity_topic_rows.append((eid, f"era:{era}"))
        entity_topic_rows.append((eid, f"type:{etype}"))

    if entity_topic_rows:
        db.executemany(
            "INSERT OR IGNORE INTO entity_topics(entity_id, topic_id) VALUES (?,?)",
            entity_topic_rows,
        )
        db.commit()

    era_count = len(era_entities)
    type_count = len(type_entities)
    link_count = sum(len(t) for t in era_type_pairs.values())
    print(f"  Topic graph: {era_count} eras, {type_count} types, {link_count} links, "
          f"{len(entity_topic_rows)} entity-topic rows")


# ── Bake functions ────────────────────────────────────────────────────────────

def bake_from_firebase(db_path: Path, project_id: str, api_key: str) -> None:
    if not project_id or not api_key:
        sys.exit(
            "Firebase project pending. Set CLIO_PROJECT and CLIO_API_KEY env vars, "
            "or pass --project and --api-key."
        )
    base = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
    session = requests.Session()
    db = _init_db(db_path)
    total = 0
    all_rows: list = []
    for col_name, entity_type in COLLECTIONS.items():
        print(f"  {col_name}...", end=" ", flush=True)
        try:
            entities = _fetch_collection(session, base, col_name, api_key)
        except requests.HTTPError as exc:
            print(f"SKIP ({exc.response.status_code})")
            continue
        rows, fts_rows = [], []
        for e in entities:
            eid = e.get("id") or ""
            if not eid:
                continue
            etype = _coerce_type(e.get("type"), entity_type)
            e["type"] = etype
            era = e.get("era") or e.get("period")
            srch = _search_text(e)
            row = (eid, e.get("name", eid), etype, era, _domains_text(e), srch,
                   json.dumps(e, ensure_ascii=False))
            rows.append(row)
            all_rows.append(row)
            fts_rows.append((eid, srch))
        _insert_batch(db, rows, fts_rows)
        print(len(rows))
        total += len(rows)
    print(f"\nBuilding topic graph...")
    _build_topic_graph(db, all_rows)
    size = db_path.stat().st_size / 1_048_576
    print(f"Done: {total} entities -> {db_path} ({size:.1f} MB)")
    db.close()
    gz_path = compress_db(db_path)
    print(f"Compressed -> {gz_path} ({gz_path.stat().st_size / 1_048_576:.1f} MB)")


def bake_from_local(source_dir: Path, db_path: Path) -> None:
    if not source_dir.exists():
        sys.exit(f"Source not found: {source_dir}")
    db = _init_db(db_path)
    total = 0
    all_rows: list = []
    for col_name, entity_type in COLLECTIONS.items():
        col_dir = source_dir / col_name
        if not col_dir.exists():
            print(f"  SKIP {col_name} (not found)")
            continue
        files = [f for f in col_dir.glob("*.json") if not f.name.startswith("_")]
        print(f"  {col_name}: {len(files)} -> {entity_type}")
        rows, fts_rows = [], []
        for jf in files:
            try:
                e = json.loads(jf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            eid = e.get("id") or jf.stem
            e["id"] = eid
            etype = _coerce_type(e.get("type"), entity_type)
            e["type"] = etype
            era = e.get("era") or e.get("period")
            srch = _search_text(e)
            row = (eid, e.get("name", eid), etype, era, _domains_text(e), srch,
                   json.dumps(e, ensure_ascii=False))
            rows.append(row)
            all_rows.append(row)
            fts_rows.append((eid, srch))
        _insert_batch(db, rows, fts_rows)
        total += len(rows)
    print(f"\nBuilding topic graph...")
    _build_topic_graph(db, all_rows)
    size = db_path.stat().st_size / 1_048_576
    print(f"Done: {total} entities -> {db_path} ({size:.1f} MB)")
    db.close()
    gz_path = compress_db(db_path)
    print(f"Compressed -> {gz_path} ({gz_path.stat().st_size / 1_048_576:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bake history data into clio.db")
    parser.add_argument("--source", metavar="DIR", help="Local JSON export directory (skips Firebase)")
    parser.add_argument("--project", default=DEFAULT_PROJECT, metavar="ID",
                        help="Firebase project ID (or set CLIO_PROJECT)")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, metavar="KEY",
                        help="Firebase public API key (or set CLIO_API_KEY)")
    parser.add_argument("--out", default=str(DATA_OUT), metavar="PATH")
    args = parser.parse_args()
    out = Path(args.out)
    if args.source:
        bake_from_local(Path(args.source), out)
    else:
        bake_from_firebase(out, args.project, args.api_key)


if __name__ == "__main__":
    main()
