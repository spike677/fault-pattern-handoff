"""Small deterministic local index over reviewed definitions and historical neighbors."""

from collections import Counter
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def tokens(text):
    text = text.casefold()
    words = re.findall(r"[a-z][a-z0-9_+-]*|\d+", text)
    for segment in re.findall(r"[\u3400-\u9fff]+", text):
        words.extend(segment[i:i + 2] for i in range(max(1, len(segment) - 1)))
    return words


def documents(catalog):
    rows = []
    for mode, card in catalog["modes"].items():
        rows.append({"id": mode, "kind": "unified_mode", "title": card["title"],
                     "status": card.get("knowledge_status", "inherited_v04"), "data": card,
                     "text": json.dumps(card, ensure_ascii=False)})
    for path in sorted((HERE / "history/normalized_mode_cards").glob("*.json")):
        card = json.loads(path.read_bytes())
        rows.append({"id": card["source_id"], "kind": "historical_source", "title": card["title"],
                     "status": card["status"], "data": card, "text": json.dumps(card, ensure_ascii=False)})
    external = HERE / "external/knowledge_items.json"
    if external.exists():
        for card in json.loads(external.read_bytes())["items"]:
            rows.append({"id": card["id"], "kind": "external_knowledge", "title": card["title"],
                         "status": card["evidence_status"], "data": card, "text": json.dumps(card, ensure_ascii=False)})
    return rows


def search(query, catalog, limit=8, kind=None):
    if not query.strip() or not 1 <= limit <= 100:
        raise ValueError("Provide a nonempty query and a limit from 1 to 100")
    docs = [row for row in documents(catalog) if kind is None or row["kind"] == kind]
    term_counts = [Counter(tokens(row["text"])) for row in docs]
    q = set(tokens(query))
    lengths = [sum(c.values()) for c in term_counts]
    avg = sum(lengths) / max(1, len(lengths))
    df = Counter(term for counts in term_counts for term in counts)
    matches = []
    for row, counts, length in zip(docs, term_counts, lengths):
        score = 0.0
        for term in q:
            freq = counts.get(term, 0)
            if freq:
                score += math.log(1 + (len(docs) - df[term] + 0.5) / (df[term] + 0.5)) * freq * 2.2 / (freq + 1.2 * (0.25 + 0.75 * length / max(1, avg)))
        if row["id"].casefold() in query.casefold().split():
            score += 10
        if score:
            matches.append({key: row[key] for key in ("id", "kind", "title", "status")} | {
                "score": round(score, 6), "matched_terms": sorted(q & counts.keys()),
                "use": "candidate_only_not_evidence_or_classification"})
    return sorted(matches, key=lambda r: (-r["score"], r["id"]))[:limit]
