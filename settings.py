import concurrent.futures
import json
import os
import uuid
from typing import List, Optional

from PyQt6 import QtCore, QtWidgets

import utils

_CANON_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)


class SettingsWindow(QtWidgets.QWidget):
    settings_saved = QtCore.pyqtSignal(list)
    canonicalized = QtCore.pyqtSignal(str, str, object)
    MAX_CITIES = 9
    MIN_CITIES = 1

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Settings")
        self.setMinimumSize(420, 320)

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
        self.remove_button = QtWidgets.QPushButton("Remove Selected", self)
        self.save_button = QtWidgets.QPushButton("Save", self)
        self.close_button = QtWidgets.QPushButton("Close", self)
        self.status_label = QtWidgets.QLabel("", self)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        main_layout.addWidget(
            QtWidgets.QLabel(f"Cities ({self.MIN_CITIES} - {self.MAX_CITIES}):", self)
        )
        main_layout.addWidget(self.list_widget, stretch=3)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.input_edit)
        row.addWidget(self.add_button)
        main_layout.addLayout(row)

        main_layout.addWidget(self.remove_button)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.close_button)
        main_layout.addLayout(buttons)
        main_layout.addWidget(self.status_label)

        self.add_button.clicked.connect(self._on_add)
        self.input_edit.returnPressed.connect(self._on_add)
        self.remove_button.clicked.connect(self._on_remove)
        self.save_button.clicked.connect(self._on_save)
        self.close_button.clicked.connect(self.hide)
        self.canonicalized.connect(self._on_canonicalized)

        self._load_cities_into_list()

    def _load_cities_into_list(self) -> None:
        self.list_widget.clear()
        cities = utils.load_cities()[: self.MAX_CITIES]
        for city in cities:
            item = QtWidgets.QListWidgetItem(city)
            item.setFlags(
                item.flags()
                | QtCore.Qt.ItemFlag.ItemIsEditable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsDragEnabled
            )
            self.list_widget.addItem(item)

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
            txt = item.text()
            if txt and txt.strip().lower() == cand:
                return True
        return False

    def _on_add(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            self.status_label.setText("Enter a city name")
            return
        if self.list_widget.count() >= self.MAX_CITIES:
            QtWidgets.QMessageBox.warning(
                self, "Limit reached", f"Maximum of {self.MAX_CITIES} cities allowed."
            )
            return
        placeholder = text.title()
        if self._exists_case_insensitive(placeholder):
            self.status_label.setText("City already in the list")
            return
        token = str(uuid.uuid4())
        item = QtWidgets.QListWidgetItem(f"{placeholder} (adding...)")
        item.setData(QtCore.Qt.ItemDataRole.UserRole, token)
        item.setFlags(
            item.flags()
            | QtCore.Qt.ItemFlag.ItemIsEditable
            | QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsDragEnabled
        )
        self.list_widget.addItem(item)
        self.input_edit.clear()
        self.status_label.setText("")
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
                return
            item.setText(canonical)
            try:
                item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, tz)
            except Exception:
                pass
            self.status_label.setText("")
            return

    def _on_remove(self) -> None:
        selected = self.list_widget.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.information(
                self, "Remove", "Select an item to remove."
            )
            return
        if self.list_widget.count() - len(selected) < self.MIN_CITIES:
            QtWidgets.QMessageBox.warning(
                self,
                "Minimum required",
                f"At least {self.MIN_CITIES} city must remain.",
            )
            return
        for it in selected:
            row = self.list_widget.row(it)
            self.list_widget.takeItem(row)
        self.status_label.setText("")

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
            txt = item.text()
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
