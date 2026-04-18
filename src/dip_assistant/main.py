from __future__ import annotations

import sys

from PySide2.QtCore import Qt

from .ui import QApplication, create_window


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = create_window()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
