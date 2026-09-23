"""
Merges detections from the regex detector and the NER detector into
a single, clean, sorted list -- with overlapping detections resolved.

Why overlaps happen: e.g. a 12-digit Aadhaar number and a 6-digit
PINCODE pattern can both match inside the same longer digit string.
When two detections cover the same (or overlapping) text span, we
keep only the higher-confidence one rather than reporting both.
"""


def _spans_overlap(a: dict, b: dict) -> bool:
    """Return True if detection `a` and `b` cover overlapping text."""
    return a["start"] < b["end"] and b["start"] < a["end"]


def merge_detections(regex_hits: list[dict],
                      ner_hits: list[dict]) -> list[dict]:
    """
    Combine regex and NER detections, removing overlaps.

    Args:
        regex_hits: Detections from detect_regex_pii().
        ner_hits: Detections from detect_ner_pii().

    Returns:
        A single list of detections, sorted by their position (start
        offset) in the document, with overlapping spans collapsed
        down to the single highest-confidence detection.
    """
    all_hits = regex_hits + ner_hits

    # Sort by start offset so overlap-checking (and the final report)
    # reads the document in natural order, top to bottom.
    all_hits.sort(key=lambda hit: hit["start"])

    merged: list[dict] = []

    for hit in all_hits:
        overlap_index = None
        for i, kept in enumerate(merged):
            if _spans_overlap(hit, kept):
                overlap_index = i
                break

        if overlap_index is None:
            merged.append(hit)
        else:
            existing = merged[overlap_index]
            # Preference rule: if categories differ on overlapping span,
            # prefer ORGANIZATION / LOCATION over PERSON_NAME if confidences are close
            if existing["category"] == "PERSON_NAME" and hit["category"] in {"ORGANIZATION", "LOCATION"}:
                if hit["confidence"] >= existing["confidence"] - 0.05:
                    merged[overlap_index] = hit
                    continue
            elif hit["category"] == "PERSON_NAME" and existing["category"] in {"ORGANIZATION", "LOCATION"}:
                if existing["confidence"] >= hit["confidence"] - 0.05:
                    continue

            if hit["confidence"] > existing["confidence"]:
                merged[overlap_index] = hit

    return merged
