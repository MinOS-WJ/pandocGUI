from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


PRESET_SCHEMA_VERSION = 1
DEFAULT_SETTINGS = {
    "pandoc_path": "",
    "last_input_directory": "",
    "last_output_directory": "",
}


class StorageError(RuntimeError):
    pass


class AppStorage:
    def __init__(self, root: Path | None = None) -> None:
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        self.root = root or Path(appdata) / "pandocGUI"
        self.settings_path = self.root / "settings.json"
        self.presets_path = self.root / "presets.json"

    def load_settings(self) -> dict[str, Any]:
        data = self._read_json(self.settings_path, {})
        settings = deepcopy(DEFAULT_SETTINGS)
        if isinstance(data, dict):
            settings.update({key: value for key, value in data.items() if key in settings})
        return settings

    def save_settings(self, settings: dict[str, Any]) -> None:
        payload = deepcopy(DEFAULT_SETTINGS)
        payload.update({key: value for key, value in settings.items() if key in payload})
        self._write_json(self.settings_path, payload)

    def load_presets(self) -> dict[str, dict[str, Any]]:
        data = self._read_json(self.presets_path, {"schema_version": PRESET_SCHEMA_VERSION, "presets": {}})
        if not isinstance(data, dict) or data.get("schema_version") != PRESET_SCHEMA_VERSION:
            raise StorageError("预设文件版本不受支持。")
        presets = data.get("presets", {})
        if not isinstance(presets, dict):
            raise StorageError("预设文件格式无效。")
        return {str(name): self._validate_preset(payload) for name, payload in presets.items()}

    def save_presets(self, presets: dict[str, dict[str, Any]]) -> None:
        validated = {str(name): self._validate_preset(payload) for name, payload in presets.items()}
        self._write_json(
            self.presets_path,
            {"schema_version": PRESET_SCHEMA_VERSION, "presets": validated},
        )

    def export_preset(self, destination: Path, name: str, payload: dict[str, Any]) -> None:
        self._write_json(
            destination,
            {"schema_version": PRESET_SCHEMA_VERSION, "name": name, "preset": self._validate_preset(payload)},
        )

    def import_preset(self, source: Path) -> tuple[str, dict[str, Any]]:
        data = self._read_json(source, None)
        if not isinstance(data, dict) or data.get("schema_version") != PRESET_SCHEMA_VERSION:
            raise StorageError("不是受支持的 pandocGUI 预设文件。")
        name = str(data.get("name", "")).strip()
        if not name:
            raise StorageError("预设名称为空。")
        return name, self._validate_preset(data.get("preset"))

    @staticmethod
    def _validate_preset(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StorageError("预设内容无效。")
        options = payload.get("options", {})
        extra_args = payload.get("extra_args", [])
        if not isinstance(options, dict) or not isinstance(extra_args, list):
            raise StorageError("预设参数格式无效。")
        return {
            "from_format": str(payload.get("from_format", "")),
            "to_format": str(payload.get("to_format", "")),
            "options": options,
            "extra_args": [str(item) for item in extra_args],
        }

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise StorageError(f"无法读取 {path.name}：{error}") from error

    def _write_json(self, path: Path, payload: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(f"{path.suffix}.tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as error:
            raise StorageError(f"无法写入 {path.name}：{error}") from error

