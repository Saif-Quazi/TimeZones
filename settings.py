import concurrent.futures
import json
import os
import uuid
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

import utils

_CANON_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)


class SettingsWindow(QtWidgets.QWidget):
    settings_saved = QtCore.pyqtSignal(list)
    canonicalized = QtCore.pyqtSignal(str, str, object)
    MAX_CITIES = 9
    MIN_CITIES = 1

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("settingsWindow")
        self.setWindowTitle("TimeZones | Widget Settings")
        self.setFixedSize(360, 560)
        
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "timezones.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        self.setStyleSheet(
            """
            #settingsWindow {
                background-color: #222;
                color: white;
                font-size: 15px;
            }
            #settingsWindow QLabel,
            #settingsWindow QLineEdit,
            #settingsWindow QPushButton,
            #settingsWindow QToolButton,
            #settingsWindow QListWidget,
            #settingsWindow QListView,
            #settingsWindow QAbstractItemView {
                background-color: #222;
                color: white;
                border: none;
                outline: 0;
            }
            #settingsWindow QLineEdit::placeholder {
                color: white;
            }
            #settingsWindow QLineEdit {
                background-color: #2d2d2d;
                padding: 6px;
                margin: 4px;
                border-radius: 8px;
            }
            #settingsWindow QListWidget,
            #settingsWindow QPushButton,
            #settingsWindow QToolButton {
                margin: 4px;
            }
            #settingsWindow QListWidget::item { border: none; }
            #settingsWindow QAbstractItemView:focus,
            #settingsWindow QPushButton:focus,
            #settingsWindow QLineEdit:focus {
                border: none;
                outline: 0;
            }
            #settingsWindow QPushButton {
                background-color: #5588e5;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0px;
            }
            #settingsWindow QToolButton#trashButton {
                background-color: #2e2e2e;
                color: white;
                border: none;
                border-radius: 8px;
                min-width: 24px;
                min-height: 24px;
                max-width: 24px;
                max-height: 24px;
            }
            #settingsWindow QToolButton#trashButton:hover {
                background-color: #3a3a3a;
            }
            #settingsWindow QWidget#cityRow {
                background-color: #2e2e2e;
                border-radius: 6px;
            }
            #settingsWindow QLabel#cityLabel {
                background-color: transparent;
                color: white;
                margin: 0px;
                padding: 0px;
            }
            #settingsWindow QPushButton#closeButton {
                background-color: #666;
            }
            #settingsWindow QPushButton:disabled,
            #settingsWindow QLineEdit:disabled,
            #settingsWindow QListWidget:disabled,
            #settingsWindow QLabel:disabled {
                background-color: #333;
                color: #666;
                opacity: 0.5;
            }
            """
        )

        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )

        self.input_edit = QtWidgets.QLineEdit(self)
        self.input_edit.setPlaceholderText("Type a city name")
        self.add_button = QtWidgets.QPushButton("Add", self)
        self.save_button = QtWidgets.QPushButton("Save", self)
        self.close_button = QtWidgets.QPushButton("Close", self)
        self.status_label = QtWidgets.QLabel("", self)
        self.close_button.setObjectName("closeButton")

        self.input_edit.setFixedHeight(40)
        self.add_button.setFixedSize(78, 32)
        self.save_button.setFixedSize(78, 32)
        self.close_button.setFixedSize(78, 32)

        self.list_widget.setSpacing(4)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.list_widget, stretch=3)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self.input_edit)
        row.addWidget(self.add_button)
        main_layout.addLayout(row)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addStretch()
        buttons.addWidget(self.close_button)
        buttons.addWidget(self.save_button)
        main_layout.addLayout(buttons)
        main_layout.addWidget(self.status_label)

        self.add_button.clicked.connect(self._on_add)
        self.input_edit.returnPressed.connect(self._on_add)
        self.save_button.clicked.connect(self._on_save)
        self.close_button.clicked.connect(self.hide)
        self.canonicalized.connect(self._on_canonicalized)

        self._load_cities_into_list()
        self._update_input_state()

    def _load_cities_into_list(self) -> None:
        self.list_widget.clear()
        cities = utils.load_cities()[: self.MAX_CITIES]
        for city in cities:
            self._add_city_item(city)
        self._update_input_state()

    def _add_city_item(self, city_text: str, token: Optional[str] = None, tz=None) -> None:
        item = QtWidgets.QListWidgetItem(city_text)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, token)
        item.setData(QtCore.Qt.ItemDataRole.UserRole + 2, city_text)
        item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, tz)
        item.setFlags(
            item.flags()
            | QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsDragEnabled
        )
        self.list_widget.addItem(item)
        row_widget = self._build_city_row_widget(item, city_text)
        item.setSizeHint(row_widget.sizeHint())
        self.list_widget.setItemWidget(item, row_widget)

    def _build_city_row_widget(
        self, item: QtWidgets.QListWidgetItem, city_text: str
    ) -> QtWidgets.QWidget:
        row_widget = QtWidgets.QWidget(self.list_widget)
        row_widget.setObjectName("cityRow")
        row = QtWidgets.QHBoxLayout(row_widget)
        row.setContentsMargins(8, 2, 8, 2)
        row.setSpacing(8)

        city_label = QtWidgets.QLabel(city_text, row_widget)
        city_label.setObjectName("cityLabel")
        city_label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        city_label.setWordWrap(False)

        trash_button = QtWidgets.QToolButton(row_widget)
        trash_button.setObjectName("trashButton")
        trash_svg = os.path.join(os.path.dirname(__file__), "assets", "trash.svg")
        if os.path.exists(trash_svg):
            trash_icon = QtGui.QIcon(trash_svg)
        else:
            trash_icon = self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_TrashIcon
            )
        trash_button.setIcon(trash_icon)
        trash_button.setIconSize(QtCore.QSize(14, 14))
        trash_button.clicked.connect(lambda _checked=False, i=item: self._remove_item(i))

        row.addWidget(city_label, 1)
        row.addWidget(trash_button)
        item.setSizeHint(QtCore.QSize(0, 34))
        return row_widget

    def _get_city_text(self, item: QtWidgets.QListWidgetItem) -> str:
        stored = item.data(QtCore.Qt.ItemDataRole.UserRole + 2)
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
        txt = item.text()
        return txt.strip() if txt else ""

    def _exists_case_insensitive(
        self, candidate: str, exclude_token: Optional[str] = None
    ) -> bool:
        cand = candidate.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            token = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if exclude_token is not None and token == exclude_token:
                continue
            txt = self._get_city_text(item)
            if txt and txt.strip().lower() == cand:
                return True
        return False

    def _update_input_state(self) -> None:
        """Enable/disable input and add button based on city count."""
        at_max = self.list_widget.count() >= self.MAX_CITIES
        self.input_edit.setEnabled(not at_max)
        self.add_button.setEnabled(not at_max)
        if at_max:
            self.input_edit.setPlaceholderText(f"Max {self.MAX_CITIES} cities reached")
        else:
            self.input_edit.setPlaceholderText("Type a city name")

    def _on_add(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            self.status_label.setText("Enter a city name")
            return
        if self.list_widget.count() >= self.MAX_CITIES:
            return
        placeholder = text.title()
        if self._exists_case_insensitive(placeholder):
            self.status_label.setText("City already in the list")
            return
        token = str(uuid.uuid4())
        self._add_city_item(f"{placeholder} (adding...)", token=token)
        self.input_edit.clear()
        self.status_label.setText("")
        self._update_input_state()
        _CANON_EXECUTOR.submit(self._bg_canonicalize, text, token)

    def _bg_canonicalize(self, text: str, token: str) -> None:
        city_tz = {}
        try:
            city_tz = utils.load_city_timezones()
        except Exception:
            pass
        display, tz = (
            utils.fuzzy_city_lookup(text, city_tz)
            if hasattr(utils, "fuzzy_city_lookup")
            else (text.title(), None)
        )
        self.canonicalized.emit(token, display, tz)

    def _on_canonicalized(self, token: str, canonical: str, tz) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            if item.data(QtCore.Qt.ItemDataRole.UserRole) != token:
                continue
            if self._exists_case_insensitive(canonical, exclude_token=token):
                row = self.list_widget.row(item)
                self.list_widget.takeItem(row)
                self.status_label.setText("City already in the list")
                self._update_input_state()
                return
            item.setText(canonical)
            item.setData(QtCore.Qt.ItemDataRole.UserRole + 2, canonical)
            try:
                item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, tz)
            except Exception:
                pass
            row_widget = self.list_widget.itemWidget(item)
            if row_widget:
                label = row_widget.findChild(QtWidgets.QLabel, "cityLabel")
                if label:
                    label.setText(canonical)
            self.status_label.setText("")
            self._update_input_state()
            return

    def _remove_item(self, item: QtWidgets.QListWidgetItem) -> None:
        if self.list_widget.count() - 1 < self.MIN_CITIES:
            QtWidgets.QMessageBox.warning(
                self,
                "Minimum required",
                f"At least {self.MIN_CITIES} city must remain.",
            )
            return
        row = self.list_widget.row(item)
        if row >= 0:
            self.list_widget.takeItem(row)
        self.status_label.setText("")
        self._update_input_state()

    def _on_save(self) -> None:
        count = self.list_widget.count()
        if count < self.MIN_CITIES:
            QtWidgets.QMessageBox.warning(
                self, "Error", f"At least {self.MIN_CITIES} city is required."
            )
            return
        if count > self.MAX_CITIES:
            QtWidgets.QMessageBox.warning(
                self, "Error", f"No more than {self.MAX_CITIES} cities are allowed."
            )
            return
        cities: List[str] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            txt = self._get_city_text(item)
            if not txt:
                continue
            cities.append(txt)
        self.status_label.setText("Saving...")
        QtWidgets.QApplication.processEvents()
        try:
            with open(
                os.path.join(os.path.dirname(__file__), "timezones.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump([{"city": c} for c in cities], f, indent=4)
            try:
                QtCore.QTimer.singleShot(0, lambda: self.settings_saved.emit(cities))
            except Exception:
                self.settings_saved.emit(cities)
            self.status_label.setText("Saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(e))
            self.status_label.setText("Save failed")
