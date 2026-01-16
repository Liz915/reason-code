"""
Simple retrieval module over historical failure cases.

This module is not used in the experiments reported in the paper,
but demonstrates how retrieval-augmented reasoning can be integrated 
in future work.
"""

import json
import os
from typing import List, Dict

# Get the project root directory to ensure reliable path resolution
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "fail_cases.jsonl")

def load_fail_cases(path=LOG_PATH):
    if not os.path.exists(path):
        return []
    out = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    out.append(json.loads(line))
                except:
                    pass
    except Exception:
        return []
    return out

def simple_retrieve(query: str, k: int = 5):
    """
    Simple retrieval mechanism: finds similar errors from historical failure cases.
    
    Intended to provide the LLM with context like "I made a similar mistake before".
    """
    try:
        cases = load_fail_cases()
        if not cases:
            return []
            
        scored = []
        q = query.lower()
        
        for c in cases:
            score = 0
            # Simple keyword-based weighted matching
            prompt_text = c.get("prompt", "") or ""
            candidate_text = c.get("candidate", "") or ""
            stderr_text = c.get("stderr", "") or ""
            
            if q in prompt_text.lower():
                score += 3
            if q in candidate_text.lower():
                score += 2
            if q in stderr_text.lower():
                score += 1
                
            if score > 0:
                scored.append((score, c))
        
        # Sort by score in descending order
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Return the top-k most relevant cases
        return [c for s, c in scored[:k]]
        
    except Exception as e:
        # Retrieval failure should not block the main process
        return []