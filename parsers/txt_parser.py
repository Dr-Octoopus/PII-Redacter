"""
Parser for plain .txt files.

This is the simplest parser: the file content IS the text we run
detection on, and character offsets from detection map directly
back onto the file with no translation needed.
"""


def parse_txt(filepath: str) -> str:
    """
    Read a .txt file and return its full content as a string.

    Args:
        filepath: Path to the .txt file on disk.

    Returns:
        The complete file content as a single string.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
