import re


def clean_extracted_text(text: str) -> str:
    """
    Cleans raw extracted text from resumes/job descriptions:
    - Normalizes unicode whitespace and control characters.
    - Strips common page number artifacts (e.g. 'Page 1 of 3').
    - Collapses excessive blank lines (3+ consecutive newlines -> 2 newlines).
    - Preserves logical paragraph structures.
    """
    if not text:
        return ""

    # Replace non-breaking spaces and other whitespace variations with standard space
    text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")

    # Remove non-printable control characters except newline and tab
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Process line by line to clean header/footer page numbers and inline spaces
    cleaned_lines = []
    page_number_pattern = re.compile(
        r"^(?:page\s+\d+(?:\s+(?:of|/)\s+\d+)?|-?\s*\d+\s*-?|page\s*\|\s*\d+)$",
        re.IGNORECASE
    )

    for line in text.split("\n"):
        # Strip trailing/leading spaces on each line
        trimmed_line = line.strip()

        # Filter out standalone page number lines
        if page_number_pattern.match(trimmed_line):
            continue

        # Collapse multiple horizontal spaces on the line
        trimmed_line = re.sub(r"[ \t]+", " ", trimmed_line)
        cleaned_lines.append(trimmed_line)

    joined_text = "\n".join(cleaned_lines)

    # Collapse 3 or more consecutive newlines down to 2 newlines
    joined_text = re.sub(r"\n{3,}", "\n\n", joined_text)

    return joined_text.strip()
