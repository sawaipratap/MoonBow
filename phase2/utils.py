"""
Shared utility for robustly parsing an EvaluationResult JSON from raw LLM output.
Handles: markdown fences, text preamble, single-quotes, trailing commas.
"""
import json
import re
from phase2.state import EvaluationResult


def parse_evaluation(raw: str, node_name: str) -> EvaluationResult:
    """
    Extracts and parses an EvaluationResult JSON from raw LLM output.
    Strategy:
      1. Find the outermost { ... } block.
      2. Attempt direct parse.
      3. If that fails, try light repairs (single-quotes → double, trailing commas).
      4. If all fails, return a failed result with a truncated snippet of the raw output.
    """
    # Step 1: find outermost JSON object boundaries
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return _fail(node_name, raw, "No JSON object found in output")

    candidate = raw[start:end + 1]

    # Step 2: direct parse
    try:
        return _build(json.loads(candidate))
    except json.JSONDecodeError:
        pass

    # Step 3: light repairs
    repaired = candidate
    # Replace Python-style True/False/None
    repaired = repaired.replace(": True", ": true").replace(": False", ": false").replace(": None", ": null")
    # Remove trailing commas before ] or }
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
    # Convert single-quoted strings to double-quoted
    repaired = re.sub(r"'([^']*)'", r'"\1"', repaired)

    try:
        return _build(json.loads(repaired))
    except json.JSONDecodeError as e:
        print(f"[{node_name}] Failed to parse LLM output after repair: {e}")
        return _fail(node_name, raw, str(e))


def _build(data: dict) -> EvaluationResult:
    return EvaluationResult(
        passed=bool(data.get("passed", False)),
        feedback=str(data.get("feedback", "")),
        confidence_score=float(data.get("confidence_score", 1.0)),
    )


def _fail(node_name: str, raw: str, reason: str) -> EvaluationResult:
    snippet = raw[:350].replace("\n", " ")
    return EvaluationResult(
        passed=False,
        feedback=f"[{node_name}] Parse failed ({reason}). Raw snippet: {snippet}",
        confidence_score=0.0,
    )
