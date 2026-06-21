#!/usr/bin/env python3
"""Build a standalone multilingual lyrics word-reader HTML file.

The script uses SudachiPy for Japanese when available, and a generic tokenizer
for Chinese/Cantonese, Korean, English, and other lyric text.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


try:
    from sudachipy import Dictionary, SplitMode  # type: ignore
except Exception:  # pragma: no cover - import depends on local environment
    Dictionary = None
    SplitMode = None

try:
    import pycantonese  # type: ignore
except Exception:  # pragma: no cover - import depends on local environment
    pycantonese = None

try:
    from opencc import OpenCC  # type: ignore
except Exception:  # pragma: no cover - import depends on local environment
    OpenCC = None


HIRAGANA_START = ord("ぁ")
HIRAGANA_END = ord("ゖ")
KATAKANA_START = ord("ァ")
KATAKANA_END = ord("ヶ")

LANGUAGE_SPEECH_LANG = {
    "ja": "ja-JP",
    "jp": "ja-JP",
    "japanese": "ja-JP",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "cn": "zh-CN",
    "mandarin": "zh-CN",
    "yue": "zh-HK",
    "cantonese": "zh-HK",
    "粤语": "zh-HK",
    "ko": "ko-KR",
    "kr": "ko-KR",
    "korean": "ko-KR",
    "en": "en-US",
    "english": "en-US",
}


@dataclass
class Token:
    surface: str
    lemma: str
    hira: str
    kata: str
    romaji: str
    zh: str
    lineIndex: int
    tokenIndex: int
    globalIndex: int
    pos: str
    startMs: int | None = None
    durationMs: int | None = None


@dataclass
class LyricEntry:
    text: str
    start_ms: int | None = None
    duration_ms: int | None = None
    audio_clip: str | None = None


def kata_to_hira(text: str) -> str:
    chars: list[str] = []
    for char in text:
        code = ord(char)
        if KATAKANA_START <= code <= KATAKANA_END:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def hira_to_kata(text: str) -> str:
    chars: list[str] = []
    for char in text:
        code = ord(char)
        if HIRAGANA_START <= code <= HIRAGANA_END:
            chars.append(chr(code + 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def is_japanese_text(text: str) -> bool:
    return bool(re.search(r"[ぁ-ゖァ-ヺ]", text))


def normalize_reading(reading: str, fallback: str) -> tuple[str, str]:
    if not reading or reading == "*":
        reading = fallback
    kata = hira_to_kata(reading)
    hira = kata_to_hira(kata)
    return hira, kata


ROMAJI_DIGRAPHS = {
    "きゃ": "kya",
    "きゅ": "kyu",
    "きょ": "kyo",
    "しゃ": "sha",
    "しゅ": "shu",
    "しょ": "sho",
    "ちゃ": "cha",
    "ちゅ": "chu",
    "ちょ": "cho",
    "にゃ": "nya",
    "にゅ": "nyu",
    "にょ": "nyo",
    "ひゃ": "hya",
    "ひゅ": "hyu",
    "ひょ": "hyo",
    "みゃ": "mya",
    "みゅ": "myu",
    "みょ": "myo",
    "りゃ": "rya",
    "りゅ": "ryu",
    "りょ": "ryo",
    "ぎゃ": "gya",
    "ぎゅ": "gyu",
    "ぎょ": "gyo",
    "じゃ": "ja",
    "じゅ": "ju",
    "じょ": "jo",
    "びゃ": "bya",
    "びゅ": "byu",
    "びょ": "byo",
    "ぴゃ": "pya",
    "ぴゅ": "pyu",
    "ぴょ": "pyo",
}


ROMAJI_MONOGRAPHS = {
    "あ": "a",
    "い": "i",
    "う": "u",
    "え": "e",
    "お": "o",
    "か": "ka",
    "き": "ki",
    "く": "ku",
    "け": "ke",
    "こ": "ko",
    "さ": "sa",
    "し": "shi",
    "す": "su",
    "せ": "se",
    "そ": "so",
    "た": "ta",
    "ち": "chi",
    "つ": "tsu",
    "て": "te",
    "と": "to",
    "な": "na",
    "に": "ni",
    "ぬ": "nu",
    "ね": "ne",
    "の": "no",
    "は": "ha",
    "ひ": "hi",
    "ふ": "fu",
    "へ": "he",
    "ほ": "ho",
    "ま": "ma",
    "み": "mi",
    "む": "mu",
    "め": "me",
    "も": "mo",
    "や": "ya",
    "ゆ": "yu",
    "よ": "yo",
    "ら": "ra",
    "り": "ri",
    "る": "ru",
    "れ": "re",
    "ろ": "ro",
    "わ": "wa",
    "を": "wo",
    "ん": "n",
    "が": "ga",
    "ぎ": "gi",
    "ぐ": "gu",
    "げ": "ge",
    "ご": "go",
    "ざ": "za",
    "じ": "ji",
    "ず": "zu",
    "ぜ": "ze",
    "ぞ": "zo",
    "だ": "da",
    "ぢ": "ji",
    "づ": "zu",
    "で": "de",
    "ど": "do",
    "ば": "ba",
    "び": "bi",
    "ぶ": "bu",
    "べ": "be",
    "ぼ": "bo",
    "ぱ": "pa",
    "ぴ": "pi",
    "ぷ": "pu",
    "ぺ": "pe",
    "ぽ": "po",
    "ぁ": "a",
    "ぃ": "i",
    "ぅ": "u",
    "ぇ": "e",
    "ぉ": "o",
    "ゃ": "ya",
    "ゅ": "yu",
    "ょ": "yo",
}


def kana_to_romaji(text: str) -> str:
    hira = kata_to_hira(text)
    result: list[str] = []
    double_next = False
    last_vowel = ""
    index = 0

    while index < len(hira):
        char = hira[index]
        if char == "っ":
            double_next = True
            index += 1
            continue
        if char == "ー":
            if last_vowel:
                result.append(last_vowel)
            index += 1
            continue

        pair = hira[index : index + 2]
        if pair in ROMAJI_DIGRAPHS:
            roman = ROMAJI_DIGRAPHS[pair]
            index += 2
        else:
            roman = ROMAJI_MONOGRAPHS.get(char, char)
            index += 1

        if double_next and roman and roman[0].isalpha():
            roman = roman[0] + roman
            double_next = False

        vowel_match = re.search(r"[aeiou]$", roman)
        if vowel_match:
            last_vowel = vowel_match.group(0)
        result.append(roman)

    return "".join(result)


def speech_lang_for(language: str | None, speech_lang: str | None) -> str:
    if speech_lang:
        return speech_lang
    if not language:
        return "ja-JP"
    return LANGUAGE_SPEECH_LANG.get(language.lower(), language)


def is_cantonese_language(language: str | None) -> bool:
    if not language:
        return False
    return language.lower() in {"yue", "cantonese", "zh-hk", "zh_hk", "粤语"}


def jyutping_chunks(text: str) -> list[tuple[str, str]]:
    if pycantonese is None:
        return []

    source = text
    if OpenCC is not None:
        try:
            source = OpenCC("s2hk").convert(text)
        except Exception:
            source = text

    chunks: list[tuple[str, str]] = []
    for surface, jyutping in pycantonese.characters_to_jyutping(source):
        if not surface.strip():
            continue
        chunks.append((surface, (jyutping or "").strip()))
    return chunks


def align_converted_chunks_to_original(original: str, converted_chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    cursor = 0
    original_no_space = original
    for converted_surface, jyutping in converted_chunks:
        target_len = len(converted_surface)
        if target_len <= 0:
            continue

        while cursor < len(original_no_space) and original_no_space[cursor].isspace():
            cursor += 1

        original_surface = original_no_space[cursor : cursor + target_len]
        cursor += target_len
        if not original_surface.strip():
            continue
        chunks.append((original_surface, jyutping))
    return chunks


def cantonese_tokenize_line(line: str, line_index: int, global_start: int) -> list[Token]:
    converted_chunks = jyutping_chunks(line)
    if not converted_chunks:
        return generic_tokenize_line(line, line_index, global_start)
    chunks = align_converted_chunks_to_original(line, converted_chunks)

    tokens: list[Token] = []
    token_index = 0
    for surface, jyutping in chunks:
        tokens.append(
            Token(
                surface=surface,
                lemma=surface,
                hira="",
                kata="",
                romaji=" ".join(re.findall(r"[a-z]+[1-6]?", jyutping)),
                zh="",
                lineIndex=line_index,
                tokenIndex=token_index,
                globalIndex=global_start + token_index,
                pos="jyutping",
            )
        )
        token_index += 1
    return tokens


def load_vocab(path: Path | None) -> dict[tuple[str, str], dict[str, str]]:
    if not path or not path.exists():
        return {}

    result: dict[tuple[str, str], dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            surface = (row.get("surface") or "").strip()
            lemma = (row.get("lemma") or surface).strip()
            if not surface:
                continue
            result[(surface, lemma)] = {
                "hira": (row.get("hira") or "").strip(),
                "kata": (row.get("kata") or "").strip(),
                "romaji": (row.get("romaji") or "").strip(),
                "zh": (row.get("zh") or "").strip(),
            }
    return result


def apply_vocab(token: Token, vocab: dict[tuple[str, str], dict[str, str]]) -> Token:
    entry = vocab.get((token.surface, token.lemma)) or vocab.get((token.surface, token.surface))
    if not entry:
        return token

    hira = entry.get("hira") or token.hira
    kata = entry.get("kata") or token.kata
    if hira and not kata:
        kata = hira_to_kata(hira)
    if kata and not hira:
        hira = kata_to_hira(kata)

    token.hira = hira
    token.kata = kata
    token.romaji = entry.get("romaji") or (kana_to_romaji(hira) if hira else token.romaji)
    token.zh = entry.get("zh") or token.zh
    return token


def sudachi_tokenize_line(line: str, line_index: int, global_start: int) -> list[Token]:
    tokenizer = Dictionary().create()
    tokens: list[Token] = []
    token_index = 0

    for morpheme in tokenizer.tokenize(line, SplitMode.C):
        surface = morpheme.surface()
        if not surface.strip():
            continue
        lemma = morpheme.dictionary_form()
        reading = morpheme.reading_form()
        hira, kata = normalize_reading(reading, surface)
        pos = "-".join(part for part in morpheme.part_of_speech() if part and part != "*")
        tokens.append(
            Token(
                surface=surface,
                lemma=lemma,
                hira=hira,
                kata=kata,
                romaji=kana_to_romaji(hira),
                zh="",
                lineIndex=line_index,
                tokenIndex=token_index,
                globalIndex=global_start + token_index,
                pos=pos,
            )
        )
        token_index += 1
    return tokens


GROUP_RE = re.compile(
    r"[A-Za-z]+(?:['’-][A-Za-z]+)*"
    r"|[0-9]+(?:[.,:][0-9]+)*"
    r"|[ぁ-ゖー]+"
    r"|[ァ-ヺー]+"
    r"|[一-龯々〆ヵヶ]+"
    r"|[가-힣]+"
    r"|[^\s]"
)
LRC_TIME_RE = re.compile(r"(?:\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\])+")
LRC_TIMESTAMP_RE = re.compile(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]")
QRC_LINE_TIME_RE = re.compile(r"^\[\d+,\d+\]")
QRC_WORD_TIME_RE = re.compile(r"\(\d+,\d+\)")
LRC_META_PREFIXES = ("[ti:", "[ar:", "[al:", "[by:", "[offset:", "[kana:")
CREDIT_LINE_RE = re.compile(r"^(?:词|曲|作詞|作曲|編曲|编曲)[:：]")
TITLE_ARTIST_RE = re.compile(r"^.+\s[-–—]\s.+\(.+\)$")
XML_TAG_RE = re.compile(r"<[^>]+>")


def generic_tokenize_line(line: str, line_index: int, global_start: int) -> list[Token]:
    tokens: list[Token] = []
    for token_index, match in enumerate(GROUP_RE.finditer(line)):
        surface = match.group(0)
        if is_japanese_text(surface):
            hira, kata = normalize_reading(surface, surface)
            romaji = kana_to_romaji(hira)
        else:
            hira = ""
            kata = ""
            romaji = ""
        tokens.append(
            Token(
                surface=surface,
                lemma=surface,
                hira=hira,
                kata=kata,
                romaji=romaji,
                zh="",
                lineIndex=line_index,
                tokenIndex=token_index,
                globalIndex=global_start + token_index,
                pos="generic",
            )
        )
    return tokens


def decode_lyric_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "lyrics",
        raw,
        0,
        min(len(raw), 1),
        "无法按常见文本编码读取。若这是 QQ 音乐 `_qm.qrc` 缓存，请确认文件完整；也可先用 LyricTools 导出明文歌词。",
    )


def clean_lyric_line(line: str) -> str:
    line = html.unescape(line.strip())
    line = XML_TAG_RE.sub("", line)
    line = LRC_TIME_RE.sub("", line)
    line = QRC_LINE_TIME_RE.sub("", line)
    line = QRC_WORD_TIME_RE.sub("", line)
    line = line.replace("\\n", "\n")
    return line.strip()


def is_metadata_line(line: str) -> bool:
    lowered = line.lower()
    if any(lowered.startswith(prefix) for prefix in LRC_META_PREFIXES):
        return True
    if CREDIT_LINE_RE.match(line):
        return True
    if TITLE_ARTIST_RE.match(line):
        return True
    return False


def lrc_timestamp_to_ms(minutes: str, seconds: str, fraction: str | None) -> int:
    total_ms = int(minutes) * 60_000 + int(seconds) * 1_000
    if not fraction:
        return total_ms
    if len(fraction) == 2:
        return total_ms + int(fraction) * 10
    if len(fraction) == 3:
        return total_ms + int(fraction)
    return total_ms + int(fraction.ljust(3, "0")[:3])


def parse_lrc_timed_entries(text: str) -> list[LyricEntry]:
    offset_ms = 0
    timed: list[tuple[int, str]] = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        lowered = stripped.lower()
        if lowered.startswith("[offset:"):
            match = re.search(r"\[offset:\s*(-?\d+)", stripped, re.IGNORECASE)
            if match:
                offset_ms = int(match.group(1))
            continue

        if any(lowered.startswith(prefix) for prefix in LRC_META_PREFIXES):
            continue

        match = LRC_TIMESTAMP_RE.search(stripped)
        if not match:
            continue

        start_ms = lrc_timestamp_to_ms(match.group(1), match.group(2), match.group(3)) + offset_ms
        text_part = LRC_TIMESTAMP_RE.sub("", stripped).strip()
        text_part = html.unescape(text_part)
        if not text_part or text_part == "//":
            continue
        if is_metadata_line(text_part):
            continue
        timed.append((start_ms, text_part))

    if not timed:
        return normalize_lyric_lines(text.splitlines())

    entries: list[LyricEntry] = []
    for index, (start_ms, lyric_text) in enumerate(timed):
        if index + 1 < len(timed):
            duration_ms = max(400, timed[index + 1][0] - start_ms)
        else:
            duration_ms = 6_000
        entries.append(LyricEntry(text=lyric_text, start_ms=start_ms, duration_ms=duration_ms))
    return entries


def normalize_lyric_lines(raw_lines: Iterable[str]) -> list[LyricEntry]:
    lines: list[LyricEntry] = []
    for raw_line in raw_lines:
        cleaned = clean_lyric_line(raw_line)
        if not cleaned:
            continue
        if is_metadata_line(cleaned):
            continue
        if cleaned.startswith(("[", "{")) and ":" in cleaned and not re.search(r"[ぁ-ゖァ-ヺ一-龯]", cleaned):
            continue
        for part in cleaned.splitlines():
            part = part.strip()
            if part:
                lines.append(LyricEntry(text=part))
    return lines


def read_lyric_entries(path: Path) -> list[LyricEntry]:
    scripts_dir = Path(__file__).resolve().parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    import qrc_decoder

    if qrc_decoder.is_probably_encrypted_qrc(path):
        return [
            LyricEntry(text=line.text, start_ms=line.start_ms, duration_ms=line.duration_ms)
            for line in qrc_decoder.read_qrc_timed_lines(path)
        ]

    text = decode_lyric_text(path)
    if path.suffix.lower() == ".lrc":
        return parse_lrc_timed_entries(text)
    return normalize_lyric_lines(text.splitlines())


def read_lyric_lines(path: Path) -> list[str]:
    return [entry.text for entry in read_lyric_entries(path)]


def read_lrc_title(text: str) -> str | None:
    match = re.search(r"\[ti:([^\]]+)\]", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def qq_lyric_cache_dirs() -> list[Path]:
    dirs: list[Path] = []
    for drive in ("C", "D", "E", "F", "G"):
        candidate = Path(f"{drive}:/QQMusicCache/QQMusicLyricNew")
        if candidate.is_dir():
            dirs.append(candidate)
    home_cache = Path.home() / "QQMusicCache" / "QQMusicLyricNew"
    if home_cache.is_dir() and home_cache not in dirs:
        dirs.append(home_cache)
    return dirs


def score_qrc_candidate(name: str, title_tokens: list[str], lyrics_stem: str) -> int:
    name_lower = name.lower()
    score = sum(1 for token in title_tokens if token in name_lower)
    stem_tokens = [
        part
        for part in re.split(r"[^\w\u3040-\u30ff\u4e00-\u9fff]+", lyrics_stem.lower())
        if len(part) >= 3
    ]
    score += sum(1 for part in stem_tokens if part in name_lower)
    return score


def resolve_qrc_timing_path(lyrics_path: Path, explicit: Path | None) -> Path | None:
    if explicit:
        explicit = explicit.resolve()
        if explicit.is_file():
            return explicit
        raise FileNotFoundError(f"QRC 词级时间轴文件不存在：{explicit}")

    if lyrics_path.suffix.lower() == ".qrc" and lyrics_path.name.endswith("_qm.qrc"):
        return lyrics_path.resolve()

    if lyrics_path.suffix.lower() != ".lrc":
        return None

    folder = lyrics_path.parent
    stem = lyrics_path.stem
    for candidate in [folder / f"{stem}_qm.qrc", *folder.glob(f"*{stem}*_qm.qrc")]:
        if candidate.is_file():
            return candidate.resolve()

    title = read_lrc_title(decode_lyric_text(lyrics_path))
    title_tokens: list[str] = []
    if title:
        title_key = re.sub(r"\s+", " ", title).lower()
        title_tokens = [
            part for part in re.split(r"[^\w\u3040-\u30ff\u4e00-\u9fff]+", title_key) if len(part) >= 3
        ]

    best: Path | None = None
    best_score = 0
    for cache_dir in qq_lyric_cache_dirs():
        for candidate in cache_dir.glob("*_qm.qrc"):
            score = score_qrc_candidate(candidate.name, title_tokens, stem)
            if score > best_score:
                best = candidate
                best_score = score

    return best.resolve() if best is not None and best_score >= 2 else None


def load_qrc_word_timings(qrc_path: Path) -> dict[int, list]:
    scripts_dir = Path(__file__).resolve().parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    import qrc_decoder
    from word_timing import parse_qrc_word_timings_by_line_start

    if qrc_decoder.is_probably_encrypted_qrc(qrc_path):
        xml_text = qrc_decoder.decode_qrc_file(qrc_path)
    else:
        xml_text = decode_lyric_text(qrc_path)
    return parse_qrc_word_timings_by_line_start(xml_text)


def lookup_line_word_timings(line_start_ms: int, timings_by_line: dict[int, list]) -> list | None:
    if line_start_ms in timings_by_line:
        return timings_by_line[line_start_ms]
    for key, timings in timings_by_line.items():
        if abs(key - line_start_ms) <= 500:
            return timings
    return None


def apply_word_timings(tokens: list[Token], timings_by_line: dict[int, list], line_start_ms: int | None) -> None:
    if line_start_ms is None:
        return

    scripts_dir = Path(__file__).resolve().parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from word_timing import merge_word_timings_for_surface

    line_timings = lookup_line_word_timings(line_start_ms, timings_by_line)
    if not line_timings:
        return

    cursor = 0
    for token in tokens:
        merged, cursor = merge_word_timings_for_surface(token.surface, line_timings, cursor)
        if merged:
            token.startMs = merged.start_ms
            token.durationMs = merged.duration_ms


def tokenize_lyrics(
    entries: Iterable[LyricEntry],
    vocab: dict[tuple[str, str], dict[str, str]],
    *,
    qrc_timings_by_line: dict[int, list] | None = None,
    language: str = "auto",
) -> tuple[list[dict], str]:
    all_lines: list[dict] = []
    global_index = 0
    language_key = language.lower()
    use_cantonese = is_cantonese_language(language)
    use_sudachi = Dictionary is not None and language_key in {"auto", "ja", "jp", "japanese"}
    tokenizer_name = "sudachipy" if use_sudachi else "generic"
    if use_cantonese and pycantonese is not None:
        tokenizer_name = "pycantonese"

    for line_index, entry in enumerate(entries):
        line = entry.text.rstrip("\n")
        if use_cantonese:
            tokens = cantonese_tokenize_line(line, line_index, global_index)
        elif use_sudachi and is_japanese_text(line):
            tokens = sudachi_tokenize_line(line, line_index, global_index)
        else:
            tokens = generic_tokenize_line(line, line_index, global_index)

        for token in tokens:
            apply_vocab(token, vocab)

        if qrc_timings_by_line:
            apply_word_timings(tokens, qrc_timings_by_line, entry.start_ms)

        line_payload: dict = {
            "lineIndex": line_index,
            "text": line,
            "tokens": [asdict(token) for token in tokens],
        }
        if entry.start_ms is not None:
            line_payload["startMs"] = entry.start_ms
        if entry.duration_ms is not None:
            line_payload["durationMs"] = entry.duration_ms
        if entry.audio_clip:
            line_payload["audioClip"] = entry.audio_clip

        all_lines.append(line_payload)
        global_index += len(tokens)

    return all_lines, tokenizer_name


def attach_audio_clips(
    entries: list[LyricEntry],
    audio_path: Path,
    output_html: Path,
    *,
    padding_ms: int,
) -> tuple[list[LyricEntry], Path]:
    scripts_dir = Path(__file__).resolve().parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from audio_splitter import AudioSegment, split_segments

    timed_entries = [
        (index, entry)
        for index, entry in enumerate(entries)
        if entry.start_ms is not None and entry.duration_ms is not None
    ]
    if not timed_entries:
        raise ValueError("歌词文件中没有 QRC/LRC 行级时间轴，无法切分音频。请使用 .lrc 或带时间戳的 _qm.qrc。")

    audio_dir = output_html.with_name(f"{output_html.stem}_audio")
    audio_dir.mkdir(parents=True, exist_ok=True)

    segments: list[AudioSegment] = []
    for index, entry in timed_entries:
        clip_path = audio_dir / f"line_{index:03d}.mp3"
        segments.append(
            AudioSegment(
                line_index=index,
                start_ms=entry.start_ms or 0,
                duration_ms=entry.duration_ms or 0,
                output_path=clip_path,
            )
        )

    split_segments(audio_path.resolve(), segments, padding_ms=padding_ms)

    updated_entries = list(entries)
    for (index, _), segment in zip(timed_entries, segments, strict=True):
        relative_clip = segment.output_path.relative_to(output_html.parent).as_posix()
        updated_entries[index] = LyricEntry(
            text=updated_entries[index].text,
            start_ms=updated_entries[index].start_ms,
            duration_ms=updated_entries[index].duration_ms,
            audio_clip=relative_clip,
        )

    return updated_entries, audio_dir


def export_vocab(lines: list[dict], path: Path) -> None:
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, str]] = []
    for line in lines:
        for token in line["tokens"]:
            key = (token["surface"], token["lemma"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "surface": token["surface"],
                    "lemma": token["lemma"],
                    "hira": token["hira"],
                    "kata": token["kata"],
                    "romaji": token["romaji"],
                    "zh": token["zh"],
                }
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["surface", "lemma", "hira", "kata", "romaji", "zh"])
        writer.writeheader()
        writer.writerows(rows)


def render_html(title: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    safe_title = html.escape(title)
    return HTML_TEMPLATE.replace("__TITLE__", safe_title).replace("__DATA__", payload)


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #667085;
      --line: #d9e0ea;
      --accent: #2563eb;
      --accent-soft: #dbeafe;
      --selected: #fde68a;
      --hover: #eef2ff;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
      line-height: 1.7;
    }

    .app {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }

    header {
      display: flex;
      gap: 16px;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 20px;
    }

    h1 {
      margin: 0 0 8px;
      font-size: 28px;
    }

    .meta {
      color: var(--muted);
      font-size: 14px;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 18px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
    }

    .lyrics {
      padding: 24px;
    }

    .line {
      padding: 14px 0;
      border-bottom: 1px solid #edf1f7;
    }

    .line-head {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }

    .line-play {
      border: 0;
      border-radius: 999px;
      width: 34px;
      height: 34px;
      padding: 0;
      background: #eef2ff;
      color: var(--accent);
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      flex: 0 0 auto;
    }

    .line-play:hover {
      background: var(--accent-soft);
    }

    .line-play.playing {
      background: var(--accent);
      color: #fff;
    }

    .line.playing-line {
      background: #f8fbff;
      border-radius: 12px;
      padding-left: 8px;
      padding-right: 8px;
    }

    .line-label {
      color: var(--muted);
      font-size: 13px;
    }

    .line-audio-hidden {
      display: none;
    }

    .line:last-child {
      border-bottom: 0;
    }

    .token {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      min-width: 1.5em;
      margin: 4px 3px;
      padding: 5px 7px;
      border-radius: 10px;
      cursor: pointer;
      user-select: none;
      transition: background 120ms ease, transform 120ms ease;
    }

    .token:hover {
      background: var(--hover);
    }

    .token.active {
      background: var(--accent-soft);
      outline: 2px solid var(--accent);
    }

    .token.selected {
      background: var(--selected);
    }

    .surface {
      font-size: 24px;
      line-height: 1.15;
      white-space: nowrap;
    }

    .reading {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.2;
      min-height: 15px;
    }

    body.hide-reading .reading,
    body.hide-romaji .romaji-inline,
    body.hide-meaning .meaning-inline {
      display: none;
    }

    .romaji-inline,
    .meaning-inline {
      color: #475467;
      font-size: 12px;
      line-height: 1.2;
      min-height: 15px;
    }

    .sidebar {
      position: sticky;
      top: 16px;
      padding: 18px;
    }

    .card-title {
      margin: 0 0 12px;
      font-size: 18px;
    }

    .word-main {
      font-size: 36px;
      font-weight: 700;
      margin-bottom: 8px;
    }

    .field {
      display: grid;
      grid-template-columns: 74px 1fr;
      gap: 8px;
      padding: 7px 0;
      border-bottom: 1px solid #edf1f7;
      font-size: 14px;
    }

    .field span:first-child {
      color: var(--muted);
    }

    .selected-text {
      min-height: 48px;
      margin: 14px 0;
      padding: 10px;
      border: 1px dashed #b8c2d6;
      border-radius: 12px;
      color: #344054;
      background: #fafcff;
    }

    .controls {
      display: grid;
      gap: 8px;
      margin-top: 14px;
    }

    button {
      border: 0;
      border-radius: 12px;
      padding: 10px 12px;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }

    button.secondary {
      background: #eef2f7;
      color: #1f2937;
    }

    .tips {
      margin-top: 14px;
      color: var(--muted);
      font-size: 13px;
    }

    @media (max-width: 840px) {
      header,
      .layout {
        display: block;
      }

      .sidebar {
        position: static;
        margin-top: 18px;
      }
    }
  </style>
</head>
<body>
  <main class="app">
    <header>
      <div>
        <h1 id="title"></h1>
        <div class="meta" id="meta"></div>
      </div>
    </header>

    <section class="layout">
      <div class="panel lyrics" id="lyrics"></div>
      <aside class="panel sidebar">
        <h2 class="card-title">词卡</h2>
        <div class="word-main" id="cardSurface">请选择词汇</div>
        <div class="field"><span>原形</span><strong id="cardLemma">-</strong></div>
        <div class="field"><span>读音</span><strong id="cardHira">-</strong></div>
        <div class="field"><span>转写</span><strong id="cardKata">-</strong></div>
        <div class="field"><span>罗马化</span><strong id="cardRomaji">-</strong></div>
        <div class="field"><span>中文</span><strong id="cardZh">-</strong></div>
        <div class="field"><span>词性</span><strong id="cardPos">-</strong></div>

        <h2 class="card-title" style="margin-top:18px;">选中短语</h2>
        <div class="selected-text" id="selectedText">拖过多个词，松开鼠标后可整段朗读。</div>

        <div class="controls">
          <button id="speakSelection">朗读选中短语</button>
          <button class="secondary" id="playLineAudio" hidden>播放本句原唱</button>
          <button class="secondary" id="clearSelection">清除选择</button>
          <button class="secondary" id="toggleReading">显示/隐藏读音</button>
          <button class="secondary" id="toggleRomaji">显示/隐藏罗马化</button>
          <button class="secondary" id="toggleMeaning">显示/隐藏中文</button>
        </div>

        <div class="tips" id="tips">
          点击单个词会朗读词汇。按住鼠标拖过多个词，会按原顺序拼成短语朗读。发音依赖浏览器或系统是否安装对应语言语音。
        </div>
      </aside>
    </section>
  </main>

  <script>
    const APP_DATA = __DATA__;

    const state = {
      isDragging: false,
      dragMoved: false,
      selected: new Set(),
      activeToken: null,
      activeLineIndex: null,
      playingLineIndex: null,
      wordStopTimer: null,
    };

    const audioPlayers = new Map();
    const playLineAudioBtn = document.querySelector("#playLineAudio");
    const tipsEl = document.querySelector("#tips");

    const titleEl = document.querySelector("#title");
    const metaEl = document.querySelector("#meta");
    const lyricsEl = document.querySelector("#lyrics");
    const selectedTextEl = document.querySelector("#selectedText");

    const card = {
      surface: document.querySelector("#cardSurface"),
      lemma: document.querySelector("#cardLemma"),
      hira: document.querySelector("#cardHira"),
      kata: document.querySelector("#cardKata"),
      romaji: document.querySelector("#cardRomaji"),
      zh: document.querySelector("#cardZh"),
      pos: document.querySelector("#cardPos"),
    };

    function getAllTokens() {
      return APP_DATA.lines.flatMap(line => line.tokens);
    }

    function tokenByIndex(index) {
      return getAllTokens().find(token => token.globalIndex === Number(index));
    }

    function hasLineAudio() {
      return APP_DATA.lines.some(line => line.audioClip);
    }

    function lineByIndex(index) {
      return APP_DATA.lines.find(line => line.lineIndex === Number(index));
    }

    function stopAllLineAudio() {
      if (state.wordStopTimer) {
        clearTimeout(state.wordStopTimer);
        state.wordStopTimer = null;
      }
      audioPlayers.forEach(player => {
        player.pause();
        player.currentTime = 0;
      });
      document.querySelectorAll(".line-play.playing").forEach(button => button.classList.remove("playing"));
      document.querySelectorAll(".line.playing-line").forEach(line => line.classList.remove("playing-line"));
      state.playingLineIndex = null;
    }

    function getLineAudio(lineIndex) {
      const line = lineByIndex(lineIndex);
      if (!line || !line.audioClip) return null;
      if (!audioPlayers.has(lineIndex)) {
        const player = new Audio(line.audioClip);
        player.preload = "auto";
        player.addEventListener("ended", () => {
          if (state.playingLineIndex === lineIndex) {
            stopAllLineAudio();
          }
        });
        audioPlayers.set(lineIndex, player);
      }
      return audioPlayers.get(lineIndex);
    }

    function playLineAudio(lineIndex) {
      const player = getLineAudio(lineIndex);
      if (!player) return;

      stopAllLineAudio();
      state.playingLineIndex = lineIndex;
      state.activeLineIndex = lineIndex;

      const lineEl = document.querySelector(`.line[data-line-index="${lineIndex}"]`);
      const playBtn = lineEl ? lineEl.querySelector(".line-play") : null;
      if (playBtn) playBtn.classList.add("playing");
      if (lineEl) lineEl.classList.add("playing-line");

      player.currentTime = 0;
      player.play().catch(error => {
        console.error(error);
        alert("无法播放该句音频，请确认 HTML 与 _audio 文件夹在同一目录。");
      });
    }

    function playWordAudio(token) {
      const line = lineByIndex(token.lineIndex);
      if (!line || !line.audioClip) {
        speak(token.surface);
        return;
      }

      if (token.startMs == null || token.durationMs == null) {
        playLineAudio(token.lineIndex);
        return;
      }

      const player = getLineAudio(token.lineIndex);
      if (!player) return;

      stopAllLineAudio();
      state.playingLineIndex = token.lineIndex;
      state.activeLineIndex = token.lineIndex;

      const lineEl = document.querySelector(`.line[data-line-index="${token.lineIndex}"]`);
      const playBtn = lineEl ? lineEl.querySelector(".line-play") : null;
      if (playBtn) playBtn.classList.add("playing");
      if (lineEl) lineEl.classList.add("playing-line");

      const padding = APP_DATA.audioPaddingMs || 0;
      const clipOffsetMs = Math.max(0, token.startMs - line.startMs + padding);
      player.currentTime = clipOffsetMs / 1000;
      player.play().catch(error => {
        console.error(error);
        alert("无法播放该词原唱片段。");
      });

      state.wordStopTimer = setTimeout(() => {
        player.pause();
        stopAllLineAudio();
      }, token.durationMs + 60);
    }

    function speak(text) {
      if (!text || !window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = APP_DATA.speechLang || "ja-JP";
      utterance.rate = 0.82;
      utterance.pitch = 1;
      window.speechSynthesis.speak(utterance);
    }

    function render() {
      titleEl.textContent = APP_DATA.title;
      const audioLineCount = APP_DATA.lines.filter(line => line.audioClip).length;
      const audioMeta = audioLineCount ? ` · 原唱句段：${audioLineCount}` : "";
      metaEl.textContent = `语言：${APP_DATA.language} · TTS：${APP_DATA.speechLang} · 分词器：${APP_DATA.tokenizer} · 行数：${APP_DATA.lines.length}${audioMeta}`;
      lyricsEl.innerHTML = "";

      if (hasLineAudio()) {
        playLineAudioBtn.hidden = false;
        const hasWordTiming = getAllTokens().some(token => token.startMs != null);
        tipsEl.textContent = hasWordTiming
          ? "点击词汇播放原唱中该词片段。行首 ▶ 播放整句。拖选多词仍用浏览器 TTS 朗读短语。"
          : "点击行首 ▶ 播放该句原唱。点击单个词使用当前语言 TTS。拖选多个词可拼成短语朗读。";
      }

      APP_DATA.lines.forEach(line => {
        const lineEl = document.createElement("div");
        lineEl.className = "line";
        lineEl.dataset.lineIndex = line.lineIndex;

        if (line.audioClip) {
          const headEl = document.createElement("div");
          headEl.className = "line-head";

          const playBtn = document.createElement("button");
          playBtn.type = "button";
          playBtn.className = "line-play";
          playBtn.textContent = "▶";
          playBtn.title = "播放本句原唱";
          playBtn.addEventListener("click", event => {
            event.stopPropagation();
            playLineAudio(line.lineIndex);
          });

          const labelEl = document.createElement("div");
          labelEl.className = "line-label";
          labelEl.textContent = `第 ${line.lineIndex + 1} 句`;

          headEl.appendChild(playBtn);
          headEl.appendChild(labelEl);
          lineEl.appendChild(headEl);
        }

        line.tokens.forEach(token => {
          const tokenEl = document.createElement("span");
          tokenEl.className = "token";
          tokenEl.dataset.index = token.globalIndex;
          tokenEl.dataset.lineIndex = line.lineIndex;
          tokenEl.title = `${token.hira || token.surface} / ${token.romaji || ""} / ${token.zh || "未填写中文释义"}`;
          tokenEl.innerHTML = `
            <span class="reading">${escapeHtml(token.hira || "")}</span>
            <span class="surface">${escapeHtml(token.surface)}</span>
            <span class="romaji-inline">${escapeHtml(token.romaji || "")}</span>
            <span class="meaning-inline">${escapeHtml(token.zh || "")}</span>
          `;
          lineEl.appendChild(tokenEl);
        });
        lyricsEl.appendChild(lineEl);
      });
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function showCard(token) {
      state.activeToken = token.globalIndex;
      state.activeLineIndex = token.lineIndex;
      card.surface.textContent = token.surface;
      card.lemma.textContent = token.lemma || "-";
      card.hira.textContent = token.hira || "-";
      card.kata.textContent = token.kata || "-";
      card.romaji.textContent = token.romaji || "-";
      card.zh.textContent = token.zh || "待校对";
      card.pos.textContent = token.pos || "-";
      document.querySelectorAll(".token").forEach(el => {
        el.classList.toggle("active", Number(el.dataset.index) === token.globalIndex);
      });
    }

    function updateSelectionDisplay() {
      document.querySelectorAll(".token").forEach(el => {
        el.classList.toggle("selected", state.selected.has(Number(el.dataset.index)));
      });

      const phrase = selectedPhrase();
      selectedTextEl.textContent = phrase || "拖过多个词，松开鼠标后可整段朗读。";
    }

    function selectedPhrase() {
      return [...state.selected]
        .sort((a, b) => a - b)
        .map(index => tokenByIndex(index))
        .filter(Boolean)
        .map(token => token.surface)
        .join("");
    }

    function clearSelection() {
      state.selected.clear();
      updateSelectionDisplay();
    }

    lyricsEl.addEventListener("mousedown", event => {
      const target = event.target.closest(".token");
      if (!target) return;
      event.preventDefault();
      state.isDragging = true;
      state.dragMoved = false;
      state.selected.clear();
      state.selected.add(Number(target.dataset.index));
      updateSelectionDisplay();
    });

    lyricsEl.addEventListener("mouseover", event => {
      if (!state.isDragging) return;
      const target = event.target.closest(".token");
      if (!target) return;
      state.dragMoved = true;
      state.selected.add(Number(target.dataset.index));
      updateSelectionDisplay();
    });

    window.addEventListener("mouseup", event => {
      if (!state.isDragging) return;
      state.isDragging = false;

      const target = event.target.closest ? event.target.closest(".token") : null;
      if (!state.dragMoved && target) {
        const token = tokenByIndex(target.dataset.index);
        if (token) {
          showCard(token);
          playWordAudio(token);
        }
        clearSelection();
        return;
      }

      const phrase = selectedPhrase();
      if (phrase) speak(phrase);
    });

    document.querySelector("#speakSelection").addEventListener("click", () => {
      speak(selectedPhrase());
    });

    playLineAudioBtn.addEventListener("click", () => {
      if (state.activeLineIndex === null) return;
      playLineAudio(state.activeLineIndex);
    });

    document.querySelector("#clearSelection").addEventListener("click", clearSelection);

    document.querySelector("#toggleReading").addEventListener("click", () => {
      document.body.classList.toggle("hide-reading");
    });

    document.querySelector("#toggleRomaji").addEventListener("click", () => {
      document.body.classList.toggle("hide-romaji");
    });

    document.querySelector("#toggleMeaning").addEventListener("click", () => {
      document.body.classList.toggle("hide-meaning");
    });

    render();
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a multilingual lyrics reader HTML file.")
    parser.add_argument("--lyrics", required=True, type=Path, help="Lyrics file: .txt/.lrc or encrypted QQ Music .qrc cache.")
    parser.add_argument("--title", default="歌词点读", help="HTML page title.")
    parser.add_argument(
        "--language",
        default="auto",
        help="Lyric language code/name, e.g. ja, yue, zh-CN, ko, en. Default: auto.",
    )
    parser.add_argument(
        "--speech-lang",
        help="Browser SpeechSynthesis language tag, e.g. ja-JP, zh-HK, ko-KR, en-US.",
    )
    parser.add_argument("--vocab", type=Path, help="Optional CSV with surface,lemma,hira,kata,romaji,zh columns.")
    parser.add_argument("--out", required=True, type=Path, help="Output HTML path.")
    parser.add_argument("--tokens-out", type=Path, help="Optional JSON output for tokenized lyrics data.")
    parser.add_argument("--export-vocab", type=Path, help="Export a CSV vocabulary table for manual translation.")
    parser.add_argument("--audio", type=Path, help="Song audio file (.mp3/.m4a/.flac). Requires QRC line timings.")
    parser.add_argument(
        "--audio-padding",
        type=int,
        default=80,
        help="Extra milliseconds added before/after each line clip (default: 80).",
    )
    parser.add_argument(
        "--qrc-timing",
        type=Path,
        help="Optional QQ Music _qm.qrc for per-word timings. Auto-detected from QQ cache when using .lrc.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lyrics_path = args.lyrics.resolve()
    output_html = args.out.resolve()
    vocab = load_vocab(args.vocab.resolve() if args.vocab else None)
    try:
        entries = read_lyric_entries(lyrics_path)
    except (UnicodeDecodeError, ValueError) as error:
        print(f"读取歌词失败：{error}", file=sys.stderr)
        raise SystemExit(2) from error

    if not entries:
        print("读取歌词失败：未提取到任何歌词行。", file=sys.stderr)
        raise SystemExit(2)

    audio_dir: Path | None = None
    audio_padding_ms = args.audio_padding
    qrc_timings_by_line: dict[int, list] | None = None

    if args.audio or args.qrc_timing:
        qrc_timing_path = resolve_qrc_timing_path(lyrics_path, args.qrc_timing)
        if qrc_timing_path:
            try:
                qrc_timings_by_line = load_qrc_word_timings(qrc_timing_path)
            except Exception as error:
                print(f"警告：未能加载 QRC 词级时间轴（{error}），词汇点击将回退为整句/TTS。", file=sys.stderr)
        elif args.qrc_timing:
            print(f"警告：未找到 QRC 词级时间轴文件，词汇点击将回退为整句/TTS。", file=sys.stderr)

    if args.audio:
        try:
            entries, audio_dir = attach_audio_clips(
                entries,
                args.audio.resolve(),
                output_html,
                padding_ms=audio_padding_ms,
            )
        except (RuntimeError, ValueError, subprocess.CalledProcessError) as error:
            print(f"音频切分失败：{error}", file=sys.stderr)
            raise SystemExit(2) from error

    tokenized_lines, tokenizer_name = tokenize_lyrics(
        entries,
        vocab,
        qrc_timings_by_line=qrc_timings_by_line,
        language=args.language,
    )
    speech_lang = speech_lang_for(args.language, args.speech_lang)

    data = {
        "title": args.title,
        "tokenizer": tokenizer_name,
        "language": args.language,
        "speechLang": speech_lang,
        "source": str(lyrics_path),
        "lines": tokenized_lines,
        "audioPaddingMs": audio_padding_ms,
    }
    if audio_dir:
        data["audioDir"] = audio_dir.name

    if args.export_vocab:
        export_vocab(tokenized_lines, args.export_vocab.resolve())

    if args.tokens_out:
        args.tokens_out.parent.mkdir(parents=True, exist_ok=True)
        args.tokens_out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(render_html(args.title, data), encoding="utf-8")
    result = {"output": str(output_html), "tokenizer": tokenizer_name}
    if audio_dir:
        result["audioDir"] = str(audio_dir)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
