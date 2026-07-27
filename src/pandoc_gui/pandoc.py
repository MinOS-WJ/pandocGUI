from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from pandoc_gui.models import PandocCapabilities


class PandocError(RuntimeError):
    pass


class PandocNotFoundError(PandocError):
    pass


class UnsupportedPandocError(PandocError):
    pass


def _run(executable: Path, arguments: list[str], timeout: int = 15) -> str:
    try:
        completed = subprocess.run(
            [str(executable), *arguments],
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PandocError(str(error)) from error
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise PandocError(stderr.strip() or stdout.strip() or f"Pandoc 退出码 {completed.returncode}")
    return stdout


def find_pandoc(configured_path: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if configured_path:
        candidates.append(Path(configured_path).expanduser())
    located = shutil.which("pandoc")
    if located:
        candidates.append(Path(located))
    for environment_name in ("ProgramFiles", "LOCALAPPDATA", "ProgramFiles(x86)"):
        base = os.environ.get(environment_name)
        if base:
            candidates.append(Path(base) / "Pandoc" / "pandoc.exe")
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate.resolve(strict=False)).casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.is_file():
            return candidate.resolve()
    raise PandocNotFoundError("未找到 Pandoc 3.x，请在设置中选择 pandoc.exe。")


def probe_pandoc(executable: str | Path) -> PandocCapabilities:
    executable_path = Path(executable).resolve()
    version_text = _run(executable_path, ["--version"])
    match = re.search(r"^pandoc\s+(\d+)(?:\.(\d+))?", version_text, re.MULTILINE)
    if not match:
        raise PandocError("无法识别 Pandoc 版本。")
    major_version = int(match.group(1))
    if major_version < 3:
        raise UnsupportedPandocError(f"需要 Pandoc 3.x，当前版本为 {match.group(0)}。")
    version = match.group(0).split(maxsplit=1)[1]
    help_text = _run(executable_path, ["--help"])
    available_options = set(re.findall(r"--([a-z0-9][a-z0-9-]*)", help_text))
    return PandocCapabilities(
        executable=executable_path,
        version=version,
        major_version=major_version,
        input_formats=_lines(_run(executable_path, ["--list-input-formats"])),
        output_formats=_lines(_run(executable_path, ["--list-output-formats"])),
        highlight_languages=_lines(_run(executable_path, ["--list-highlight-languages"])),
        highlight_styles=_lines(_run(executable_path, ["--list-highlight-styles"])),
        available_options=available_options,
        help_text=help_text,
    )


def list_extensions(capabilities: PandocCapabilities, format_name: str) -> list[str]:
    if format_name not in capabilities.extensions:
        capabilities.extensions[format_name] = _lines(
            _run(capabilities.executable, [f"--list-extensions={format_name}"])
        )
    return capabilities.extensions[format_name]


def run_tool(capabilities: PandocCapabilities, arguments: list[str]) -> str:
    return _run(capabilities.executable, arguments, timeout=30)


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]

