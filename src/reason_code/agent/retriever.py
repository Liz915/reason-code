import json
import os
from typing import List, Dict

def load_fail_cases(path="logs/fail_cases.jsonl"):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except:
                pass
    return out

def simple_retrieve(query: str, k: int = 5):
    cases = load_fail_cases()
    scored = []
    q = query.lower()
    for c in cases:
        score = 0
        if q in (c.get("prompt","").lower()):
            score += 3
        if q in (c.get("candidate","").lower()):
            score += 2
        if q in (c.get("stderr","").lower()):
            score += 1
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for s,c in scored[:k] if s>0]