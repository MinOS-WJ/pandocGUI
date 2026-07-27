from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class OptionKind(str, Enum):
    TEXT = "text"
    INTEGER = "integer"
    PATH = "path"
    CHOICE = "choice"
    BOOL = "bool"
    SWITCH = "switch"


@dataclass(frozen=True, slots=True)
class OptionSpec:
    key: str
    flag: str
    label: str
    category: str
    kind: OptionKind = OptionKind.TEXT
    choices: tuple[str, ...] = ()
    repeatable: bool = False
    aliases: tuple[str, ...] = ()
    description: str = ""

    @property
    def long_names(self) -> set[str]:
        return {self.flag.removeprefix("--"), *self.aliases}


class JobState(str, Enum):
    WAITING = "等待"
    RUNNING = "运行中"
    SUCCEEDED = "成功"
    FAILED = "失败"
    CANCELED = "已取消"


@dataclass(slots=True)
class PandocCapabilities:
    executable: Path
    version: str
    major_version: int
    input_formats: list[str]
    output_formats: list[str]
    highlight_languages: list[str]
    highlight_styles: list[str]
    available_options: set[str]
    help_text: str
    extensions: dict[str, list[str]] = field(default_factory=dict)

    def supports(self, spec: OptionSpec) -> bool:
        return bool(spec.long_names & self.available_options)


@dataclass(slots=True)
class ConversionJob:
    inputs: list[Path]
    output: Path
    from_format: str
    to_format: str
    working_directory: Path
    options: dict[str, Any] = field(default_factory=dict)
    extra_args: list[str] = field(default_factory=list)
    identifier: str = ""
    state: JobState = JobState.WAITING
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""

    def preset_payload(self) -> dict[str, Any]:
        return {
            "from_format": self.from_format,
            "to_format": self.to_format,
            "options": self.options,
            "extra_args": self.extra_args,
        }

    def snapshot(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["inputs"] = [str(path) for path in self.inputs]
        payload["output"] = str(self.output)
        payload["working_directory"] = str(self.working_directory)
        payload["state"] = self.state.value
        return payload


@dataclass(slots=True)
class CommandInvocation:
    executable: str
    arguments: list[str]
    working_directory: str

