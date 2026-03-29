import json
import os
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

import utils


class SettingsWindow(QtWidgets.QWidget):
    settingsSaved = QtCore.pyqtSignal(list)
    maxCities = 9
    minCities = 1

    suggestLimit = 5
    suggestCutoff = 65

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("settingsWindow")
        self.setWindowTitle("TimeZones | Widget Settings")
        self.setFixedSize(360, 560)

        iconPath = os.path.join(os.path.dirname(__file__), "assets", "timezones.ico")
        if os.path.exists(iconPath):
            self.setWindowIcon(QtGui.QIcon(iconPath))
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

        self.listWidget = QtWidgets.QListWidget(self)
        self.listWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.listWidget.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )

        self.inputEdit = QtWidgets.QLineEdit(self)
        self.inputEdit.setPlaceholderText("Type a city name")
        self.addButton = QtWidgets.QPushButton("Add", self)
        self.saveButton = QtWidgets.QPushButton("Save", self)
        self.closeButton = QtWidgets.QPushButton("Close", self)
        self.statusLabel = QtWidgets.QLabel("", self)
        self.closeButton.setObjectName("closeButton")

        self.suggestions = QtWidgets.QListWidget(self)
        self.suggestions.setObjectName("citySuggestions")
        self.suggestions.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.suggestions.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.suggestions.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.suggestions.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.suggestions.setMouseTracking(True)

        self.suggestions.setStyleSheet(
            """
            QListWidget#citySuggestions {
                background-color: #2d2d2d;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 4px;
            }
            QListWidget#citySuggestions::item {
                padding: 8px;
                border-radius: 8px;
            }
            QListWidget#citySuggestions::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget#citySuggestions::item:selected {
                background-color: #5588e5;
            }
            """
        )
        self.suggestions.hide()

        try:
            self.cityTz = utils.loadCityTimezones()
        except Exception:
            self.cityTz = {}

        self.selectedSuggestionDisplay: Optional[str] = None
        self.selectedSuggestionTz: Optional[str] = None
        self.inputConfirmedValid: bool = False

        self.inputEdit.setFixedHeight(40)
        self.addButton.setFixedSize(78, 32)
        self.saveButton.setFixedSize(78, 32)
        self.closeButton.setFixedSize(78, 32)

        self.inputEdit.textEdited.connect(self.onQueryChanged)
        self.inputEdit.installEventFilter(self)
        self.suggestions.itemClicked.connect(self.onSuggestionClicked)

        try:
            self.syncSuggestionsGeometry()
        except Exception:
            pass

        self.listWidget.setSpacing(4)

        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setContentsMargins(12, 12, 12, 12)
        mainLayout.setSpacing(10)
        mainLayout.addWidget(self.listWidget, stretch=3)

        rowLayout = QtWidgets.QHBoxLayout()
        rowLayout.setContentsMargins(0, 0, 0, 0)
        rowLayout.setSpacing(8)
        rowLayout.addWidget(self.inputEdit)
        rowLayout.addWidget(self.addButton)
        mainLayout.addWidget(self.suggestions)

        mainLayout.addLayout(rowLayout)

        buttonsLayout = QtWidgets.QHBoxLayout()
        buttonsLayout.setContentsMargins(0, 0, 0, 0)
        buttonsLayout.setSpacing(8)
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.closeButton)
        buttonsLayout.addWidget(self.saveButton)
        mainLayout.addLayout(buttonsLayout)
        mainLayout.addWidget(self.statusLabel)

        self.addButton.clicked.connect(self.onAdd)
        self.inputEdit.returnPressed.connect(self.onAdd)
        self.saveButton.clicked.connect(self.onSave)
        self.closeButton.clicked.connect(self.hide)

        self.loadCitiesIntoList()
        self.updateInputState()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.inputEdit and self.suggestions.isVisible():
            if not isinstance(event, QtGui.QKeyEvent):
                return super().eventFilter(watched, event)
            if event.type() == QtCore.QEvent.Type.KeyPress:
                key = event.key()
                if key in (QtCore.Qt.Key.Key_Down, QtCore.Qt.Key.Key_Up):
                    if self.suggestions.count() == 0:
                        return False
                    row = self.suggestions.currentRow()
                    if row < 0:
                        row = 0
                    if key == QtCore.Qt.Key.Key_Down:
                        row = min(self.suggestions.count() - 1, row + 1)
                    else:
                        row = max(0, row - 1)
                    self.suggestions.setCurrentRow(row)
                    return True
                if key in (
                    QtCore.Qt.Key.Key_Return,
                    QtCore.Qt.Key.Key_Enter,
                    QtCore.Qt.Key.Key_Tab,
                ):
                    item = self.suggestions.currentItem()
                    if item is not None:
                        self.applySuggestionItem(item)
                        return True
                if key == QtCore.Qt.Key.Key_Escape:
                    self.hideSuggestions()
                    return True
        return super().eventFilter(watched, event)

    def loadCitiesIntoList(self) -> None:
        self.listWidget.clear()

        try:
            entries = utils.loadCityEntries()[: self.maxCities]
        except Exception:
            entries = []

        if entries:
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                label = entry.get("label") or entry.get("city")
                timezone = entry.get("tz")
                if (
                    isinstance(label, str)
                    and label.strip()
                    and isinstance(timezone, str)
                    and timezone.strip()
                ):
                    self.addCityItem(label.strip(), tz=timezone.strip())
        else:
            cities = utils.loadCities()[: self.maxCities]
            for city in cities:
                self.addCityItem(city)

        self.updateInputState()

    def addCityItem(self, cityText: str, tz: Optional[str] = None) -> None:
        item = QtWidgets.QListWidgetItem(cityText)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, cityText)
        item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, tz)
        item.setFlags(
            item.flags()
            | QtCore.Qt.ItemFlag.ItemIsEnabled
            | QtCore.Qt.ItemFlag.ItemIsSelectable
            | QtCore.Qt.ItemFlag.ItemIsDragEnabled
        )
        self.listWidget.addItem(item)
        rowWidget = self.buildCityRowWidget(item, cityText)
        item.setSizeHint(rowWidget.sizeHint())
        self.listWidget.setItemWidget(item, rowWidget)

    def buildCityRowWidget(
        self, item: QtWidgets.QListWidgetItem, cityText: str
    ) -> QtWidgets.QWidget:
        rowWidget = QtWidgets.QWidget(self.listWidget)
        rowWidget.setObjectName("cityRow")
        rowLayout = QtWidgets.QHBoxLayout(rowWidget)
        rowLayout.setContentsMargins(8, 2, 8, 2)
        rowLayout.setSpacing(8)

        cityLabel = QtWidgets.QLabel(cityText, rowWidget)
        cityLabel.setObjectName("cityLabel")
        cityLabel.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        cityLabel.setWordWrap(False)

        trashButton = QtWidgets.QToolButton(rowWidget)
        trashButton.setObjectName("trashButton")
        trashSvg = os.path.join(os.path.dirname(__file__), "assets", "trash.svg")
        if os.path.exists(trashSvg):
            trashIcon = QtGui.QIcon(trashSvg)
        else:
            style = self.style()
            if style is not None:
                trashIcon = style.standardIcon(
                    QtWidgets.QStyle.StandardPixmap.SP_TrashIcon
                )
            else:
                trashIcon = QtGui.QIcon()
        trashButton.setIcon(trashIcon)
        trashButton.setIconSize(QtCore.QSize(14, 14))
        trashButton.clicked.connect(
            lambda _checked=False, currentItem=item: self.removeItem(currentItem)
        )

        rowLayout.addWidget(cityLabel, 1)
        rowLayout.addWidget(trashButton)
        item.setSizeHint(QtCore.QSize(0, 34))
        return rowWidget

    def getCityText(self, item: QtWidgets.QListWidgetItem) -> str:
        stored = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
        text = item.text()
        return text.strip() if text else ""

    def existsCaseInsensitive(
        self, candidate: str, excludeToken: Optional[str] = None
    ) -> bool:
        normalizedCandidate = candidate.strip().lower()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if not item:
                continue
            token = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if excludeToken is not None and token == excludeToken:
                continue
            text = self.getCityText(item)
            if text and text.strip().lower() == normalizedCandidate:
                return True
        return False

    def updateInputState(self) -> None:
        atMax = self.listWidget.count() >= self.maxCities
        self.inputEdit.setEnabled(not atMax)
        self.addButton.setEnabled(not atMax)
        if atMax:
            self.inputEdit.setPlaceholderText(f"Max {self.maxCities} cities reached")
            self.hideSuggestions()
        else:
            self.inputEdit.setPlaceholderText("Type a city name")

    def hideSuggestions(self) -> None:
        try:
            self.suggestions.hide()
        except Exception:
            pass
        try:
            self.suggestions.clear()
        except Exception:
            pass

    def syncSuggestionsGeometry(self) -> None:
        try:
            width = self.inputEdit.width()
            height = self.inputEdit.height() * 3
            self.suggestions.setFixedWidth(width)
            self.suggestions.setFixedHeight(height)
        except Exception:
            pass

    def onQueryChanged(self, text: str) -> None:
        self.inputConfirmedValid = False
        self.selectedSuggestionDisplay = None
        self.selectedSuggestionTz = None

        if self.listWidget.count() >= self.maxCities:
            self.hideSuggestions()
            return

        query = (text or "").strip()
        if len(query) < 2:
            self.hideSuggestions()
            self.statusLabel.setText("")
            return

        exactKey = query.strip().lower()
        if exactKey in self.cityTz:
            self.inputConfirmedValid = True
            self.selectedSuggestionDisplay = query.strip().title()
            self.selectedSuggestionTz = self.cityTz.get(exactKey)
            self.hideSuggestions()
            self.statusLabel.setText("")
            return

        suggestions = []
        try:
            suggestFn = getattr(utils, "suggestCities", None)
            if suggestFn is not None:
                suggestions = suggestFn(
                    query,
                    self.cityTz,
                    limit=self.suggestLimit,
                    scoreCutoff=self.suggestCutoff,
                )
        except Exception:
            suggestions = []

        geoSuggestions = []
        if not suggestions:
            try:
                geoFn = getattr(utils, "suggestPlacesGeocode", None)
                if geoFn is not None:
                    geoSuggestions = geoFn(query, limit=self.suggestLimit)
            except Exception:
                geoSuggestions = []

        if not suggestions and not geoSuggestions:
            self.hideSuggestions()
            self.statusLabel.setText("Invalid/Unknown City")
            return

        self.statusLabel.setText("Pick a city from suggestions")
        self.suggestions.clear()

        for display, timezone, score in suggestions:
            item = QtWidgets.QListWidgetItem(f"{display}  ({timezone})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, display)
            item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, timezone)
            item.setData(QtCore.Qt.ItemDataRole.UserRole + 2, score)
            self.suggestions.addItem(item)

        for label, timezone, score in geoSuggestions:
            clean = label.split(",")[0].strip() if isinstance(label, str) else ""
            display = clean or (label.strip() if isinstance(label, str) else "")
            item = QtWidgets.QListWidgetItem(f"{display}  ({timezone})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, display)
            item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, timezone)
            item.setData(QtCore.Qt.ItemDataRole.UserRole + 2, score)
            try:
                item.setToolTip(label)
            except Exception:
                pass
            self.suggestions.addItem(item)

        self.suggestions.setCurrentRow(0)
        self.syncSuggestionsGeometry()
        self.suggestions.show()

    def applySuggestionItem(self, item: QtWidgets.QListWidgetItem) -> None:
        display = item.data(QtCore.Qt.ItemDataRole.UserRole)
        timezone = item.data(QtCore.Qt.ItemDataRole.UserRole + 1)

        if isinstance(display, str) and display.strip():
            try:
                self.inputEdit.setText(display.strip())
                self.inputEdit.setFocus()
                self.inputEdit.setCursorPosition(len(self.inputEdit.text()))
            except Exception:
                pass

        self.inputConfirmedValid = True
        self.selectedSuggestionDisplay = (
            display.strip() if isinstance(display, str) else None
        )
        self.selectedSuggestionTz = timezone if isinstance(timezone, str) else None

        self.statusLabel.setText("Valid city")
        self.hideSuggestions()

    def onSuggestionClicked(self, item: QtWidgets.QListWidgetItem) -> None:
        self.applySuggestionItem(item)

    def onAdd(self) -> None:
        if self.suggestions.isVisible() and self.suggestions.count() > 0:
            currentItem = self.suggestions.currentItem()
            if currentItem is not None:
                self.applySuggestionItem(currentItem)

        self.hideSuggestions()

        text = self.inputEdit.text().strip()
        if not text:
            self.statusLabel.setText("Enter a city name")
            return
        if self.listWidget.count() >= self.maxCities:
            return

        exactKey = text.lower()
        exactTimezone = self.cityTz.get(exactKey)
        isExact = exactTimezone is not None

        timezone = exactTimezone
        canonical = text.title()

        if not isExact and not self.inputConfirmedValid:
            geoFn = getattr(utils, "suggestPlacesGeocode", None)
            if geoFn is not None:
                try:
                    geoSuggestions = geoFn(text, limit=1)
                except Exception:
                    geoSuggestions = []
                if geoSuggestions:
                    fullLabel, timezone2, _score = geoSuggestions[0]
                    clean = (
                        fullLabel.split(",")[0].strip()
                        if isinstance(fullLabel, str)
                        else ""
                    )
                    canonical = clean or (str(fullLabel).strip() if fullLabel else canonical)
                    timezone = timezone2
                    self.inputConfirmedValid = True
                    self.selectedSuggestionDisplay = canonical
                    self.selectedSuggestionTz = timezone

        if not isExact and not self.inputConfirmedValid:
            self.statusLabel.setText("Invalid/Unknown City")
            return

        if not isExact and self.selectedSuggestionDisplay:
            canonical = self.selectedSuggestionDisplay
            timezone = self.selectedSuggestionTz

        if self.existsCaseInsensitive(canonical):
            self.statusLabel.setText("City already in the list")
            return

        self.addCityItem(canonical, tz=timezone)
        self.inputEdit.clear()
        self.inputConfirmedValid = False
        self.selectedSuggestionDisplay = None
        self.selectedSuggestionTz = None
        self.statusLabel.setText("Added")
        self.updateInputState()

    def removeItem(self, item: QtWidgets.QListWidgetItem) -> None:
        if self.listWidget.count() - 1 < self.minCities:
            QtWidgets.QMessageBox.warning(
                self,
                "Minimum required",
                f"At least {self.minCities} city must remain.",
            )
            return
        row = self.listWidget.row(item)
        if row >= 0:
            self.listWidget.takeItem(row)
        self.statusLabel.setText("")
        self.updateInputState()

    def onSave(self) -> None:
        count = self.listWidget.count()
        if count < self.minCities:
            QtWidgets.QMessageBox.warning(
                self, "Error", f"At least {self.minCities} city is required."
            )
            return
        if count > self.maxCities:
            QtWidgets.QMessageBox.warning(
                self, "Error", f"No more than {self.maxCities} cities are allowed."
            )
            return

        entries = []
        labelsForSignal: List[str] = []

        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if not item:
                continue

            label = self.getCityText(item)
            timezone = item.data(QtCore.Qt.ItemDataRole.UserRole + 1)

            if not isinstance(label, str) or not label.strip():
                continue
            if not isinstance(timezone, str) or not timezone.strip():
                continue

            entries.append({"label": label.strip(), "tz": timezone.strip()})
            labelsForSignal.append(label.strip())

        if len(entries) < self.minCities:
            QtWidgets.QMessageBox.warning(
                self, "Error", f"At least {self.minCities} valid city is required."
            )
            return

        self.statusLabel.setText("Saving...")
        QtWidgets.QApplication.processEvents()
        try:
            saveFn = getattr(utils, "saveCityEntries", None)
            if saveFn is not None:
                saveFn(entries, os.path.join(os.path.dirname(__file__), "timezones.json"))
            else:
                with open(
                    os.path.join(os.path.dirname(__file__), "timezones.json"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(entries, f, indent=4)

            try:
                QtCore.QTimer.singleShot(
                    0, lambda: self.settingsSaved.emit(labelsForSignal)
                )
            except Exception:
                self.settingsSaved.emit(labelsForSignal)

            self.statusLabel.setText("Saved")
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(error))
            self.statusLabel.setText("Save failed")
