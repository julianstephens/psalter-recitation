from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WhisperCppConfig:
    executable_path: Path
    model_path: Path
    language: str = "en"
    threads: int | None = None
    temp_directory: Path | None = None
    retain_artifacts: bool = False


@dataclass(frozen=True, slots=True)
class FfmpegRecorderConfig:
    executable_path: Path
    input_device: str | None = None
    max_duration_seconds: int | None = None
    temp_directory: Path | None = None
    retain_artifacts: bool = False


@dataclass(frozen=True, slots=True)
class AppConfig:
    data_dir: Path
    db_path: Path
    default_translation_id: str | None
    scripture_provider: str
    scripture_provider_base_url: str
    scripture_provider_timeout_seconds: float
    whisper_cpp: WhisperCppConfig | None
    recorder: FfmpegRecorderConfig | None


def default_data_dir() -> Path:
    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "psalter-recitation"
    return Path.home() / ".local" / "share" / "psalter-recitation"


def _parse_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().casefold() in {"1", "true", "yes", "y", "on"}


def _parse_optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    return int(raw)


def _parse_optional_path(name: str) -> Path | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    return Path(raw).expanduser()


def build_config(data_dir: Path | None = None) -> AppConfig:
    root = data_dir or default_data_dir()
    whisper_executable = _parse_optional_path("PSALTER_WHISPER_EXECUTABLE")
    whisper_model = _parse_optional_path("PSALTER_WHISPER_MODEL")
    retain_artifacts = _parse_bool("PSALTER_RETAIN_AUDIO")
    whisper_temp_dir = _parse_optional_path("PSALTER_AUDIO_TEMP_DIRECTORY")
    recorder_temp_dir = whisper_temp_dir

    whisper_cpp = None
    if whisper_executable is not None and whisper_model is not None:
        whisper_cpp = WhisperCppConfig(
            executable_path=whisper_executable,
            model_path=whisper_model,
            language=os.getenv("PSALTER_WHISPER_LANGUAGE", "en"),
            threads=_parse_optional_int("PSALTER_WHISPER_THREADS"),
            temp_directory=whisper_temp_dir,
            retain_artifacts=retain_artifacts,
        )

    recorder = None
    recorder_executable = _parse_optional_path("PSALTER_RECORDER_EXECUTABLE")
    if recorder_executable is not None:
        recorder = FfmpegRecorderConfig(
            executable_path=recorder_executable,
            input_device=os.getenv("PSALTER_AUDIO_INPUT_DEVICE"),
            max_duration_seconds=_parse_optional_int("PSALTER_MAX_RECORD_SECONDS"),
            temp_directory=recorder_temp_dir,
            retain_artifacts=retain_artifacts,
        )

    return AppConfig(
        data_dir=root,
        db_path=root / "psalter.db",
        default_translation_id=os.getenv("PSALTER_DEFAULT_TRANSLATION"),
        scripture_provider=os.getenv("PSALTER_SCRIPTURE_PROVIDER", "helloao").strip().casefold(),
        scripture_provider_base_url=os.getenv(
            "PSALTER_SCRIPTURE_PROVIDER_BASE_URL",
            "https://bible.helloao.org/api",
        ).strip(),
        scripture_provider_timeout_seconds=float(
            os.getenv("PSALTER_SCRIPTURE_PROVIDER_TIMEOUT_SECONDS", "20")
        ),
        whisper_cpp=whisper_cpp,
        recorder=recorder,
    )
