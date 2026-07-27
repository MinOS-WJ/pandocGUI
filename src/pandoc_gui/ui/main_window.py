from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from pandoc_gui import __version__
from pandoc_gui.command import (
    CommandValidationError,
    PandocCommandBuilder,
    command_preview,
    parse_windows_arguments,
    suggested_output,
)
from pandoc_gui.models import ConversionJob, JobState, PandocCapabilities
from pandoc_gui.pandoc import (
    PandocError,
    find_pandoc,
    list_extensions,
    probe_pandoc,
    run_tool,
)
from pandoc_gui.queue import JobQueue
from pandoc_gui.storage import AppStorage, StorageError
from pandoc_gui.ui.widgets import AdvancedOptionsWidget, FileListWidget, FormatExtensionsDialog


class MainWindow(QMainWindow):
    def __init__(self, storage: AppStorage | None = None) -> None:
        super().__init__()
        self.storage = storage or AppStorage()
        try:
            self.settings = self.storage.load_settings()
        except StorageError:
            self.settings = {"pandoc_path": "", "last_input_directory": "", "last_output_directory": ""}
        try:
            self.presets = self.storage.load_presets()
        except StorageError as error:
            self.presets = {}
            QMessageBox.warning(self, "预设读取失败", str(error))
        self.capabilities: PandocCapabilities | None = None
        self.builder = PandocCommandBuilder("pandoc.exe")
        self.queue = JobQueue(self.builder, self)
        self.setWindowTitle(f"pandocGUI {__version__}")
        self.resize(1180, 820)
        self._build_ui()
        self._connect_queue()
        self._refresh_presets()
        self._load_pandoc(self.settings.get("pandoc_path", ""), show_error=False)

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.converter_page = self._build_converter_page()
        self.queue_page = self._build_queue_page()
        self.tools_page = self._build_tools_page()
        self.settings_page = self._build_settings_page()
        self.tabs.addTab(self.converter_page, "转换器")
        self.tabs.addTab(self.queue_page, "任务队列")
        self.tabs.addTab(self.tools_page, "Pandoc 工具")
        self.tabs.addTab(self.settings_page, "设置")
        self.setCentralWidget(self.tabs)
        self.status_label = QLabel("正在检测 Pandoc…")
        self.statusBar().addPermanentWidget(self.status_label)

    def _build_converter_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("预设："))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(220)
        preset_row.addWidget(self.preset_combo)
        for text, slot in (
            ("加载", self._load_selected_preset),
            ("保存当前", self._save_preset),
            ("删除", self._delete_preset),
            ("导入", self._import_preset),
            ("导出", self._export_preset),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            preset_row.addWidget(button)
        preset_row.addStretch()
        outer.addLayout(preset_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        basics = QWidget()
        basics_layout = QVBoxLayout(basics)
        basics_layout.setContentsMargins(0, 0, 0, 0)
        self.input_list = FileListWidget()
        self.input_list.setMinimumHeight(120)
        self.input_list.files_dropped.connect(self._add_input_paths)
        basics_layout.addWidget(QLabel("输入文件（按列表顺序传给 Pandoc）："))
        basics_layout.addWidget(self.input_list)
        input_buttons = QHBoxLayout()
        for text, slot in (
            ("添加文件…", self._choose_inputs),
            ("移除", self._remove_inputs),
            ("上移", lambda: self._move_input(-1)),
            ("下移", lambda: self._move_input(1)),
            ("清空", self._clear_inputs),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            input_buttons.addWidget(button)
        input_buttons.addStretch()
        basics_layout.addLayout(input_buttons)

        form = QFormLayout()
        self.from_combo = QComboBox()
        self.from_combo.setEditable(True)
        self.from_extensions_button = QPushButton("扩展…")
        from_row = QHBoxLayout()
        from_row.addWidget(self.from_combo, 1)
        from_row.addWidget(self.from_extensions_button)
        form.addRow("输入格式：", from_row)
        self.to_combo = QComboBox()
        self.to_combo.setEditable(True)
        self.to_extensions_button = QPushButton("扩展…")
        to_row = QHBoxLayout()
        to_row.addWidget(self.to_combo, 1)
        to_row.addWidget(self.to_extensions_button)
        form.addRow("输出格式：", to_row)
        self.output_edit = QLineEdit()
        output_button = QPushButton("浏览…")
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(output_button)
        form.addRow("输出文件：", output_row)
        self.working_directory_edit = QLineEdit()
        working_button = QPushButton("浏览…")
        working_row = QHBoxLayout()
        working_row.addWidget(self.working_directory_edit, 1)
        working_row.addWidget(working_button)
        form.addRow("工作目录：", working_row)
        basics_layout.addLayout(form)

        self.advanced_options = AdvancedOptionsWidget()
        splitter.addWidget(basics)
        splitter.addWidget(self.advanced_options)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, 1)

        extra_layout = QFormLayout()
        self.extra_args_edit = QLineEdit()
        self.extra_args_edit.setPlaceholderText("例如：--new-pandoc-option=value")
        extra_layout.addRow("附加参数：", self.extra_args_edit)
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setMaximumHeight(82)
        extra_layout.addRow("命令预览：", self.preview_edit)
        outer.addLayout(extra_layout)

        action_row = QHBoxLayout()
        refresh_button = QPushButton("刷新预览")
        refresh_button.clicked.connect(self._refresh_preview)
        self.convert_button = QPushButton("开始转换")
        self.convert_button.setDefault(True)
        self.convert_button.clicked.connect(lambda: self._submit_job(True))
        self.enqueue_button = QPushButton("加入队列")
        self.enqueue_button.clicked.connect(lambda: self._submit_job(False))
        action_row.addStretch()
        action_row.addWidget(refresh_button)
        action_row.addWidget(self.enqueue_button)
        action_row.addWidget(self.convert_button)
        outer.addLayout(action_row)

        self.from_extensions_button.clicked.connect(lambda: self._edit_extensions(self.from_combo))
        self.to_extensions_button.clicked.connect(lambda: self._edit_extensions(self.to_combo))
        output_button.clicked.connect(self._choose_output)
        working_button.clicked.connect(self._choose_working_directory)
        self.from_combo.currentTextChanged.connect(self._refresh_preview)
        self.to_combo.currentTextChanged.connect(self._output_format_changed)
        self.output_edit.textChanged.connect(self._refresh_preview)
        self.working_directory_edit.textChanged.connect(self._refresh_preview)
        self.extra_args_edit.textChanged.connect(self._refresh_preview)
        self.advanced_options.changed.connect(self._refresh_preview)
        return page

    def _build_queue_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.job_table = QTableWidget(0, 5)
        self.job_table.setHorizontalHeaderLabels(["状态", "输入", "输出格式", "输出文件", "退出码"])
        self.job_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.job_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.job_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.job_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.job_table, 2)
        buttons = QHBoxLayout()
        cancel_button = QPushButton("取消当前任务")
        cancel_button.clicked.connect(self.queue.cancel_active)
        retry_button = QPushButton("重试选中任务")
        retry_button.clicked.connect(self._retry_selected_job)
        clear_button = QPushButton("清除已完成")
        clear_button.clicked.connect(self.queue.clear_finished)
        buttons.addWidget(cancel_button)
        buttons.addWidget(retry_button)
        buttons.addWidget(clear_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addWidget(QLabel("运行日志："))
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit, 1)
        return page

    def _build_tools_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.tool_combo = QComboBox()
        tool_items = (
            ("列出输入格式", "--list-input-formats", False),
            ("列出输出格式", "--list-output-formats", False),
            ("列出格式扩展", "--list-extensions", True),
            ("列出高亮语言", "--list-highlight-languages", False),
            ("列出高亮样式", "--list-highlight-styles", False),
            ("输出默认模板", "--print-default-template", True),
            ("输出默认数据文件", "--print-default-data-file", True),
            ("输出高亮样式", "--print-highlight-style", True),
            ("显示版本", "--version", False),
            ("显示帮助", "--help", False),
            ("生成 Bash 补全", "--bash-completion", False),
        )
        for label, flag, requires_value in tool_items:
            self.tool_combo.addItem(label, (flag, requires_value))
        self.tool_parameter_edit = QLineEdit()
        self.tool_parameter_edit.setPlaceholderText("格式、文件名或样式名称")
        form.addRow("工具：", self.tool_combo)
        form.addRow("参数：", self.tool_parameter_edit)
        layout.addLayout(form)
        actions = QHBoxLayout()
        run_button = QPushButton("运行")
        run_button.clicked.connect(self._run_tool)
        save_button = QPushButton("保存结果…")
        save_button.clicked.connect(self._save_tool_result)
        actions.addWidget(run_button)
        actions.addWidget(save_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.tool_result_edit = QPlainTextEdit()
        self.tool_result_edit.setReadOnly(True)
        layout.addWidget(self.tool_result_edit, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.pandoc_path_edit = QLineEdit(str(self.settings.get("pandoc_path", "")))
        browse_button = QPushButton("浏览…")
        path_row = QHBoxLayout()
        path_row.addWidget(self.pandoc_path_edit, 1)
        path_row.addWidget(browse_button)
        form.addRow("pandoc.exe：", path_row)
        self.pandoc_info_label = QLabel("尚未检测")
        self.pandoc_info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("检测结果：", self.pandoc_info_label)
        layout.addLayout(form)
        action_row = QHBoxLayout()
        detect_button = QPushButton("自动检测")
        detect_button.clicked.connect(lambda: self._load_pandoc("", show_error=True))
        validate_button = QPushButton("验证并保存")
        validate_button.clicked.connect(lambda: self._load_pandoc(self.pandoc_path_edit.text(), show_error=True))
        download_button = QPushButton("打开 Pandoc 官方下载页")
        download_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://pandoc.org/installing.html"))
        )
        action_row.addWidget(detect_button)
        action_row.addWidget(validate_button)
        action_row.addWidget(download_button)
        action_row.addStretch()
        layout.addLayout(action_row)
        note = QLabel(
            "pandocGUI 不会下载或捆绑 Pandoc、TeX、PDF 引擎及过滤器。"
            "外部工具缺失时会保留 Pandoc 的原始错误信息。"
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        browse_button.clicked.connect(self._choose_pandoc)
        return page

    def _connect_queue(self) -> None:
        self.queue.job_added.connect(lambda _job: self._refresh_jobs())
        self.queue.job_updated.connect(lambda _job: self._refresh_jobs())
        self.queue.log_received.connect(self._append_log)

    def _load_pandoc(self, configured_path: str, show_error: bool) -> None:
        try:
            executable = find_pandoc(configured_path or None)
            capabilities = probe_pandoc(executable)
        except PandocError as error:
            self.capabilities = None
            self.convert_button.setEnabled(False)
            self.enqueue_button.setEnabled(False)
            self.advanced_options.set_capabilities(None)
            self.pandoc_info_label.setText(str(error))
            self.status_label.setText("Pandoc 不可用")
            if show_error:
                QMessageBox.warning(self, "Pandoc 不可用", str(error))
            return
        self.capabilities = capabilities
        self.builder = PandocCommandBuilder(capabilities.executable)
        self.queue.set_builder(self.builder)
        self.from_combo.clear()
        self.from_combo.addItems(capabilities.input_formats)
        self.to_combo.clear()
        self.to_combo.addItems(capabilities.output_formats)
        self.from_combo.setCurrentText("markdown")
        self.to_combo.setCurrentText("html")
        self.advanced_options.set_capabilities(capabilities)
        self.convert_button.setEnabled(True)
        self.enqueue_button.setEnabled(True)
        self.pandoc_path_edit.setText(str(capabilities.executable))
        self.pandoc_info_label.setText(
            f"Pandoc {capabilities.version}\n{len(capabilities.input_formats)} 个输入格式，"
            f"{len(capabilities.output_formats)} 个输出格式"
        )
        self.status_label.setText(f"Pandoc {capabilities.version}")
        self.settings["pandoc_path"] = str(capabilities.executable)
        self._save_settings()
        self._refresh_preview()

    def _choose_pandoc(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "选择 pandoc.exe", filter="Pandoc (pandoc.exe);;程序 (*.exe)")
        if selected:
            self.pandoc_path_edit.setText(selected)

    def _choose_inputs(self) -> None:
        selected, _ = QFileDialog.getOpenFileNames(
            self,
            "选择输入文件",
            str(self.settings.get("last_input_directory", "")),
            "所有文件 (*.*)",
        )
        if selected:
            self._add_input_paths([Path(path) for path in selected])

    def _add_input_paths(self, paths: list[Path]) -> None:
        existing = {self.input_list.item(index).text().casefold() for index in range(self.input_list.count())}
        for path in paths:
            resolved = str(path.resolve())
            if resolved.casefold() not in existing:
                self.input_list.addItem(resolved)
                existing.add(resolved.casefold())
        if paths:
            self.settings["last_input_directory"] = str(paths[0].parent)
            if not self.working_directory_edit.text():
                self.working_directory_edit.setText(str(paths[0].parent))
        self._suggest_output()
        self._refresh_preview()

    def _remove_inputs(self) -> None:
        for item in self.input_list.selectedItems():
            self.input_list.takeItem(self.input_list.row(item))
        self._suggest_output()
        self._refresh_preview()

    def _clear_inputs(self) -> None:
        self.input_list.clear()
        self.output_edit.clear()
        self._refresh_preview()

    def _move_input(self, offset: int) -> None:
        row = self.input_list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.input_list.count():
            return
        item = self.input_list.takeItem(row)
        self.input_list.insertItem(target, item)
        self.input_list.setCurrentRow(target)
        self._suggest_output()
        self._refresh_preview()

    def _choose_output(self) -> None:
        suggested = self.output_edit.text() or str(self.settings.get("last_output_directory", ""))
        selected, _ = QFileDialog.getSaveFileName(self, "选择输出文件", suggested, "所有文件 (*.*)")
        if selected:
            self.output_edit.setText(selected)
            self.settings["last_output_directory"] = str(Path(selected).parent)

    def _choose_working_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择工作目录", self.working_directory_edit.text())
        if selected:
            self.working_directory_edit.setText(selected)

    def _output_format_changed(self) -> None:
        self._suggest_output()
        self._refresh_preview()

    def _suggest_output(self) -> None:
        inputs = self._input_paths()
        output = suggested_output(inputs, self._base_format(self.to_combo.currentText()))
        if output:
            self.output_edit.setText(str(output))

    def _edit_extensions(self, combo: QComboBox) -> None:
        if not self.capabilities:
            return
        current = combo.currentText().strip()
        base = self._base_format(current)
        if not base:
            return
        try:
            extensions = list_extensions(self.capabilities, base)
        except PandocError as error:
            QMessageBox.warning(self, "无法读取扩展", str(error))
            return
        dialog = FormatExtensionsDialog(base, extensions, current, self)
        if dialog.exec():
            combo.setCurrentText(dialog.format_value())

    @staticmethod
    def _base_format(format_value: str) -> str:
        indices = [index for marker in "+-" if (index := format_value.find(marker)) >= 0]
        return format_value[: min(indices)] if indices else format_value

    def _input_paths(self) -> list[Path]:
        return [Path(self.input_list.item(index).text()) for index in range(self.input_list.count())]

    def _create_job(self) -> ConversionJob:
        arguments = parse_windows_arguments(self.extra_args_edit.text())
        output = Path(self.output_edit.text().strip()).expanduser()
        working = Path(self.working_directory_edit.text().strip()).expanduser()
        return ConversionJob(
            inputs=self._input_paths(),
            output=output,
            from_format=self.from_combo.currentText().strip(),
            to_format=self.to_combo.currentText().strip(),
            working_directory=working,
            options=self.advanced_options.values(),
            extra_args=arguments,
        )

    def _refresh_preview(self) -> None:
        if not self.capabilities:
            self.preview_edit.setPlainText("请先配置 Pandoc 3.x。")
            return
        try:
            invocation = self.builder.build(self._create_job())
            self.preview_edit.setPlainText(command_preview(invocation))
        except (CommandValidationError, OSError, ValueError) as error:
            self.preview_edit.setPlainText(f"准备就绪后显示命令：{error}")

    def _submit_job(self, switch_to_queue: bool) -> None:
        try:
            job = self._create_job()
            self.builder.validate(job)
        except (CommandValidationError, OSError, ValueError) as error:
            QMessageBox.warning(self, "任务无效", str(error))
            return
        if job.output.exists():
            answer = QMessageBox.question(
                self,
                "覆盖输出文件",
                f"输出文件已存在：\n{job.output}\n\n是否允许 Pandoc 覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.queue.enqueue(job)
        except (CommandValidationError, RuntimeError) as error:
            QMessageBox.warning(self, "无法加入队列", str(error))
            return
        if switch_to_queue:
            self.tabs.setCurrentWidget(self.queue_page)

    def _refresh_jobs(self) -> None:
        self.job_table.setRowCount(len(self.queue.jobs))
        for row, job in enumerate(self.queue.jobs):
            values = (
                job.state.value,
                "; ".join(path.name for path in job.inputs),
                job.to_format,
                str(job.output),
                "" if job.exit_code is None else str(job.exit_code),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, job.identifier)
                self.job_table.setItem(row, column, item)
        self.job_table.resizeRowsToContents()

    def _retry_selected_job(self) -> None:
        row = self.job_table.currentRow()
        if row >= 0 and (item := self.job_table.item(row, 0)):
            self.queue.retry(str(item.data(Qt.ItemDataRole.UserRole)))

    def _append_log(self, text: str) -> None:
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.log_edit.setTextCursor(cursor)

    def _run_tool(self) -> None:
        if not self.capabilities:
            QMessageBox.warning(self, "Pandoc 不可用", "请先在设置中配置 Pandoc 3.x。")
            return
        flag, requires_value = self.tool_combo.currentData()
        parameter = self.tool_parameter_edit.text().strip()
        if requires_value and not parameter:
            QMessageBox.warning(self, "缺少参数", "此工具需要格式、文件名或样式名称。")
            return
        arguments = [f"{flag}={parameter}" if parameter else flag]
        try:
            result = run_tool(self.capabilities, arguments)
        except PandocError as error:
            QMessageBox.warning(self, "工具运行失败", str(error))
            return
        self.tool_result_edit.setPlainText(result)

    def _save_tool_result(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(self, "保存工具结果", filter="文本文件 (*.txt);;所有文件 (*.*)")
        if not selected:
            return
        try:
            Path(selected).write_text(self.tool_result_edit.toPlainText(), encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(self, "保存失败", str(error))

    def _current_preset_payload(self) -> dict[str, Any]:
        return {
            "from_format": self.from_combo.currentText().strip(),
            "to_format": self.to_combo.currentText().strip(),
            "options": self.advanced_options.values(),
            "extra_args": parse_windows_arguments(self.extra_args_edit.text()),
        }

    def _refresh_presets(self) -> None:
        current = self.preset_combo.currentText() if hasattr(self, "preset_combo") else ""
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(self.presets, key=str.casefold))
        if current:
            self.preset_combo.setCurrentText(current)

    def _load_selected_preset(self) -> None:
        payload = self.presets.get(self.preset_combo.currentText())
        if not payload:
            return
        self.from_combo.setCurrentText(payload["from_format"])
        self.to_combo.setCurrentText(payload["to_format"])
        self.advanced_options.set_values(payload["options"])
        self.extra_args_edit.setText(subprocess.list2cmdline(payload["extra_args"]))
        self._refresh_preview()

    def _save_preset(self) -> None:
        name, accepted = QInputDialog.getText(self, "保存预设", "预设名称：", text=self.preset_combo.currentText())
        if not accepted or not name.strip():
            return
        try:
            self.presets[name.strip()] = self._current_preset_payload()
            self.storage.save_presets(self.presets)
        except (StorageError, ValueError) as error:
            QMessageBox.warning(self, "保存失败", str(error))
            return
        self._refresh_presets()
        self.preset_combo.setCurrentText(name.strip())

    def _delete_preset(self) -> None:
        name = self.preset_combo.currentText()
        if not name:
            return
        del self.presets[name]
        try:
            self.storage.save_presets(self.presets)
        except StorageError as error:
            QMessageBox.warning(self, "删除失败", str(error))
        self._refresh_presets()

    def _import_preset(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "导入预设", filter="pandocGUI 预设 (*.json)")
        if not selected:
            return
        try:
            name, payload = self.storage.import_preset(Path(selected))
            self.presets[name] = payload
            self.storage.save_presets(self.presets)
        except StorageError as error:
            QMessageBox.warning(self, "导入失败", str(error))
            return
        self._refresh_presets()
        self.preset_combo.setCurrentText(name)

    def _export_preset(self) -> None:
        name = self.preset_combo.currentText()
        if not name:
            return
        selected, _ = QFileDialog.getSaveFileName(self, "导出预设", f"{name}.json", "JSON (*.json)")
        if not selected:
            return
        try:
            self.storage.export_preset(Path(selected), name, self.presets[name])
        except StorageError as error:
            QMessageBox.warning(self, "导出失败", str(error))

    def _save_settings(self) -> None:
        try:
            self.storage.save_settings(self.settings)
        except StorageError as error:
            self.statusBar().showMessage(str(error), 5000)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.queue.runner.running:
            answer = QMessageBox.question(
                self,
                "任务仍在运行",
                "关闭应用会取消当前转换，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.queue.cancel_active()
        self._save_settings()
        event.accept()
