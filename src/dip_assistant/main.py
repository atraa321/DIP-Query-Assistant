from __future__ import annotations

import sys

from PySide2.QtCore import Qt
from PySide2.QtGui import QIcon

from .metadata import APP_NAME
from .paths import APP_ICON_PATH
from .ui import QApplication, create_window


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    app.setQuitOnLastWindowClosed(False)
    window = create_window()
    window.setWindowTitle(APP_NAME)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
