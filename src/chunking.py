from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be between 0 and chunk_size - 1")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])(?:[ \t]+|\n+)", text) if sentence.strip()]
        return [
            " ".join(sentences[index : index + self.max_sentences_per_chunk])
            for index in range(0, len(sentences), self.max_sentences_per_chunk)
        ]


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return [chunk for chunk in self._split(text, self.separators) if chunk]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        current_text = current_text.strip()
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text]

        if not remaining_separators:
            return [
                current_text[index : index + self.chunk_size]
                for index in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]
        if not separator:
            return [
                current_text[index : index + self.chunk_size]
                for index in range(0, len(current_text), self.chunk_size)
            ]

        parts = current_text.split(separator)
        if len(parts) == 1:
            return self._split(current_text, remaining_separators[1:])

        chunks: list[str] = []
        pending = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            candidate = part if not pending else pending + separator + part
            if len(candidate) <= self.chunk_size:
                pending = candidate
                continue
            if pending:
                chunks.extend(self._split(pending, remaining_separators[1:]))
            if len(part) > self.chunk_size:
                chunks.extend(self._split(part, remaining_separators[1:]))
                pending = ""
            else:
                pending = part
        if pending:
            chunks.extend(self._split(pending, remaining_separators[1:]))
        return chunks


class HeadingChunker:
    """Split Markdown text into heading-based sections.

    A section starts at an ATX heading (for example ``## Returns``) and
    includes its body until the next heading. Sections larger than
    ``chunk_size`` are recursively split while retaining their heading.
    """

    HEADING_PATTERN = re.compile(r"(?m)^[ \t]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*#?[ \t]*$")

    def __init__(self, chunk_size: int = 500) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        matches = list(self.HEADING_PATTERN.finditer(text))
        if not matches:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text)

        sections: list[tuple[str, str]] = []
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("", preamble))

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            heading = match.group(0).strip()
            body = text[match.end() : end].strip()
            sections.append((heading, body))

        chunks: list[str] = []
        recursive = RecursiveChunker(chunk_size=self.chunk_size)
        for heading, body in sections:
            section = "\n\n".join(part for part in (heading, body) if part)
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue
            if not heading:
                chunks.extend(recursive.chunk(body))
                continue

            heading_prefix = heading + "\n\n"
            available = self.chunk_size - len(heading_prefix)
            if available <= 0:
                chunks.append(heading)
                continue
            body_chunks = RecursiveChunker(chunk_size=available).chunk(body)
            for body_chunk in body_chunks:
                chunks.append(heading_prefix + body_chunk)
        return chunks


# Both names are useful when callers describe the strategy as sections.
HeadingSectionChunker = HeadingChunker
SectionChunker = HeadingChunker


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    magnitude_a = math.sqrt(_dot(vec_a, vec_a))
    magnitude_b = math.sqrt(_dot(vec_b, vec_b))
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=0),
            "by_sentences": SentenceChunker(),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }
        comparison = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            comparison[name] = {
                "count": len(chunks),
                "avg_length": sum(map(len, chunks)) / len(chunks) if chunks else 0.0,
                "chunks": chunks,
            }
        return comparison
