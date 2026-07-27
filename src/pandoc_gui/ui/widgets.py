from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pandoc_gui.models import OptionKind, OptionSpec, PandocCapabilities
from pandoc_gui.options import CATEGORIES, OPTION_SPECS


class FileListWidget(QListWidget):
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        files = [path for path in paths if path.is_file()]
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class PathEditor(QWidget):
    changed = Signal()

    def __init__(self, directory: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.directory = directory
        self.line_edit = QLineEdit()
        self.button = QPushButton("浏览…")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.button)
        self.line_edit.textChanged.connect(self.changed)
        self.button.clicked.connect(self._browse)

    def value(self) -> str:
        return self.line_edit.text().strip()

    def set_value(self, value: Any) -> None:
        self.line_edit.setText("" if value is None else str(value))

    def _browse(self) -> None:
        if self.directory:
            selected = QFileDialog.getExistingDirectory(self, "选择目录", self.value())
        else:
            selected, _ = QFileDialog.getOpenFileName(self, "选择文件", self.value())
        if selected:
            self.line_edit.setText(selected)


class RepeatingValueEditor(QWidget):
    changed = Signal()

    def __init__(self, path_values: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.path_values = path_values
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(90)
        self.input = QLineEdit()
        self.add_button = QPushButton("添加")
        self.browse_button = QPushButton("浏览…")
        self.remove_button = QPushButton("移除")
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input, 1)
        if path_values:
            input_layout.addWidget(self.browse_button)
        input_layout.addWidget(self.add_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)
        layout.addLayout(input_layout)
        layout.addWidget(self.remove_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_button.clicked.connect(self._add)
        self.input.returnPressed.connect(self._add)
        self.remove_button.clicked.connect(self._remove)
        self.browse_button.clicked.connect(self._browse)

    def value(self) -> list[str]:
        return [self.list_widget.item(index).text() for index in range(self.list_widget.count())]

    def set_value(self, value: Any) -> None:
        self.list_widget.clear()
        if isinstance(value, list):
            self.list_widget.addItems([str(item) for item in value])
        self.changed.emit()

    def _add(self) -> None:
        value = self.input.text().strip()
        if value:
            self.list_widget.addItem(value)
            self.input.clear()
            self.changed.emit()

    def _remove(self) -> None:
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.changed.emit()

    def _browse(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if selected:
            self.input.setText(selected)


class OptionEditor(QWidget):
    changed = Signal()

    def __init__(self, spec: OptionSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.control: QWidget
        if spec.repeatable:
            editor = RepeatingValueEditor(spec.kind is OptionKind.PATH)
            editor.changed.connect(self.changed)
            self.control = editor
        elif spec.kind is OptionKind.BOOL:
            combo = QComboBox()
            combo.addItem("未指定", None)
            combo.addItem("启用", True)
            combo.addItem("禁用", False)
            combo.currentIndexChanged.connect(self.changed)
            self.control = combo
        elif spec.kind is OptionKind.SWITCH:
            checkbox = QCheckBox("启用")
            checkbox.toggled.connect(self.changed)
            self.control = checkbox
        elif spec.kind is OptionKind.CHOICE:
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItem("")
            combo.addItems(spec.choices)
            combo.currentTextChanged.connect(self.changed)
            self.control = combo
        elif spec.kind is OptionKind.PATH:
            editor = PathEditor()
            editor.changed.connect(self.changed)
            self.control = editor
        else:
            line_edit = QLineEdit()
            if spec.kind is OptionKind.INTEGER:
                line_edit.setValidator(QIntValidator(-1_000_000, 1_000_000, line_edit))
            line_edit.textChanged.connect(self.changed)
            self.control = line_edit
        layout.addWidget(self.control)
        if spec.description:
            self.setToolTip(spec.description)

    def value(self) -> Any:
        if isinstance(self.control, RepeatingValueEditor):
            return self.control.value()
        if self.spec.kind is OptionKind.BOOL:
            return self.control.currentData()  # type: ignore[attr-defined]
        if self.spec.kind is OptionKind.SWITCH:
            return self.control.isChecked()  # type: ignore[attr-defined]
        if isinstance(self.control, QComboBox):
            return self.control.currentText().strip()
        if isinstance(self.control, PathEditor):
            return self.control.value()
        return self.control.text().strip()  # type: ignore[attr-defined]

    def set_value(self, value: Any) -> None:
        if isinstance(self.control, RepeatingValueEditor):
            self.control.set_value(value)
        elif self.spec.kind is OptionKind.BOOL:
            index = self.control.findData(value)  # type: ignore[attr-defined]
            self.control.setCurrentIndex(max(index, 0))  # type: ignore[attr-defined]
        elif self.spec.kind is OptionKind.SWITCH:
            self.control.setChecked(bool(value))  # type: ignore[attr-defined]
        elif isinstance(self.control, QComboBox):
            self.control.setCurrentText("" if value is None else str(value))
        elif isinstance(self.control, PathEditor):
            self.control.set_value(value)
        else:
            self.control.setText("" if value is None else str(value))  # type: ignore[attr-defined]


class AdvancedOptionsWidget(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索中文名称或 --pandoc-option")
        self.editors: dict[str, OptionEditor] = {}
        self.rows: dict[str, tuple[QLabel, OptionEditor, QGroupBox]] = {}
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        for category in CATEGORIES:
            group = QGroupBox(category)
            form = QFormLayout(group)
            for spec in (item for item in OPTION_SPECS if item.category == category):
                label = QLabel(f"{spec.label}<br><small>{spec.flag}</small>")
                editor = OptionEditor(spec)
                editor.changed.connect(self.changed)
                self.editors[spec.key] = editor
                self.rows[spec.key] = (label, editor, group)
                form.addRow(label, editor)
            body_layout.addWidget(group)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search)
        layout.addWidget(scroll, 1)
        self.search.textChanged.connect(self._filter)

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, editor in self.editors.items():
            value = editor.value()
            if value is not None and value != "" and value != [] and value is not False:
                result[key] = value
            elif editor.spec.kind is OptionKind.BOOL and value is False:
                result[key] = False
        return result

    def set_values(self, values: dict[str, Any]) -> None:
        for key, editor in self.editors.items():
            editor.set_value(values.get(key))

    def set_capabilities(self, capabilities: PandocCapabilities | None) -> None:
        for key, (label, editor, _group) in self.rows.items():
            supported = capabilities is not None and capabilities.supports(editor.spec)
            editor.setProperty("pandoc_supported", supported)
            label.setVisible(supported)
            editor.setVisible(supported)
        self._update_groups()

    def _filter(self, text: str) -> None:
        query = text.strip().casefold()
        for key, (label, editor, _group) in self.rows.items():
            haystack = f"{editor.spec.label} {editor.spec.flag} {editor.spec.category}".casefold()
            matched = (not query or query in haystack) and bool(editor.property("pandoc_supported"))
            label.setVisible(matched)
            editor.setVisible(matched)
        self._update_groups()

    def _update_groups(self) -> None:
        groups = {group for _, _, group in self.rows.values()}
        for group in groups:
            group.setVisible(any(not editor.isHidden() for _, editor, owner in self.rows.values() if owner is group))


class FormatExtensionsDialog(QDialog):
    def __init__(self, base_format: str, extensions: list[str], current: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{base_format} 格式扩展")
        self.base_format = base_format
        self.list_widget = QListWidget()
        overrides = self._parse_overrides(current.removeprefix(base_format))
        self.defaults: dict[str, bool] = {}
        for extension in extensions:
            default_enabled = extension.startswith("+")
            name = extension[1:] if extension[:1] in "+-" else extension
            self.defaults[name] = default_enabled
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            enabled = overrides.get(name, default_enabled)
            item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("仅与 Pandoc 默认值不同的扩展会写入格式字符串。"))
        layout.addWidget(self.list_widget)
        layout.addWidget(buttons)
        self.resize(440, 560)

    def format_value(self) -> str:
        suffixes: list[str] = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            enabled = item.checkState() == Qt.CheckState.Checked
            if enabled != self.defaults[item.text()]:
                suffixes.append(("+" if enabled else "-") + item.text())
        return self.base_format + "".join(suffixes)

    @staticmethod
    def _parse_overrides(value: str) -> dict[str, bool]:
        result: dict[str, bool] = {}
        marker = ""
        token = ""
        for character in value:
            if character in "+-":
                if marker and token:
                    result[token] = marker == "+"
                marker, token = character, ""
            else:
                token += character
        if marker and token:
            result[token] = marker == "+"
        return result
