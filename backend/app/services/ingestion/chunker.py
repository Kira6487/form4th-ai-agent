import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkPiece:
    content: str
    approx_token_count: int
    metadata: dict[str, str | int | None]


def estimate_tokens(text: str) -> int:
    """A deterministic neutral estimate: roughly four UTF-8 characters per token."""
    return max(1, math.ceil(len(text) / 4))


def _split_long_unit(text: str, target: int) -> list[str]:
    words = text.split()
    pieces: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and estimate_tokens(candidate) > target:
            pieces.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        pieces.append(" ".join(current))
    return pieces or [text]


def _units(content: str) -> list[tuple[str, str | None]]:
    units: list[tuple[str, str | None]] = []
    heading: str | None = None
    for block in re.split(r"\n{2,}", content):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if len(lines) == 1 and re.match(r"^#{1,6}\s+", lines[0]):
            heading = lines[0].strip()
            units.append((heading, heading))
            continue
        sentences = re.split(r"(?<=[.!?。！？])\s+", block)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                units.append((sentence, heading))
    return units


def chunk_content(content: str, target_tokens: int = 800, overlap_tokens: int = 100) -> list[ChunkPiece]:
    if not content.strip():
        return []
    expanded: list[tuple[str, str | None]] = []
    for unit, heading in _units(content):
        if estimate_tokens(unit) <= target_tokens:
            expanded.append((unit, heading))
        else:
            expanded.extend((part, heading) for part in _split_long_unit(unit, target_tokens))

    chunks: list[ChunkPiece] = []
    current: list[tuple[str, str | None]] = []
    current_tokens = 0
    for unit, heading in expanded:
        unit_tokens = estimate_tokens(unit)
        if current and current_tokens + unit_tokens > target_tokens:
            chunks.append(_make_piece(current, len(chunks)))
            overlap: list[tuple[str, str | None]] = []
            overlap_count = 0
            for previous in reversed(current):
                previous_tokens = estimate_tokens(previous[0])
                if overlap and overlap_count + previous_tokens > overlap_tokens:
                    break
                overlap.insert(0, previous)
                overlap_count += previous_tokens
                if overlap_count >= overlap_tokens:
                    break
            current = overlap
            current_tokens = overlap_count
        current.append((unit, heading))
        current_tokens += unit_tokens
    if current:
        chunks.append(_make_piece(current, len(chunks)))
    return chunks


def _make_piece(units: list[tuple[str, str | None]], index: int) -> ChunkPiece:
    text = "\n\n".join(unit for unit, _ in units).strip()
    headings = list(dict.fromkeys(heading for _, heading in units if heading))
    return ChunkPiece(
        content=text,
        approx_token_count=estimate_tokens(text),
        metadata={"chunk_index": index, "section": headings[-1] if headings else None},
    )
