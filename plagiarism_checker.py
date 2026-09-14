"""Core plagiarism-checking logic for the paper similarity assignment.

The module keeps the command-line program small and exposes testable functions
for file loading, HTML extraction, normalization, and similarity calculation.
"""

from __future__ import annotations

import math
import sys
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


ENCODINGS: Tuple[str, ...] = ("utf-8-sig", "utf-8", "gb18030")
NGRAM_WEIGHTS: Tuple[Tuple[int, float], ...] = ((1, 0.35), (2, 0.45), (3, 0.20))


class DocumentError(Exception):
    """Raised when an input document cannot be loaded or interpreted."""


class DocumentHTMLParser(HTMLParser):
    """Extract visible document text, preferring GitHub blob code lines."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._current_blob_line: Optional[List[str]] = None
        self._blob_lines: List[str] = []
        self._visible_text: List[str] = []

    def handle_starttag(
        self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]
    ) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        classes = set(attr_map.get("class", "").split())

        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return

        is_github_code_cell = (
            tag == "td"
            and (
                attr_map.get("id", "").startswith("LC")
                or "blob-code" in classes
                or "js-file-line" in classes
            )
        )
        if is_github_code_cell:
            self._current_blob_line = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return

        if tag == "td" and self._current_blob_line is not None:
            self._blob_lines.append("".join(self._current_blob_line))
            self._current_blob_line = None
            return

        if tag in {"p", "br", "div", "tr", "li", "section", "article"}:
            self._visible_text.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return

        if self._current_blob_line is not None:
            self._current_blob_line.append(data)
            return

        if data.strip():
            self._visible_text.append(data)

    @property
    def text(self) -> str:
        """Return the best extracted text from the parsed HTML."""

        meaningful_blob_lines = [line for line in self._blob_lines if line.strip()]
        if meaningful_blob_lines:
            return "\n".join(self._blob_lines)
        return " ".join(self._visible_text)


def read_text_file(file_path: str) -> str:
    """Read text from a file using common Chinese/UTF encodings."""

    path = Path(file_path)
    if not path.is_file():
        raise DocumentError(f"Input file does not exist: {path}")

    last_error: Optional[UnicodeDecodeError] = None
    for encoding in ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except OSError as exc:
            raise DocumentError(f"Cannot read input file: {path}") from exc

    raise DocumentError(f"Cannot decode input file: {path}") from last_error


def looks_like_html(text: str) -> bool:
    """Return whether the document is probably HTML."""

    head = text[:4096].lower()
    return "<!doctype html" in head or "<html" in head or "<body" in head


def extract_document_text(raw_text: str) -> str:
    """Extract article text from plain text or HTML input."""

    if not looks_like_html(raw_text):
        return raw_text

    parser = DocumentHTMLParser()
    parser.feed(raw_text)
    parser.close()
    return parser.text


def normalize_text(text: str) -> str:
    """Normalize text for similarity calculation.

    Punctuation, whitespace, and HTML layout noise are removed. Alphanumeric
    characters from Unicode are preserved, so Chinese text remains intact.
    """

    normalized = unicodedata.normalize("NFKC", text).lower()
    return "".join(char for char in normalized if char.isalnum())


def iter_ngrams(text: str, size: int) -> Iterable[str]:
    """Yield character n-grams, falling back safely for short text."""

    if not text:
        return

    if len(text) < size:
        yield text
        return

    for index in range(len(text) - size + 1):
        yield text[index : index + size]


def cosine_similarity(first_terms: Counter[str], second_terms: Counter[str]) -> float:
    """Calculate cosine similarity between two frequency counters."""

    if not first_terms and not second_terms:
        return 1.0
    if not first_terms or not second_terms:
        return 0.0

    dot_product = sum(
        count * second_terms.get(term, 0) for term, count in first_terms.items()
    )
    first_norm = math.sqrt(sum(count * count for count in first_terms.values()))
    second_norm = math.sqrt(sum(count * count for count in second_terms.values()))
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0
    return dot_product / (first_norm * second_norm)


def calculate_similarity(original_text: str, suspect_text: str) -> float:
    """Calculate a plagiarism repetition rate in the range [0.0, 1.0]."""

    original = normalize_text(original_text)
    suspect = normalize_text(suspect_text)

    if not original and not suspect:
        return 1.0
    if not original or not suspect:
        return 0.0

    weighted_score = 0.0
    for ngram_size, weight in NGRAM_WEIGHTS:
        original_terms = Counter(iter_ngrams(original, ngram_size))
        suspect_terms = Counter(iter_ngrams(suspect, ngram_size))
        weighted_score += weight * cosine_similarity(original_terms, suspect_terms)

    return min(max(weighted_score, 0.0), 1.0)


def check_documents(original_path: str, suspect_path: str) -> float:
    """Load two documents and return their similarity score."""

    original_text = extract_document_text(read_text_file(original_path))
    suspect_text = extract_document_text(read_text_file(suspect_path))
    return calculate_similarity(original_text, suspect_text)


def write_answer(answer_path: str, score: float) -> None:
    """Write the score with two digits after the decimal point."""

    path = Path(answer_path)
    try:
        path.write_text(f"{score:.2f}", encoding="utf-8")
    except OSError as exc:
        raise DocumentError(f"Cannot write answer file: {path}") from exc


def run_cli(arguments: Sequence[str]) -> int:
    """Run the command-line interface and return a process exit code."""

    if len(arguments) != 3:
        print(
            "Usage: python main.py <original_file> <suspect_file> <answer_file>",
            file=sys.stderr,
        )
        return 2

    original_path, suspect_path, answer_path = arguments
    try:
        score = check_documents(original_path, suspect_path)
        write_answer(answer_path, score)
    except DocumentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0
