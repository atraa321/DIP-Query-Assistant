from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List, Optional

from .config_store import AppConfig, ConfigStore
from .metadata import APP_NAME
from .paths import APP_ICON_PATH, DEFAULT_DB_PATH, SOURCE_DIR
from .query_service import DipQueryService, QueryResult

# ---------------------------------------------------------------------------
#  Treatment mode code → Chinese name mapping
# ---------------------------------------------------------------------------

_TREATMENT_MODE_MAP = {
    "SS": "手术",
    "ZLXCZ": "治疗性操作",
    "ZDXCZ": "诊断性操作",
    "BSZL": "保守治疗",
}

# Regex pattern: match treatment codes that appear as standalone suffix after "/" or ":"
import re as _re
_TREATMENT_CODE_RE = _re.compile(
    r"[/:\s](?:%s)\b" % "|".join(_TREATMENT_MODE_MAP.keys())
)

try:
    from PySide2.QtCore import QPoint, Qt
    from PySide2.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
    from PySide2.QtWidgets import (
        QAction,
        QApplication,
        QCheckBox,
        QDesktopWidget,
        QDialog,
        QFrame,
        QGraphicsDropShadowEffect,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QSizePolicy,
        QSystemTrayIcon,
        QTableWidget,
        QTableWidgetItem,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("运行桌面程序前请先安装 PySide2。") from exc


# ---------------------------------------------------------------------------
#  Global stylesheet — token-driven, compact, modern
# ---------------------------------------------------------------------------

_GLOBAL_STYLE = """
/* ── Shell container ── */
QFrame#Shell {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}

/* ── Title bar ── */
QFrame#TitleBar {
    background: #f8fafc;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border-bottom: 1px solid #edf2f7;
}

QLabel#AppTitle {
    font-size: 13px;
    font-weight: bold;
    color: #4a5568;
    padding-left: 2px;
}

/* ── Search input ── */
QLineEdit#SearchInput {
    padding: 7px 12px;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    background: #f7fafc;
    font-size: 14px;
    min-height: 16px;
    color: #1a202c;
    selection-background-color: #bee3f8;
}
QLineEdit#SearchInput:focus {
    border-color: #63b3ed;
    background: #ffffff;
}
QLineEdit#SearchInput::placeholder {
    color: #a0aec0;
}

/* ── Buttons ── */
QPushButton#SearchBtn {
    padding: 6px 18px;
    border: none;
    border-radius: 8px;
    background: #3182ce;
    color: white;
    font-size: 13px;
    font-weight: bold;
    min-height: 22px;
}
QPushButton#SearchBtn:hover {
    background: #2b6cb0;
}
QPushButton#SearchBtn:pressed {
    background: #2c5282;
}

QToolButton#TitleBtn {
    border: none;
    border-radius: 6px;
    background: transparent;
    font-size: 14px;
    color: #718096;
    padding: 3px 7px;
    min-width: 24px;
    min-height: 22px;
}
QToolButton#TitleBtn:hover {
    background: #edf2f7;
    color: #2d3748;
}

/* ── Result area ── */
QFrame#ResultArea {
    background: transparent;
}

/* DIP code — big & bold */
QLabel#CodeDisplay {
    font-size: 16px;
    font-weight: bold;
    color: #2b6cb0;
}

/* Disease name — secondary */
QLabel#NameDisplay {
    font-size: 13px;
    color: #2d3748;
}

/* Amount row */
QFrame#AmountRow {
    background: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

QLabel#AmountLabel {
    font-size: 11px;
    color: #718096;
}
QLabel#AmountValue {
    font-size: 15px;
    font-weight: bold;
    color: #2b6cb0;
}
QLabel#AmountValue[resident=true] {
    color: #2f855a;
}
QLabel#AmountValue[employee=true] {
    color: #9b2c2c;
}

/* Meta tags (score, match type, group type) */
QLabel#MetaTag {
    font-size: 11px;
    color: #4a5568;
    background: #edf2f7;
    border-radius: 4px;
    padding: 2px 7px;
}

/* Message / hint */
QLabel#HintLabel {
    font-size: 11px;
    color: #a0aec0;
}

/* ── Candidate table ── */
QFrame#CandidateArea {
    background: transparent;
}

QLabel#CandidateLabel {
    font-size: 11px;
    color: #718096;
}

QTableWidget#CandidateTable {
    background: transparent;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 12px;
    gridline-color: #edf2f7;
}
QTableWidget#CandidateTable::item {
    padding: 3px 6px;
    color: #2d3748;
}
QTableWidget#CandidateTable::item:selected {
    background: #bee3f8;
    color: #1a365d;
}
QHeaderView::section {
    background: #f7fafc;
    padding: 4px 6px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-size: 11px;
    font-weight: bold;
    color: #718096;
}

/* ── Status footer ── */
QLabel#StatusText {
    font-size: 10px;
    color: #a0aec0;
}

/* ── Settings dialog ── */
QDialog#SettingsDlg {
    background: #ffffff;
}
QDialog#SettingsDlg QLineEdit {
    padding: 6px 10px;
    border: 1.5px solid #e2e8f0;
    border-radius: 6px;
    background: #f7fafc;
    font-size: 13px;
    min-height: 16px;
}
QDialog#SettingsDlg QLineEdit:focus {
    border-color: #63b3ed;
    background: #ffffff;
}
QDialog#SettingsDlg QLabel#FormLabel {
    font-size: 12px;
    color: #4a5568;
    font-weight: bold;
}
QDialog#SettingsDlg QPushButton#DialogCancel {
    padding: 6px 20px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background: #ffffff;
    color: #4a5568;
    font-size: 12px;
}
QDialog#SettingsDlg QPushButton#DialogCancel:hover {
    background: #f7fafc;
}
QDialog#SettingsDlg QPushButton#DialogSave {
    padding: 6px 20px;
    border: none;
    border-radius: 6px;
    background: #3182ce;
    color: white;
    font-size: 12px;
    font-weight: bold;
}
QDialog#SettingsDlg QPushButton#DialogSave:hover {
    background: #2b6cb0;
}
"""


# ---------------------------------------------------------------------------
#  Settings Dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    def __init__(
        self,
        config: AppConfig,
        on_save: Callable[[Optional[float], Optional[float], float, bool], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super(SettingsDialog, self).__init__(parent)
        self._on_save = on_save
        self.setObjectName("SettingsDlg")
        self.setWindowTitle("后台设置")
        self.setModal(True)
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # ── Point values section ──
        pv_label = QLabel("医保点值")
        pv_label.setObjectName("FormLabel")
        layout.addWidget(pv_label)

        pv_row = QHBoxLayout()
        pv_row.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)
        r_label = QLabel("居民")
        r_label.setObjectName("FormLabel")
        self.resident_input = QLineEdit(
            "" if config.resident_point_value is None else str(config.resident_point_value)
        )
        self.resident_input.setPlaceholderText("例: 4.12")
        left_col.addWidget(r_label)
        left_col.addWidget(self.resident_input)

        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        e_label = QLabel("职工")
        e_label.setObjectName("FormLabel")
        self.employee_input = QLineEdit(
            "" if config.employee_point_value is None else str(config.employee_point_value)
        )
        self.employee_input.setPlaceholderText("例: 4.89")
        right_col.addWidget(e_label)
        right_col.addWidget(self.employee_input)

        pv_row.addLayout(left_col)
        pv_row.addLayout(right_col)
        layout.addLayout(pv_row)

        # ── Window section ──
        win_label = QLabel("窗口")
        win_label.setObjectName("FormLabel")
        layout.addWidget(win_label)

        win_row = QHBoxLayout()
        win_row.setSpacing(10)

        opa_col = QVBoxLayout()
        opa_col.setSpacing(4)
        opa_lbl = QLabel("空闲透明度(%)")
        opa_lbl.setObjectName("FormLabel")
        self.opacity_input = QLineEdit(str(int(config.idle_opacity * 100)))
        opa_col.addWidget(opa_lbl)
        opa_col.addWidget(self.opacity_input)

        top_col = QVBoxLayout()
        top_col.setSpacing(4)
        top_placeholder = QLabel("")  # align with the label above
        top_placeholder.setFixedHeight(opa_lbl.sizeHint().height())
        self.always_on_top_checkbox = QCheckBox("前台置顶")
        self.always_on_top_checkbox.setChecked(config.always_on_top)
        top_col.addWidget(top_placeholder)
        top_col.addWidget(self.always_on_top_checkbox)

        win_row.addLayout(opa_col)
        win_row.addLayout(top_col)
        layout.addLayout(win_row)

        # ── Hint ──
        hint = QLabel("透明度建议 60~85。金额 = 分值 × 点值试算。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #a0aec0; font-size: 10px;")
        layout.addWidget(hint)

        # ── Buttons ──
        layout.addSpacing(4)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("DialogCancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("DialogSave")
        save_btn.clicked.connect(self._save)
        buttons.addWidget(cancel_btn)
        buttons.addSpacing(8)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    def _save(self) -> None:
        try:
            resident_value = _parse_optional_float(self.resident_input.text())
            employee_value = _parse_optional_float(self.employee_input.text())
            opacity = _parse_opacity_percent(self.opacity_input.text())
        except ValueError:
            QMessageBox.warning(self, "设置错误", "请填写有效数字。透明度请输入 35~100 之间的整数。")
            return

        self._on_save(
            resident_value,
            employee_value,
            opacity,
            self.always_on_top_checkbox.isChecked(),
        )
        self.accept()


# ---------------------------------------------------------------------------
#  Main Floating Window
# ---------------------------------------------------------------------------

class FloatingDipWindow(QMainWindow):
    def __init__(self, config_store: ConfigStore) -> None:
        super(FloatingDipWindow, self).__init__()
        self.config_store = config_store
        self.config = config_store.load()
        self.query_service = DipQueryService(Path(self.config.database_path or str(DEFAULT_DB_PATH)))
        self.drag_offset = None  # type: Optional[QPoint]
        self.last_results = []  # type: List[QueryResult]
        self.primary_result = None  # type: Optional[QueryResult]

        self.setWindowTitle(APP_NAME)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self._apply_window_mode(initial=True)
        self.resize(self.config.window_width, self.config.window_height)
        self.move(self.config.window_x, self.config.window_y)
        self.setMinimumSize(420, 340)

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

    # ── UI Construction ──

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(0)

        shell = QFrame()
        shell.setObjectName("Shell")
        shell.setStyleSheet(_GLOBAL_STYLE)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # ── 1. Title bar (compact) ──
        title_bar = QFrame()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(32)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(10, 0, 6, 0)
        tb_layout.setSpacing(0)

        app_title = QLabel("DIP 查询")
        app_title.setObjectName("AppTitle")
        tb_layout.addWidget(app_title)
        tb_layout.addStretch(1)

        self.layer_button = QToolButton()
        self.layer_button.setObjectName("TitleBtn")
        self.layer_button.clicked.connect(self.toggle_always_on_top)
        self.clear_button = QToolButton()
        self.clear_button.setObjectName("TitleBtn")
        self.clear_button.setText("✕")
        self.clear_button.setToolTip("清空结果")
        self.clear_button.clicked.connect(self.clear_results)
        self.minimize_button = QToolButton()
        self.minimize_button.setObjectName("TitleBtn")
        self.minimize_button.setText("—")
        self.minimize_button.setToolTip("最小化到托盘")
        self.minimize_button.clicked.connect(self.hide_to_tray)
        self.close_button = QToolButton()
        self.close_button.setObjectName("TitleBtn")
        self.close_button.setText("×")
        self.close_button.setToolTip("隐藏到托盘")
        self.close_button.clicked.connect(self.hide_to_tray)

        tb_layout.addWidget(self.layer_button)
        tb_layout.addSpacing(2)
        tb_layout.addWidget(self.clear_button)
        tb_layout.addSpacing(2)
        tb_layout.addWidget(self.minimize_button)
        tb_layout.addSpacing(2)
        tb_layout.addWidget(self.close_button)

        shell_layout.addWidget(title_bar)

        # ── 2. Search bar ──
        search_row = QHBoxLayout()
        search_row.setContentsMargins(8, 8, 8, 4)
        search_row.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("输入 DIP 编码或病种名称…")
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_button = QPushButton("查询")
        self.search_button.setObjectName("SearchBtn")
        self.search_button.clicked.connect(self.perform_search)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_button)
        shell_layout.addLayout(search_row)

        # ── 3. Result display ──
        self.result_area = QFrame()
        self.result_area.setObjectName("ResultArea")
        ra_layout = QVBoxLayout(self.result_area)
        ra_layout.setContentsMargins(10, 4, 10, 4)
        ra_layout.setSpacing(4)

        # Code + Name (single line each, no separate label)
        self.code_display = QLabel("—")
        self.code_display.setObjectName("CodeDisplay")
        ra_layout.addWidget(self.code_display)

        self.name_display = QLabel("输入编码或名称开始查询")
        self.name_display.setObjectName("NameDisplay")
        self.name_display.setWordWrap(True)
        ra_layout.addWidget(self.name_display)

        # Amount row — two columns in one frame
        self.amount_row = QFrame()
        self.amount_row.setObjectName("AmountRow")
        ar_layout = QHBoxLayout(self.amount_row)
        ar_layout.setContentsMargins(8, 5, 8, 5)
        ar_layout.setSpacing(0)

        # Resident column
        res_col = QVBoxLayout()
        res_col.setSpacing(1)
        self.res_amount_label = QLabel("居民医保")
        self.res_amount_label.setObjectName("AmountLabel")
        self.res_amount_value = QLabel("—")
        self.res_amount_value.setObjectName("AmountValue")
        self.res_amount_value.setProperty("resident", True)
        res_col.addWidget(self.res_amount_label)
        res_col.addWidget(self.res_amount_value)

        # Employee column
        emp_col = QVBoxLayout()
        emp_col.setSpacing(1)
        self.emp_amount_label = QLabel("职工医保")
        self.emp_amount_label.setObjectName("AmountLabel")
        self.emp_amount_value = QLabel("—")
        self.emp_amount_value.setObjectName("AmountValue")
        self.emp_amount_value.setProperty("employee", True)
        emp_col.addWidget(self.emp_amount_label)
        emp_col.addWidget(self.emp_amount_value)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color: #e2e8f0;")

        ar_layout.addLayout(res_col, 1)
        ar_layout.addWidget(divider)
        ar_layout.addLayout(emp_col, 1)
        ra_layout.addWidget(self.amount_row)

        # Meta tags row (score + match type + group type)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        self.score_tag = QLabel("分值 —")
        self.score_tag.setObjectName("MetaTag")
        self.group_tag = QLabel("")
        self.group_tag.setObjectName("MetaTag")
        self.match_tag = QLabel("")
        self.match_tag.setObjectName("MetaTag")
        meta_row.addWidget(self.score_tag)
        meta_row.addWidget(self.group_tag)
        meta_row.addWidget(self.match_tag)
        meta_row.addStretch(1)
        ra_layout.addLayout(meta_row)

        # Hint label (replaces message_label)
        self.hint_label = QLabel("按回车查询")
        self.hint_label.setObjectName("HintLabel")
        ra_layout.addWidget(self.hint_label)

        shell_layout.addWidget(self.result_area)

        # ── 4. Candidate list ──
        self.candidate_area = QFrame()
        self.candidate_area.setObjectName("CandidateArea")
        ca_layout = QVBoxLayout(self.candidate_area)
        ca_layout.setContentsMargins(8, 0, 8, 4)
        ca_layout.setSpacing(3)

        self.candidate_label = QLabel("")
        self.candidate_label.setObjectName("CandidateLabel")
        ca_layout.addWidget(self.candidate_label)

        self.candidate_table = QTableWidget(0, 3)
        self.candidate_table.setObjectName("CandidateTable")
        self.candidate_table.setHorizontalHeaderLabels(["编码", "病种名称", "分值"])
        self.candidate_table.verticalHeader().setVisible(False)
        self.candidate_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.candidate_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.candidate_table.setSelectionMode(QTableWidget.SingleSelection)
        self.candidate_table.setMinimumHeight(180)
        self.candidate_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.candidate_table.horizontalHeader().setStretchLastSection(False)
        self.candidate_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.candidate_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.candidate_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.candidate_table.cellClicked.connect(self.select_candidate_row)
        ca_layout.addWidget(self.candidate_table)

        self.candidate_area.hide()
        shell_layout.addWidget(self.candidate_area)

        # ── 5. Status footer (single line) ──
        status_row = QHBoxLayout()
        status_row.setContentsMargins(10, 2, 10, 5)
        status_row.setSpacing(8)
        self.resident_status = QLabel("")
        self.resident_status.setObjectName("StatusText")
        self.employee_status = QLabel("")
        self.employee_status.setObjectName("StatusText")
        self.mode_status = QLabel("")
        self.mode_status.setObjectName("StatusText")
        status_row.addWidget(self.resident_status)
        status_row.addWidget(self.employee_status)
        status_row.addStretch(1)
        status_row.addWidget(self.mode_status)
        shell_layout.addLayout(status_row)

        root.addWidget(shell)

    # ── Tray icon ──

    def _init_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self._build_tray_icon(), self)
        self.tray_icon.setToolTip(APP_NAME)
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
        painter.setBrush(QColor("#3182ce"))
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

    # ── Status refresh ──

    def _refresh_status(self) -> None:
        r_pv = _format_point_value(self.config.resident_point_value)
        e_pv = _format_point_value(self.config.employee_point_value)
        self.resident_status.setText("居民 %s" % r_pv)
        self.employee_status.setText("职工 %s" % e_pv)
        mode_text = "置顶" if self.config.always_on_top else "普通"
        self.mode_status.setText("%s · 透明度%s%%" % (mode_text, int(self.config.idle_opacity * 100)))
        self.layer_button.setText("↓" if self.config.always_on_top else "↑")
        self.layer_button.setToolTip("切换为底层" if self.config.always_on_top else "切换为置顶")
        self.layer_action.setText("切换为底层显示" if self.config.always_on_top else "切换为前台显示")

    # ── Search ──

    def perform_search(self) -> None:
        keyword = self.search_input.text().strip()
        if not keyword:
            self._set_hint("请输入编码或关键词")
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
            self._set_hint("查询失败：%s" % exc)
            return

        if not results:
            self.clear_results(keep_keyword=True)
            self._set_hint("未找到匹配的 DIP 病组")
            return

        self.last_results = results
        self._show_primary_result(results[0])
        self._populate_candidates(results)
        self._set_hint("找到 %d 条结果" % len(results))

    def _show_primary_result(self, result: QueryResult) -> None:
        self.primary_result = result
        self.code_display.setText(result.code)
        self.name_display.setText(_format_display_name(result.name, result.code))

        self.res_amount_value.setText(_format_currency(result.resident_estimated_amount))
        self.emp_amount_value.setText(_format_currency(result.employee_estimated_amount))

        self.score_tag.setText("分值 %s" % _format_number(result.score_value))
        self.group_tag.setText(result.group_type)
        match_text = "精确" if result.match_type == "exact_code" else (
            "前缀" if result.match_type == "code_prefix" else "模糊"
        )
        self.match_tag.setText(match_text)

    def _populate_candidates(self, results: List[QueryResult]) -> None:
        if len(results) <= 1:
            self.candidate_area.hide()
            self.candidate_table.setRowCount(0)
            return

        self.candidate_area.show()
        self.candidate_table.setRowCount(len(results))
        self.candidate_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        for row_index, result in enumerate(results):
            values = [result.code, _format_display_name(result.name, result.code), _format_number(result.score_value)]
            for column_index, value in enumerate(values):
                self.candidate_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.candidate_table.selectRow(0)
        self.candidate_label.setText("候选 (%d)" % len(results))
        self.candidate_table.resizeRowsToContents()

    def select_candidate_row(self, row: int, _column: int) -> None:
        if 0 <= row < len(self.last_results):
            self._show_primary_result(self.last_results[row])

    def clear_results(self, keep_keyword: bool = False) -> None:
        self.last_results = []
        self.primary_result = None
        self.code_display.setText("—")
        self.name_display.setText("输入编码或名称开始查询")
        self.res_amount_value.setText("—")
        self.emp_amount_value.setText("—")
        self.score_tag.setText("分值 —")
        self.group_tag.setText("")
        self.match_tag.setText("")
        self.candidate_table.setRowCount(0)
        self.candidate_area.hide()
        if not keep_keyword:
            self.search_input.clear()
        self._set_hint("按回车查询")

    def _set_hint(self, text: str) -> None:
        self.hint_label.setText(text)

    # ── Settings ──

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
        self._set_hint("重建完成，%d 条记录" % count)

    # ── Window management ──

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
        margin = 8
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


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

class QDesktopServicesWrapper:
    @staticmethod
    def open_path(path: str) -> None:
        if sys.platform.startswith("win"):
            from os import startfile

            startfile(path)  # type: ignore[attr-defined]


def create_window() -> FloatingDipWindow:
    return FloatingDipWindow(ConfigStore())


def _format_display_name(raw_name: str, raw_code: str) -> str:
    """For comprehensive diseases, append translated treatment mode from code."""
    text = raw_name or ""

    # Extract treatment code suffix from DIP code (e.g. "I63:ZLXCZ" → "ZLXCZ")
    if ":" in raw_code and len(raw_code.split(":")) >= 2:
        code_suffix = raw_code.split(":")[-1].strip()
        cn_name = _TREATMENT_MODE_MAP.get(code_suffix)
        if cn_name:
            return "%s / %s" % (text.strip(), cn_name)

    # Fallback: replace any standalone treatment codes found in name text
    result = _re.sub(
        r"([A-Z]{2,5})\b",
        lambda m: _TREATMENT_MODE_MAP.get(m.group(1), m.group(1)),
        text,
    )
    return result


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
        return "未设"
    return _format_number(value)


def _format_currency(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "¥%.2f" % value
