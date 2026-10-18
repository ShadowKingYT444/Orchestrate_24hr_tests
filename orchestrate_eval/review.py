"""Evidence-backed manual or externally configured judge reviews. Not official grades."""
from .checks import result

CRITERIA = {
    "architecture": "Describe implemented decomposition and state/data flow, with source references.",
    "prompt_and_tool_design": "Check actual prompts, tool interfaces, validation and tool choice where applicable.",
    "robustness": "Cite measured failure handling, retries, malformed inputs and resource boundaries.",
    "experimental_rigor": "Cite reproducible baselines/ablations and their outcomes, not merely intentions.",
    "transcript_direction_and_ownership": "Cite genuine turns showing user direction, prioritization and ownership of decisions.",
    "transcript_technical_specificity": "Cite requirement-specific reasoning, implementation guidance and concrete tool use.",
    "transcript_iteration_and_verification": "Cite tests, observed failures, revisions and checks that fixes worked.",
    "transcript_safety_and_edge_cases": "Cite genuine discussions and verification of safety, adversarial cases and boundaries."
}

def validate_review(data):
    if not isinstance(data, dict) or data.get("origin") not in {"human", "configured_judge"}:
        raise ValueError("Review origin must be human or configured_judge")
    if not isinstance(data.get("reviewer"), str) or not data["reviewer"].strip():
        raise ValueError("Review must identify reviewer/model")
    entries = data.get("criteria")
    if not isinstance(entries, dict):
        raise ValueError("Review requires criteria object")
    if set(entries) - set(CRITERIA):
        raise ValueError("Unsupported review criteria: " + ", ".join(sorted(set(entries) - set(CRITERIA))))
    checks = []
    for name, guidance in CRITERIA.items():
        entry = entries.get(name)
        if entry is None:
            checks.append(result(name, "unknown", [guidance], "subjective"))
            continue
        if not isinstance(entry, dict) or entry.get("rating") not in {"weak", "adequate", "strong", "unknown", "not_applicable"}:
            raise ValueError(f"Invalid review criterion: {name}")
        evidence = entry.get("evidence", [])
        if not isinstance(evidence, list) or not all(isinstance(e, str) and e.strip() for e in evidence):
            raise ValueError(f"Evidence must be nonempty strings: {name}")
        if entry["rating"] not in {"unknown", "not_applicable"} and not evidence:
            raise ValueError(f"Rating needs source/evaluation evidence: {name}")
        checks.append(result(name, "unknown", [f"{data['origin']} reviewer {data['reviewer']}; advisory rating: {entry['rating']}"] + evidence + ["Evidence references are reviewer claims, not automatically verified"], "subjective"))
    return checks
