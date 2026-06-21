"""Parse QQ Music QRC inline word/character timings like 夏(14973,447)."""

from __future__ import annotations

import re
from dataclasses import dataclass

QRC_LINE_HEADER_RE = re.compile(r"^\[(\d+),(\d+)\]")
QRC_INLINE_TIMING_RE = re.compile(r"([^\(\[\]\r\n]+?)\((\d+),(\d+)\)")


@dataclass(frozen=True)
class WordTiming:
    surface: str
    start_ms: int
    duration_ms: int

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


def parse_qrc_inline_timings(segment: str) -> list[WordTiming]:
    timings: list[WordTiming] = []
    for match in QRC_INLINE_TIMING_RE.finditer(segment):
        surface = match.group(1).strip()
        if not surface:
            continue
        timings.append(
            WordTiming(
                surface=surface,
                start_ms=int(match.group(2)),
                duration_ms=int(match.group(3)),
            )
        )
    return timings


def parse_qrc_word_timings_by_line_start(qrc_xml: str) -> dict[int, list[WordTiming]]:
    by_line: dict[int, list[WordTiming]] = {}
    for raw_line in qrc_xml.replace("\r\n", "\n").split("\n"):
        raw_line = raw_line.strip()
        header = QRC_LINE_HEADER_RE.match(raw_line)
        if not header:
            continue
        line_start = int(header.group(1))
        body = raw_line[header.end() :]
        timings = parse_qrc_inline_timings(body)
        if timings:
            by_line[line_start] = timings
    return by_line


def merge_word_timings_for_surface(
    surface: str,
    timings: list[WordTiming],
    cursor: int,
) -> tuple[WordTiming | None, int]:
    if cursor >= len(timings):
        return None, cursor

    collected: list[WordTiming] = []
    consumed = ""
    index = cursor

    while index < len(timings) and len(consumed) < len(surface):
        item = timings[index]
        collected.append(item)
        consumed += item.surface
        index += 1
        if consumed == surface:
            return (
                WordTiming(
                    surface=surface,
                    start_ms=collected[0].start_ms,
                    duration_ms=collected[-1].end_ms - collected[0].start_ms,
                ),
                index,
            )

    return None, cursor
