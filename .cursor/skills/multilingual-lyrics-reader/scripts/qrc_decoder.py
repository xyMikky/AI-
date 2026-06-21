"""Decode QQ Music QRC lyric files, including local `_qm.qrc` cache files."""

from __future__ import annotations

import html
import re
import zlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from qq_des import triple_transform

QRC_QMC_MAGIC = bytes([0x98, 0x25, 0xB0, 0xAC, 0xE3, 0x02, 0x83, 0x68, 0xE8, 0xFC, 0x6C])

QMC1_KEY = bytes(
    [
        0xC3,
        0x4A,
        0xD6,
        0xCA,
        0x90,
        0x67,
        0xF7,
        0x52,
        0xD8,
        0xA1,
        0x66,
        0x62,
        0x9F,
        0x5B,
        0x09,
        0x00,
        0xC3,
        0x5E,
        0x95,
        0x23,
        0x9F,
        0x13,
        0x11,
        0x7E,
        0xD8,
        0x92,
        0x3F,
        0xBC,
        0x90,
        0xBB,
        0x74,
        0x0E,
        0xC3,
        0x47,
        0x74,
        0x3D,
        0x90,
        0xAA,
        0x3F,
        0x51,
        0xD8,
        0xF4,
        0x11,
        0x84,
        0x9F,
        0xDE,
        0x95,
        0x1D,
        0xC3,
        0xC6,
        0x09,
        0xD5,
        0x9F,
        0xFA,
        0x66,
        0xF9,
        0xD8,
        0xF0,
        0xF7,
        0xA0,
        0x90,
        0xA1,
        0xD6,
        0xF3,
        0xC3,
        0xF3,
        0xD6,
        0xA1,
        0x90,
        0xA0,
        0xF7,
        0xF0,
        0xD8,
        0xF9,
        0x66,
        0xFA,
        0x9F,
        0xD5,
        0x09,
        0xC6,
        0xC3,
        0x1D,
        0x95,
        0xDE,
        0x9F,
        0x84,
        0x11,
        0xF4,
        0xD8,
        0x51,
        0x3F,
        0xAA,
        0x90,
        0x3D,
        0x74,
        0x47,
        0xC3,
        0x0E,
        0x74,
        0xBB,
        0x90,
        0xBC,
        0x3F,
        0x92,
        0xD8,
        0x7E,
        0x11,
        0x13,
        0x9F,
        0x23,
        0x95,
        0x5E,
        0xC3,
        0x00,
        0x09,
        0x5B,
        0x9F,
        0x62,
        0x66,
        0xA1,
        0xD8,
        0x52,
        0xF7,
        0x67,
        0x90,
        0xCA,
        0xD6,
        0x4A,
    ]
)

DES_KEYS = (b"!@#)(NHL", b"123ZXC!@", b"!@#)(*$%")
DES_ENCRYPT_FLAGS = (False, True, False)

QRC_WORD_TIME_RE = re.compile(r"\(\d+,\d+\)")
LRC_TIME_RE = re.compile(r"(?:\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\])+")
QRC_LINE_PREFIX_RE = re.compile(r"^\[(\d+),(\d+)\](.*)$")
LRC_META_PREFIXES = ("[ti:", "[ar:", "[al:", "[by:", "[offset:", "[kana:")
CREDIT_LINE_RE = re.compile(r"^(?:词|曲|作詞|作曲|編曲|编曲)[:：]")
TITLE_ARTIST_RE = re.compile(r"^.+\s[-–—]\s.+\(.+\)$")


@dataclass(frozen=True)
class TimedLyricLine:
    text: str
    start_ms: int
    duration_ms: int

    @property
    def end_ms(self) -> int:
        return self.start_ms + self.duration_ms


def qmc_decode(data: bytearray) -> bytearray:
    for index in range(len(data)):
        key = QMC1_KEY[(index % 0x7FFF) & 0x7F] if index > 0x7FFF else QMC1_KEY[index & 0x7F]
        data[index] ^= key
    return data


def decode_qrc_bytes(data: bytes) -> bytes:
    payload = bytearray(data)
    if payload[: len(QRC_QMC_MAGIC)] == QRC_QMC_MAGIC:
        payload = qmc_decode(payload)
        payload = payload[len(QRC_QMC_MAGIC) :]

    usable = len(payload) // 8 * 8
    if usable <= 0:
        raise ValueError("QRC 数据过短，无法解密")
    body = bytearray(payload[:usable])
    triple_transform(body, DES_ENCRYPT_FLAGS, DES_KEYS)
    return zlib.decompress(bytes(body))


def decode_qrc_file(path: Path) -> str:
    xml_bytes = decode_qrc_bytes(path.read_bytes())
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return xml_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return xml_bytes.decode("utf-8", errors="replace")


def _strip_qrc_timing(text: str) -> str:
    text = html.unescape(text)
    text = QRC_WORD_TIME_RE.sub("", text)
    text = LRC_TIME_RE.sub("", text)
    text = text.replace("\\n", "\n")
    return text.strip()


def _is_metadata_line(text: str) -> bool:
    lowered = text.lower()
    if any(lowered.startswith(prefix) for prefix in LRC_META_PREFIXES):
        return True
    if CREDIT_LINE_RE.match(text):
        return True
    if TITLE_ARTIST_RE.match(text):
        return True
    return False


def parse_qrc_raw_line(raw_line: str) -> TimedLyricLine | None:
    raw_line = raw_line.strip()
    if not raw_line:
        return None

    match = QRC_LINE_PREFIX_RE.match(raw_line)
    if not match:
        return None

    start_ms = int(match.group(1))
    duration_ms = int(match.group(2))
    text = _strip_qrc_timing(match.group(3))
    if not text:
        return None
    if _is_metadata_line(text):
        return None
    if text.startswith(("[", "{")) and ":" in text and not re.search(r"[ぁ-ゖァ-ヺ一-龯]", text):
        return None
    return TimedLyricLine(text=text, start_ms=start_ms, duration_ms=duration_ms)


def extract_timed_lines_from_qrc_xml(xml_text: str) -> list[TimedLyricLine]:
    raw_lines: list[str] = []

    try:
        root = ET.fromstring(xml_text)
        for element in root.iter():
            content = element.get("LyricContent") or element.text or ""
            if not content:
                continue
            raw_lines.extend(content.replace("\\n", "\n").splitlines())
    except ET.ParseError:
        for attr_value in re.findall(r'LyricContent="([\s\S]*?)"', xml_text):
            raw_lines.extend(attr_value.replace("\\n", "\n").splitlines())

    if not raw_lines:
        raise ValueError("QRC XML 中未找到歌词正文")

    timed_lines: list[TimedLyricLine] = []
    for raw_line in raw_lines:
        parsed = parse_qrc_raw_line(raw_line)
        if parsed:
            timed_lines.append(parsed)

    if not timed_lines:
        raise ValueError("QRC 中未找到带时间轴的歌词行")
    return timed_lines


def extract_lyric_lines_from_qrc_xml(xml_text: str) -> list[str]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        match = re.search(r'LyricContent="([\s\S]*?)"', xml_text)
        if not match:
            raise ValueError("无法从 QRC XML 中提取 LyricContent") from None
        content = _strip_qrc_timing(match.group(1))
        return [line.strip() for line in content.splitlines() if line.strip()]

    lines: list[str] = []
    for element in root.iter():
        if element.tag.endswith("LyricContent") or element.get("LyricContent"):
            content = element.get("LyricContent") or (element.text or "")
            content = _strip_qrc_timing(content)
            lines.extend(line.strip() for line in content.splitlines() if line.strip())
        elif element.text and "LyricContent" in (element.attrib or {}):
            content = _strip_qrc_timing(element.attrib["LyricContent"])
            lines.extend(line.strip() for line in content.splitlines() if line.strip())

    if not lines:
        for attr_value in re.findall(r'LyricContent="([\s\S]*?)"', xml_text):
            content = _strip_qrc_timing(attr_value)
            lines.extend(line.strip() for line in content.splitlines() if line.strip())

    if not lines:
        raise ValueError("QRC XML 中未找到歌词正文")
    return lines


def read_qrc_lyric_lines(path: Path) -> list[str]:
    return [line.text for line in read_qrc_timed_lines(path)]


def read_qrc_timed_lines(path: Path) -> list[TimedLyricLine]:
    xml_text = decode_qrc_file(path)
    return extract_timed_lines_from_qrc_xml(xml_text)


def is_probably_encrypted_qrc(path: Path) -> bool:
    if path.suffix.lower() != ".qrc":
        return False
    try:
        head = path.read_bytes()[: len(QRC_QMC_MAGIC)]
    except OSError:
        return False
    return head == QRC_QMC_MAGIC
