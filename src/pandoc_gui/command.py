from __future__ import annotations

import ctypes
import os
import shlex
import subprocess
from ctypes import wintypes
from pathlib import Path
from typing import Any

from pandoc_gui.models import CommandInvocation, ConversionJob, OptionKind
from pandoc_gui.options import OPTION_BY_KEY, OPTION_SPECS


class CommandValidationError(ValueError):
    pass


RESERVED_LONG_OPTIONS = {"--from", "--read", "--to", "--write", "--output"}
RESERVED_SHORT_OPTIONS = {"-f", "-r", "-t", "-w", "-o"}


class PandocCommandBuilder:
    def __init__(self, executable: str | Path) -> None:
        self.executable = str(executable)

    def build(self, job: ConversionJob) -> CommandInvocation:
        self.validate(job)
        arguments: list[str] = []

        defaults_spec = OPTION_BY_KEY["defaults"]
        self._append_value(arguments, defaults_spec, job.options.get("defaults"))
        arguments.extend([f"--from={job.from_format}", f"--to={job.to_format}"])
        arguments.append(f"--output={job.output}")

        for spec in OPTION_SPECS:
            if spec.key == "defaults":
                continue
            self._append_value(arguments, spec, job.options.get(spec.key))
        arguments.extend(job.extra_args)
        arguments.extend(str(path) for path in job.inputs)
        return CommandInvocation(
            executable=self.executable,
            arguments=arguments,
            working_directory=str(job.working_directory),
        )

    def validate(self, job: ConversionJob) -> None:
        if not job.inputs:
            raise CommandValidationError("请至少添加一个输入文件。")
        missing = [str(path) for path in job.inputs if not path.is_file()]
        if missing:
            raise CommandValidationError(f"输入文件不存在：{missing[0]}")
        if not job.from_format or not job.to_format:
            raise CommandValidationError("请选择输入格式和输出格式。")
        if not job.output.name:
            raise CommandValidationError("请选择输出文件。")
        if not job.output.parent.is_dir():
            raise CommandValidationError(f"输出目录不存在：{job.output.parent}")
        if not job.working_directory.is_dir():
            raise CommandValidationError(f"工作目录不存在：{job.working_directory}")
        validate_extra_args(job.extra_args)

    @staticmethod
    def _append_value(arguments: list[str], spec: Any, value: Any) -> None:
        if value is None or value == "" or value == []:
            return
        if spec.kind is OptionKind.BOOL:
            arguments.append(f"{spec.flag}={'true' if bool(value) else 'false'}")
            return
        if spec.kind is OptionKind.SWITCH:
            if value:
                arguments.append(spec.flag)
            return
        values = value if spec.repeatable and isinstance(value, list) else [value]
        for item in values:
            if item is not None and str(item) != "":
                arguments.append(f"{spec.flag}={item}")


def validate_extra_args(arguments: list[str]) -> None:
    for argument in arguments:
        lowered = argument.casefold()
        if lowered == "--":
            raise CommandValidationError("附加参数不能包含位置参数分隔符 --。")
        if any(lowered == flag or lowered.startswith(f"{flag}=") for flag in RESERVED_LONG_OPTIONS):
            raise CommandValidationError(f"附加参数不能覆盖 GUI 管理的参数：{argument}")
        if any(argument == flag or argument.startswith(flag) for flag in RESERVED_SHORT_OPTIONS):
            raise CommandValidationError(f"附加参数不能覆盖 GUI 管理的参数：{argument}")
        if not argument.startswith("-"):
            raise CommandValidationError(f"附加参数不能包含输入文件：{argument}")


def parse_windows_arguments(command_line: str) -> list[str]:
    if not command_line.strip():
        return []
    if os.name != "nt":
        return shlex.split(command_line)
    shell32 = ctypes.windll.shell32
    shell32.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    count = ctypes.c_int()
    fake_command = f"pandoc.exe {command_line}"
    pointer = shell32.CommandLineToArgvW(fake_command, ctypes.byref(count))
    if not pointer:
        raise CommandValidationError("无法解析附加参数。")
    try:
        return [pointer[index] for index in range(1, count.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(pointer)


def command_preview(invocation: CommandInvocation) -> str:
    return subprocess.list2cmdline([invocation.executable, *invocation.arguments])


OUTPUT_EXTENSIONS = {
    "asciidoc": ".adoc",
    "asciidoctor": ".adoc",
    "beamer": ".tex",
    "commonmark": ".md",
    "commonmark_x": ".md",
    "context": ".tex",
    "docbook": ".xml",
    "docbook4": ".xml",
    "docbook5": ".xml",
    "docx": ".docx",
    "epub": ".epub",
    "epub2": ".epub",
    "epub3": ".epub",
    "gfm": ".md",
    "html": ".html",
    "html4": ".html",
    "html5": ".html",
    "ipynb": ".ipynb",
    "json": ".json",
    "latex": ".tex",
    "markdown": ".md",
    "native": ".txt",
    "odt": ".odt",
    "pdf": ".pdf",
    "plain": ".txt",
    "pptx": ".pptx",
    "revealjs": ".html",
    "rst": ".rst",
    "rtf": ".rtf",
    "typst": ".typ",
}


def suggested_output(inputs: list[Path], output_format: str) -> Path | None:
    if not inputs:
        return None
    suffix = OUTPUT_EXTENSIONS.get(output_format, f".{output_format}")
    marker = "_converted" if len(inputs) > 1 else ""
    return inputs[0].with_name(f"{inputs[0].stem}{marker}{suffix}")
