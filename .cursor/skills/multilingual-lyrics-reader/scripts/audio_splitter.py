"""Split audio files into line clips using ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioSegment:
    line_index: int
    start_ms: int
    duration_ms: int
    output_path: Path


def resolve_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:  # pragma: no cover - depends on local install
        raise RuntimeError(
            "未找到 ffmpeg。请安装系统 ffmpeg，或执行：pip install imageio-ffmpeg"
        ) from error


def split_segments(
    audio_path: Path,
    segments: list[AudioSegment],
    *,
    padding_ms: int = 80,
) -> list[Path]:
    ffmpeg = resolve_ffmpeg()
    audio_path = audio_path.resolve()
    if not audio_path.is_file():
        raise FileNotFoundError(f"音频文件不存在：{audio_path}")

    written: list[Path] = []
    for segment in segments:
        segment.output_path.parent.mkdir(parents=True, exist_ok=True)
        start_ms = max(0, segment.start_ms - padding_ms)
        duration_ms = segment.duration_ms + padding_ms * 2
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(audio_path),
            "-ss",
            f"{start_ms / 1000:.3f}",
            "-t",
            f"{duration_ms / 1000:.3f}",
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            str(segment.output_path),
        ]
        subprocess.run(command, check=True)
        written.append(segment.output_path)
    return written
