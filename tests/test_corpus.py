"""
Corpus loader tests. The corpus is the full unlabeled input set for Step 1
("run all texts"). ASPM CSVs expand to one text per row.
"""

from src.corpus import load_corpus
from src.routing import detect_source, route_for_source


def test_corpus_loads_three_sources():
    texts = load_corpus()
    hints = {t.source_hint for t in texts}
    assert hints == {"team_report", "linpeas", "aspm"}


def test_corpus_aspm_rows_expanded():
    texts = load_corpus()
    aspm = [t for t in texts if t.source_hint == "aspm"]
    # Each ASPM CSV row is its own text; origin carries the row marker.
    assert len(aspm) >= 5
    assert all("#row" in t.origin for t in aspm)


def test_corpus_doc_ids_unique():
    texts = load_corpus()
    ids = [t.doc_id for t in texts]
    assert len(ids) == len(set(ids))


def test_corpus_routes_aspm_to_parser():
    texts = load_corpus()
    for t in texts:
        src = detect_source(t.text)
        if t.source_hint == "aspm":
            assert src == "aspm" and route_for_source(src) == "parser"
        else:
            assert route_for_source(detect_source(t.text)) == "llm"
