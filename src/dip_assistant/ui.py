from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List, Optional

from .config_store import AppConfig, ConfigStore
from .paths import DEFAULT_DB_PATH, SOURCE_DIR
from .query_service import DipQueryService, QueryResult

try:
    from PySide2.QtCore import QPoint, Qt
    from PySide2.QtGui import QColor, QIcon, QPainter, QPixmap
    from PySide2.QtWidgets import (
        QAction,
        QApplication,
        QCheckBox,
        QDesktopWidget,
        QDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QSystemTrayIcon,
        QTableWidget,
        QTableWidgetItem,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("运行桌面程序前请先安装 PySide2。") from exc


class SettingsDialog(QDialog):
    def __init__(
        self,
        config: AppConfig,
        on_save: Callable[[Optional[float], Optional[float], float, bool], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super(SettingsDialog, self).__init__(parent)
        self._on_save = on_save
        self.setWindowTitle("后台设置")
        self.setModal(True)
        self.setFixedWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)

        self.resident_input = QLineEdit("" if config.resident_point_value is None else str(config.resident_point_value))
        self.employee_input = QLineEdit("" if config.employee_point_value is None else str(config.employee_point_value))
        self.opacity_input = QLineEdit(str(int(config.idle_opacity * 100)))
        self.always_on_top_checkbox = QCheckBox("默认前台显示（置顶悬浮）")
        self.always_on_top_checkbox.setChecked(config.always_on_top)

        form.addRow("居民医保点值", self.resident_input)
        form.addRow("职工医保点值", self.employee_input)
        form.addRow("空闲透明度(%)", self.opacity_input)
        form.addRow("", self.always_on_top_checkbox)
        layout.addLayout(form)

        hint = QLabel("主界面不再显示路径类长信息；空闲透明度建议设置在 60 到 85 之间。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #5f6778; font-size: 11px;")
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("保存")
        save_button.clicked.connect(self._save)
        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)

    def _save(self) -> None:
        try:
            resident_value = _parse_optional_float(self.resident_input.text())
            employee_value = _parse_optional_float(self.employee_input.text())
            opacity = _parse_opacity_percent(self.opacity_input.text())
        except ValueError:
            QMessageBox.warning(self, "设置错误", "请填写有效数字。透明度请输入 35 到 100 之间的整数。")
            return

        self._on_save(
            resident_value,
            employee_value,
            opacity,
            self.always_on_top_checkbox.isChecked(),
        )
        self.accept()


class FloatingDipWindow(QMainWindow):
    def __init__(self, config_store: ConfigStore) -> None:
        super(FloatingDipWindow, self).__init__()
        self.config_store = config_store
        self.config = config_store.load()
        self.query_service = DipQueryService(Path(self.config.database_path or str(DEFAULT_DB_PATH)))
        self.drag_offset = None  # type: Optional[QPoint]
        self.last_results = []  # type: List[QueryResult]
        self.primary_result = None  # type: Optional[QueryResult]

        self.setWindowTitle("DIP 查询助手")
        self._apply_window_mode(initial=True)
        self.resize(self.config.window_width, self.config.window_height)
        self.move(self.config.window_x, self.config.window_y)
        self.setMinimumSize(760, 520)

        self._init_ui()
        self._init_tray()
        self._refresh_status()
        self._apply_idle_opacity(active=False)

    def _apply_window_mode(self, initial: bool = False) -> None:
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.config.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        if not initial:
            self.show()

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        shell = QFrame()
        shell.setStyleSheet(
            """
            QFrame#Shell {
                background: #f8fbff;
                border: 1px solid #d8e2f0;
                border-radius: 14px;
            }
            QLabel#TitleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #162033;
            }
            QLabel#MutedLabel {
                font-size: 13px;
                color: #687386;
            }
            QLabel#SectionTitle {
                font-size: 15px;
                font-weight: bold;
                color: #21304a;
            }
            QLabel#ValueLabel {
                font-size: 15px;
                color: #1d2740;
            }
            QLabel#AmountValue {
                font-size: 18px;
                font-weight: bold;
                color: #183e85;
            }
            QLineEdit {
                padding: 8px 10px;
                border: 1px solid #c8d5e7;
                border-radius: 10px;
                background: white;
                font-size: 15px;
                min-height: 18px;
            }
            QPushButton, QToolButton {
                min-height: 32px;
                min-width: 44px;
                padding: 4px 10px;
                border: 1px solid #b9c8dc;
                border-radius: 10px;
                background: white;
                font-size: 14px;
            }
            QPushButton:hover, QToolButton:hover {
                background: #edf4ff;
            }
            QFrame#ResultCard, QFrame#StatusBar, QFrame#CandidateCard {
                background: white;
                border: 1px solid #dbe4f0;
                border-radius: 12px;
            }
            QTableWidget {
                background: transparent;
                border: none;
                font-size: 14px;
            }
            QHeaderView::section {
                background: #f4f8fd;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #dde6f2;
                font-size: 13px;
                font-weight: bold;
                color: #30415e;
            }
            """
        )
        shell.setObjectName("Shell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(12, 12, 12, 12)
        shell_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_label = QLabel("DIP 查询助手")
        title_label.setObjectName("TitleLabel")
        title_row.addWidget(title_label)
        title_row.addStretch(1)

        self.layer_button = QToolButton()
        self.layer_button.clicked.connect(self.toggle_always_on_top)
        self.clear_button = QToolButton()
        self.clear_button.setText("清空")
        self.clear_button.clicked.connect(self.clear_results)
        self.minimize_button = QToolButton()
        self.minimize_button.setText("一")
        self.minimize_button.clicked.connect(self.hide_to_tray)
        self.close_button = QToolButton()
        self.close_button.setText("×")
        self.close_button.clicked.connect(self.hide_to_tray)
        title_row.addWidget(self.layer_button)
        title_row.addWidget(self.clear_button)
        title_row.addWidget(self.minimize_button)
        title_row.addWidget(self.close_button)
        shell_layout.addLayout(title_row)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入 DIP 编码 / 病种名称")
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_button = QPushButton("查询")
        self.search_button.clicked.connect(self.perform_search)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_button)
        shell_layout.addLayout(search_row)

        self.message_label = QLabel("输入编码或病种名称后按回车，可快速查看主结果。")
        self.message_label.setObjectName("MutedLabel")
        shell_layout.addWidget(self.message_label)

        self.result_card = QFrame()
        self.result_card.setObjectName("ResultCard")
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(12, 10, 12, 10)
        result_layout.setSpacing(8)

        result_title = QLabel("主结果")
        result_title.setObjectName("SectionTitle")
        result_layout.addWidget(result_title)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(18)
        summary_grid.setVerticalSpacing(4)
        self.code_title = QLabel("DIP编码")
        self.code_title.setObjectName("MutedLabel")
        self.code_value = QLabel("未查询")
        self.code_value.setObjectName("ValueLabel")
        self.name_title = QLabel("病种名称")
        self.name_title.setObjectName("MutedLabel")
        self.name_value = QLabel("请先输入编码或名称")
        self.name_value.setWordWrap(True)
        self.name_value.setObjectName("ValueLabel")
        self.resident_amount_title = QLabel("居民医保金额")
        self.resident_amount_title.setObjectName("MutedLabel")
        self.resident_amount_value = QLabel("未设置点值")
        self.resident_amount_value.setObjectName("AmountValue")
        self.employee_amount_title = QLabel("职工医保金额")
        self.employee_amount_title.setObjectName("MutedLabel")
        self.employee_amount_value = QLabel("未设置点值")
        self.employee_amount_value.setObjectName("AmountValue")
        summary_grid.addWidget(self.code_title, 0, 0)
        summary_grid.addWidget(self.name_title, 0, 1)
        summary_grid.addWidget(self.code_value, 1, 0)
        summary_grid.addWidget(self.name_value, 1, 1)
        summary_grid.addWidget(self.resident_amount_title, 2, 0)
        summary_grid.addWidget(self.employee_amount_title, 2, 1)
        summary_grid.addWidget(self.resident_amount_value, 3, 0)
        summary_grid.addWidget(self.employee_amount_value, 3, 1)
        summary_grid.setColumnStretch(0, 1)
        summary_grid.setColumnStretch(1, 2)
        result_layout.addLayout(summary_grid)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        self.score_value = QLabel("DIP分值：-")
        self.score_value.setObjectName("MutedLabel")
        self.match_value = QLabel("匹配方式：-")
        self.match_value.setObjectName("MutedLabel")
        bottom_row.addWidget(self.score_value)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.match_value)
        result_layout.addLayout(bottom_row)

        shell_layout.addWidget(self.result_card)

        self.candidate_card = QFrame()
        self.candidate_card.setObjectName("CandidateCard")
        candidate_layout = QVBoxLayout(self.candidate_card)
        candidate_layout.setContentsMargins(10, 8, 10, 8)
        candidate_layout.setSpacing(6)
        self.candidate_title = QLabel("候选结果")
        self.candidate_title.setObjectName("SectionTitle")
        self.candidate_table = QTableWidget(0, 3)
        self.candidate_table.setHorizontalHeaderLabels(["DIP编码", "病种名称", "分值"])
        self.candidate_table.verticalHeader().setVisible(False)
        self.candidate_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.candidate_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.candidate_table.setSelectionMode(QTableWidget.SingleSelection)
        self.candidate_table.setMinimumHeight(220)
        self.candidate_table.horizontalHeader().setStretchLastSection(False)
        self.candidate_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.candidate_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.candidate_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.candidate_table.cellClicked.connect(self.select_candidate_row)
        candidate_layout.addWidget(self.candidate_title)
        candidate_layout.addWidget(self.candidate_table)
        self.candidate_card.hide()
        shell_layout.addWidget(self.candidate_card)

        status_card = QFrame()
        status_card.setObjectName("StatusBar")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(10, 6, 10, 6)
        status_layout.setSpacing(14)
        self.resident_label = QLabel("")
        self.resident_label.setObjectName("MutedLabel")
        self.employee_label = QLabel("")
        self.employee_label.setObjectName("MutedLabel")
        self.mode_label = QLabel("")
        self.mode_label.setObjectName("MutedLabel")
        status_layout.addWidget(self.resident_label)
        status_layout.addWidget(self.employee_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.mode_label)
        shell_layout.addWidget(status_card)

        root.addWidget(shell)

    def _init_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self._build_tray_icon(), self)
        self.tray_icon.setToolTip("DIP 查询助手")
        self.tray_icon.activated.connect(self._on_tray_activated)

        menu = QMenu(self)
        toggle_action = QAction("显示/隐藏窗口", self)
        toggle_action.triggered.connect(self.toggle_visibility)
        self.layer_action = QAction("", self)
        self.layer_action.triggered.connect(self.toggle_always_on_top)
        settings_action = QAction("后台设置", self)
        settings_action.triggered.connect(self.open_settings)
        open_source_action = QAction("打开数据源目录", self)
        open_source_action.triggered.connect(self.open_source_directory)
        rebuild_action = QAction("重建查询库", self)
        rebuild_action.triggered.connect(self.rebuild_database)
        exit_action = QAction("退出程序", self)
        exit_action.triggered.connect(self.exit_app)

        menu.addAction(toggle_action)
        menu.addAction(self.layer_action)
        menu.addAction(settings_action)
        menu.addAction(open_source_action)
        menu.addAction(rebuild_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _build_tray_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#2a66d9"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(6, 6, 52, 52, 14, 14)
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(20)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "D")
        painter.end()
        return QIcon(pixmap)

    def _refresh_status(self) -> None:
        self.resident_label.setText("居民点值：%s" % _format_point_value(self.config.resident_point_value))
        self.employee_label.setText("职工点值：%s" % _format_point_value(self.config.employee_point_value))
        mode_text = "前台显示" if self.config.always_on_top else "底层显示"
        self.mode_label.setText("%s | 空闲透明度 %s%%" % (mode_text, int(self.config.idle_opacity * 100)))
        self.layer_button.setText("底层" if self.config.always_on_top else "置顶")
        self.layer_action.setText("切换为底层显示" if self.config.always_on_top else "切换为前台显示")

    def perform_search(self) -> None:
        keyword = self.search_input.text().strip()
        if not keyword:
            self._show_message("请输入 DIP 编码或病种关键词。")
            self.clear_results(keep_keyword=True)
            return

        try:
            results = self.query_service.search(
                keyword,
                self.config.resident_point_value,
                self.config.employee_point_value,
            )
        except Exception as exc:
            self.clear_results(keep_keyword=True)
            self._show_message("查询失败：%s" % exc)
            return

        if not results:
            self.clear_results(keep_keyword=True)
            self._show_message("未找到对应 DIP 病组，请检查编码或名称关键词。")
            return

        self.last_results = results
        self._show_primary_result(results[0])
        self._populate_candidates(results)
        self._show_message("已找到 %s 条结果，主结果显示最优匹配。" % len(results))

    def _show_primary_result(self, result: QueryResult) -> None:
        self.primary_result = result
        self.code_value.setText(result.code)
        self.name_value.setText("%s（%s）" % (result.name, result.group_type))
        self.resident_amount_value.setText(_format_currency(result.resident_estimated_amount))
        self.employee_amount_value.setText(_format_currency(result.employee_estimated_amount))
        self.score_value.setText("DIP分值：%s" % _format_number(result.score_value))
        self.match_value.setText("匹配方式：%s" % ("精确编码" if result.match_type == "exact_code" else "名称匹配"))

    def _populate_candidates(self, results: List[QueryResult]) -> None:
        if len(results) <= 1:
            self.candidate_card.hide()
            self.candidate_table.setRowCount(0)
            return

        self.candidate_card.show()
        self.candidate_table.setRowCount(len(results))
        self.candidate_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        for row_index, result in enumerate(results):
            values = [result.code, result.name, _format_number(result.score_value)]
            for column_index, value in enumerate(values):
                self.candidate_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.candidate_table.selectRow(0)
        self.candidate_title.setText("候选结果（单击切换主结果）")
        self.candidate_table.resizeRowsToContents()

    def select_candidate_row(self, row: int, _column: int) -> None:
        if 0 <= row < len(self.last_results):
            self._show_primary_result(self.last_results[row])

    def clear_results(self, keep_keyword: bool = False) -> None:
        self.last_results = []
        self.primary_result = None
        self.code_value.setText("未查询")
        self.name_value.setText("请先输入编码或名称")
        self.resident_amount_value.setText("未设置点值" if self.config.resident_point_value is None else "-")
        self.employee_amount_value.setText("未设置点值" if self.config.employee_point_value is None else "-")
        self.score_value.setText("DIP分值：-")
        self.match_value.setText("匹配方式：-")
        self.candidate_table.setRowCount(0)
        self.candidate_card.hide()
        if not keep_keyword:
            self.search_input.clear()
        self._show_message("输入编码或病种名称后按回车，可快速查看主结果。")

    def _show_message(self, message: str) -> None:
        self.message_label.setText(message)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self._save_settings, self)
        dialog.exec_()

    def _save_settings(
        self,
        resident_value: Optional[float],
        employee_value: Optional[float],
        idle_opacity: float,
        always_on_top: bool,
    ) -> None:
        self.config.resident_point_value = resident_value
        self.config.employee_point_value = employee_value
        self.config.idle_opacity = idle_opacity
        mode_changed = self.config.always_on_top != always_on_top
        self.config.always_on_top = always_on_top
        self.config_store.save(self.config)
        if mode_changed:
            self._apply_window_mode()
        self._refresh_status()
        self._apply_idle_opacity(active=self.isActiveWindow())
        if self.search_input.text().strip():
            self.perform_search()
        else:
            self.clear_results(keep_keyword=True)

    def toggle_always_on_top(self) -> None:
        self.config.always_on_top = not self.config.always_on_top
        self.config_store.save(self.config)
        self._apply_window_mode()
        self._refresh_status()

    def open_source_directory(self) -> None:
        path = self.config.source_directory or str(SOURCE_DIR)
        QDesktopServicesWrapper.open_path(path)

    def rebuild_database(self) -> None:
        from .data_builder import build_lookup_database

        source_dir = Path(self.config.source_directory or str(SOURCE_DIR))
        source_excel = source_dir / "平顶山2025年DIP2.0分组目录库.xlsx"
        db_path = Path(self.config.database_path or str(DEFAULT_DB_PATH))
        try:
            count = build_lookup_database(source_excel=source_excel, db_path=db_path)
        except Exception as exc:
            QMessageBox.warning(self, "重建失败", "重建查询库失败：%s" % exc)
            return

        self.query_service = DipQueryService(db_path)
        self._refresh_status()
        self._show_message("查询库重建完成，共导入 %s 条目录记录。" % count)

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide_to_tray()
        else:
            self.show_from_tray()

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self._apply_idle_opacity(active=True)

    def hide_to_tray(self) -> None:
        self._persist_window_geometry()
        self.hide()

    def exit_app(self) -> None:
        self._persist_window_geometry()
        self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()
        self.hide_to_tray()

    def changeEvent(self, event) -> None:  # type: ignore[override]
        if self.isMinimized():
            event.ignore()
            self.hide_to_tray()
            return
        super(FloatingDipWindow, self).changeEvent(event)

    def focusInEvent(self, event) -> None:  # type: ignore[override]
        self._apply_idle_opacity(active=True)
        super(FloatingDipWindow, self).focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # type: ignore[override]
        self._apply_idle_opacity(active=False)
        super(FloatingDipWindow, self).focusOutEvent(event)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._apply_idle_opacity(active=True)
        super(FloatingDipWindow, self).enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._apply_idle_opacity(active=False)
        super(FloatingDipWindow, self).leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.buttons() == Qt.LeftButton and self.drag_offset is not None:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self.drag_offset = None
        self._snap_to_screen()
        self._persist_window_geometry()
        event.accept()

    def _apply_idle_opacity(self, active: bool) -> None:
        self.setWindowOpacity(1.0 if active else self.config.idle_opacity)

    def _snap_to_screen(self) -> None:
        desktop = QDesktopWidget().availableGeometry(self)
        geo = self.frameGeometry()
        x = geo.x()
        y = geo.y()
        margin = 12
        if abs(x - desktop.left()) <= 20:
            x = desktop.left() + margin
        elif abs(geo.right() - desktop.right()) <= 20:
            x = desktop.right() - geo.width() - margin
        if abs(y - desktop.top()) <= 20:
            y = desktop.top() + margin
        elif abs(geo.bottom() - desktop.bottom()) <= 20:
            y = desktop.bottom() - geo.height() - margin
        self.move(x, y)

    def _persist_window_geometry(self) -> None:
        self.config.window_x = self.x()
        self.config.window_y = self.y()
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        self.config_store.save(self.config)

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_visibility()


class QDesktopServicesWrapper:
    @staticmethod
    def open_path(path: str) -> None:
        if sys.platform.startswith("win"):
            from os import startfile

            startfile(path)  # type: ignore[attr-defined]


def create_window() -> FloatingDipWindow:
    return FloatingDipWindow(ConfigStore())


def _parse_optional_float(value: str) -> Optional[float]:
    text = (value or "").strip()
    if not text:
        return None
    return float(text)


def _parse_opacity_percent(value: str) -> float:
    percent = int((value or "").strip())
    if percent < 35 or percent > 100:
        raise ValueError("invalid opacity")
    return percent / 100.0


def _format_number(value: float) -> str:
    return ("%.4f" % value).rstrip("0").rstrip(".")


def _format_point_value(value: Optional[float]) -> str:
    if value is None:
        return "未设置"
    return _format_number(value)


def _format_currency(value: Optional[float]) -> str:
    if value is None:
        return "未设置点值"
    return "%.2f" % value
