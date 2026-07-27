from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pandoc_gui.ui.main_window import MainWindow


def create_application(arguments: list[str] | None = None) -> QApplication:
    app = QApplication(arguments if arguments is not None else sys.argv)
    QCoreApplication.setOrganizationName("pandocGUI")
    QCoreApplication.setApplicationName("pandocGUI")
    QCoreApplication.setApplicationVersion("0.1.0")
    icon_candidates = (
        Path(__file__).parent / "resources" / "Pandoc-GUI.ico",
        Path(__file__).resolve().parents[2] / "Pandoc-GUI.ico",
        Path.cwd() / "Pandoc-GUI.ico",
    )
    icon_path = next((path for path in icon_candidates if path.is_file()), None)
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
    return app


def main() -> int:
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
