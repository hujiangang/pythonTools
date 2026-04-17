#!/usr/bin/env python3
"""Extract audio and embedded subtitle streams from a video file."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


AUDIO_EXTENSIONS = {
    "aac": ".m4a",
    "mp3": ".mp3",
    "opus": ".opus",
    "vorbis": ".ogg",
    "flac": ".flac",
    "pcm_s16le": ".wav",
}


def run_command(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"无法生成可用输出文件名：{path}")


def ffprobe(input_path: Path) -> dict:
    result = run_command([
        "ffprobe",
        "-v", "error",
        "-show_streams",
        "-of", "json",
        str(input_path),
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout)


def stream_label(stream: dict, fallback: str) -> str:
    tags = stream.get("tags") or {}
    language = tags.get("language")
    title = tags.get("title")
    parts = [value for value in (language, title) if value]
    return "_".join(parts) if parts else fallback


def safe_name(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid else char for char in name)
    return cleaned.strip(" .") or "stream"


def extract_audio(input_path: Path, output_dir: Path, streams: list[dict]) -> list[Path]:
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if not audio_streams:
        print("未发现音频流")
        return []

    outputs = []
    for audio_index, stream in enumerate(audio_streams):
        codec = stream.get("codec_name") or "audio"
        extension = AUDIO_EXTENSIONS.get(codec, ".mka")
        label = safe_name(stream_label(stream, f"audio_{audio_index}"))
        output_path = unique_path(output_dir / f"{input_path.stem}_{label}{extension}")

        result = run_command([
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-map", f"0:a:{audio_index}",
            "-vn",
            "-c:a", "copy",
            str(output_path),
        ])

        if result.returncode != 0:
            # Some containers/codecs cannot be copied into the chosen extension. Fall back to wav.
            output_path = unique_path(output_dir / f"{input_path.stem}_{label}.wav")
            result = run_command([
                "ffmpeg",
                "-y",
                "-i", str(input_path),
                "-map", f"0:a:{audio_index}",
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                str(output_path),
            ])

        if result.returncode != 0:
            print(f"音频流 {audio_index} 提取失败：{result.stderr.strip()}")
            continue

        print(f"音频已提取：{output_path}")
        outputs.append(output_path)

    return outputs


def extract_subtitles(input_path: Path, output_dir: Path, streams: list[dict]) -> list[Path]:
    subtitle_streams = [stream for stream in streams if stream.get("codec_type") == "subtitle"]
    if not subtitle_streams:
        print("未发现内嵌字幕流")
        return []

    outputs = []
    for subtitle_index, stream in enumerate(subtitle_streams):
        label = safe_name(stream_label(stream, f"subtitle_{subtitle_index}"))
        output_path = unique_path(output_dir / f"{input_path.stem}_{label}.srt")

        result = run_command([
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-map", f"0:s:{subtitle_index}",
            "-c:s", "srt",
            str(output_path),
        ])

        if result.returncode != 0:
            raw_path = unique_path(output_dir / f"{input_path.stem}_{label}.sub")
            result = run_command([
                "ffmpeg",
                "-y",
                "-i", str(input_path),
                "-map", f"0:s:{subtitle_index}",
                "-c:s", "copy",
                str(raw_path),
            ])
            output_path = raw_path

        if result.returncode != 0:
            print(f"字幕流 {subtitle_index} 提取失败：{result.stderr.strip()}")
            continue

        print(f"字幕已提取：{output_path}")
        outputs.append(output_path)

    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="提取视频中的音频和内嵌字幕")
    parser.add_argument("input", help="输入视频文件")
    parser.add_argument("-o", "--output", default="./output/extracted", help="输出目录")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()

    if not input_path.exists():
        print(f"输入文件不存在：{input_path}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        info = ffprobe(input_path)
    except Exception as exc:
        print(f"读取媒体信息失败：{exc}", file=sys.stderr)
        return 1

    streams = info.get("streams", [])
    audio_outputs = extract_audio(input_path, output_dir, streams)
    subtitle_outputs = extract_subtitles(input_path, output_dir, streams)

    print()
    print("=" * 60)
    print(f"完成：音频 {len(audio_outputs)} 个，字幕 {len(subtitle_outputs)} 个")
    print(f"输出目录：{output_dir}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
