import re
from dateutil import parser as dateparser
from typing import Dict, Any, List


def clause_extractor(text: str, clause_keywords: List[str] = None) -> Dict[str, Any]:
    """Extract clauses from text that contain any of the clause_keywords.
    Returns dict with clauses: [{page, text}]
    """
    clause_keywords = clause_keywords or ["warranty", "liability", "term", "termination"]
    sentences = re.split(r"(?<=[.!?])\\s+", text)
    matches = [s for s in sentences if any(k.lower() in s.lower() for k in clause_keywords)]
    return {"clauses": [{"text": m} for m in matches]}


def date_calculator(text: str) -> Dict[str, Any]:
    """Parse the first date-like expression in text and return ISO date.
    Returns {date: iso, original: str}
    """
    # naive find of date tokens
    tokens = re.findall(r"\b\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}\b|\b\w+ \d{1,2},? \d{4}\b", text)
    if not tokens:
        return {"date": None, "original": None}
    tok = tokens[0]
    try:
        dt = dateparser.parse(tok)
        return {"date": dt.date().isoformat(), "original": tok}
    except Exception:
        return {"date": None, "original": tok}


def doc_compare(text_a: str, text_b: str) -> Dict[str, Any]:
    """Return a simple token-overlap similarity score and diffs.
    """
    a = set(re.findall(r"\w+", text_a.lower()))
    b = set(re.findall(r"\w+", text_b.lower()))
    if not a or not b:
        score = 0.0
    else:
        score = len(a & b) / max(len(a | b), 1)
    return {"score": score, "shared_terms": list(a & b)[:20]}


STATUTE_DB = {
    "contract": "Statute 12.3: On contracts, parties must...",
    "employment": "Statute 7.1: Employment laws require...",
}


def statute_lookup(query: str) -> Dict[str, Any]:
    # naive keyword lookup
    keys = [k for k in STATUTE_DB.keys() if k in query.lower()]
    results = [STATUTE_DB[k] for k in keys]
    return {"results": results}
