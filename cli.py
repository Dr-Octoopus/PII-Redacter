"""
Command-line entrypoint.

Usage examples
--------------
# Redact everything detected in a PDF:
    python cli.py path/to/document.pdf --output-dir ./output

# Only redact emails and phone numbers:
    python cli.py path/to/document.pdf --include EMAIL,PHONE_NUMBER

# Redact everything EXCEPT pincodes and locations:
    python cli.py path/to/document.pdf --exclude PINCODE,LOCATION

Valid category names for --include / --exclude
----------------------------------------------
  Regex-detected  : EMAIL, PAN_NUMBER, PHONE_NUMBER, DATE_OF_BIRTH,
                    IP_ADDRESS, AADHAAR_NUMBER, CREDIT_CARD, PINCODE
  NER-detected    : PERSON_NAME, LOCATION, ORGANIZATION

This file is intentionally thin: all real work happens in
core.pipeline.process_document(), the same function api.py calls.
Keeping this wrapper thin guarantees the CLI and the API can never
drift out of sync with each other's behaviour.
"""

import argparse

from core.pipeline import process_document


def _parse_csv(value: str) -> list[str]:
    """Split a comma-separated string into a trimmed list of uppercase names."""
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect and redact PII from a document.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Category names for --include / --exclude:\n"
            "  Regex : EMAIL, PAN_NUMBER, PHONE_NUMBER, DATE_OF_BIRTH,\n"
            "          IP_ADDRESS, AADHAAR_NUMBER, CREDIT_CARD, PINCODE\n"
            "  NER   : PERSON_NAME, LOCATION, ORGANIZATION\n"
        ),
    )
    parser.add_argument(
        "filepath",
        help="Path to the input document (.txt, .docx, .pdf, or .xlsx)",
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory to write the redacted file and JSON report into "
             "(default: ./output)",
    )
    parser.add_argument(
        "--include",
        metavar="TYPES",
        default=None,
        help=(
            "Comma-separated list of PII types to detect (all others skipped). "
            "Example: --include EMAIL,PHONE_NUMBER"
        ),
    )
    parser.add_argument(
        "--exclude",
        metavar="TYPES",
        default=None,
        help=(
            "Comma-separated list of PII types to skip. "
            "Ignored when --include is also set. "
            "Example: --exclude PINCODE,LOCATION"
        ),
    )

    args = parser.parse_args()

    include = _parse_csv(args.include) if args.include else None
    exclude = _parse_csv(args.exclude) if args.exclude else None

    redacted_path, report_path = process_document(
        args.filepath,
        args.output_dir,
        include=include,
        exclude=exclude,
    )

    print(f"\nRedacted document : {redacted_path}")
    print(f"JSON report       : {report_path}")


if __name__ == "__main__":
    main()
