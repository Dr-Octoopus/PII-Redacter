"""
Builds the structured JSON report required by the problem statement,
and generates "warnings" -- this is the piece that satisfies the
"tool must flag its own limitations" requirement. A human reviewer
reads the warnings list to know exactly where to double-check the
tool's work by hand, instead of blindly trusting it.
"""

import json

# Any detection below this confidence is called out individually as
# a warning, so a reviewer knows exactly which specific match to
# double-check by eye.
LOW_CONFIDENCE_THRESHOLD = 0.75


def build_json_report(entities: list[dict],
                       source_filename: str,
                       review_candidates: list[dict] | None = None,
                       extra_warnings: list[str] | None = None) -> dict:
    """
    Assemble the final JSON report structure.

    Args:
        entities: The merged list of PII detections (from merge.py).
        source_filename: Name of the original input file, included
            for traceability.
        extra_warnings: Warnings raised earlier in the pipeline, e.g.
            by a parser that couldn't read a page (unsupported/
            scanned content). Passed in from outside since parsers
            are the ones that know about parsing-level problems.

    Returns:
        A dict ready to be serialized to JSON, containing the entity
        list and a warnings list.
    """
    warnings = list(extra_warnings) if extra_warnings else []

    for entity in entities:
        if entity["confidence"] < LOW_CONFIDENCE_THRESHOLD:
            warnings.append(
                f"Low-confidence {entity['category']} detection "
                f"('{entity['text']}') at offset {entity['start']} -- "
                f"please verify manually."
            )

    review_items = list(review_candidates) if review_candidates else []
    for candidate in review_items:
        warnings.append(
            f"Review-only {candidate['category']} candidate "
            f"('{candidate['text']}') at offset {candidate['start']} "
            f"scored {candidate['confidence']:.0%} "
            f"(raw detector score {candidate.get('raw_confidence', 0):.1%}) -- "
            f"not redacted; please verify manually."
        )

    if not entities:
        warnings.append(
            "No PII entities were detected. If this document is "
            "expected to contain PII, please review it manually -- "
            "the tool may have missed content in an unsupported "
            "format (e.g. scanned/image-only pages)."
        )

    return {
        "source_file": source_filename,
        "total_entities_found": len(entities),
        "entities": entities,
        "review_candidates": review_items,
        "warnings": warnings,
    }


def save_report(report: dict, output_path: str) -> None:
    """
    Write the report dict to disk as formatted JSON.

    Args:
        report: The dict produced by build_json_report().
        output_path: Where to write the .json file.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
