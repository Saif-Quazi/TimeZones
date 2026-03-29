import os
import sys
import uuid
from datetime import datetime
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

import utils
from settings import SettingsWindow

unknownCityDisplay = "Invalid/Unknown City"


class SmallClock(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.time = None
        self.setFixedSize(40, 40)

    def setTime(self, t):
        self.time = t
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(4, 4, -4, -4)
        p.setPen(QtGui.QPen(QtGui.QColor("#bbb"), 1.2))
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawEllipse(r)
        if self.time is not None:
            c = r.center()
            cx, cy = float(c.x()), float(c.y())
            radius = r.width() // 2
            hour = (self.time.hour % 12) + (self.time.minute / 60.0)
            angleDeg = (hour / 12.0) * 360.0 - 90
            import math

            hw = 1.2
            p.setPen(
                QtGui.QPen(QtGui.QColor("#fff"), hw, cap=QtCore.Qt.PenCapStyle.RoundCap)
            )
            rad = math.radians(angleDeg)
            p.drawLine(
                QtCore.QPointF(cx, cy),
                QtCore.QPointF(
                    cx + 0.3 * radius * math.cos(rad), cy + 0.3 * radius * math.sin(rad)
                ),
            )
            minute = self.time.minute
            minuteDeg = (minute / 60.0) * 360.0 - 90
            minuteRad = math.radians(minuteDeg)
            p.setPen(
                QtGui.QPen(QtGui.QColor("#fff"), hw, cap=QtCore.Qt.PenCapStyle.RoundCap)
            )
            p.drawLine(
                QtCore.QPointF(cx, cy),
                QtCore.QPointF(
                    cx + 0.6 * radius * math.cos(minuteRad),
                    cy + 0.6 * radius * math.sin(minuteRad),
                ),
            )
        p.end()


class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.id = str(uuid.uuid4())
        self.gen = 0
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.entries = utils.loadCityEntries()[:9]
        self.cities: List[str] = [
            e.get("label") or e.get("city") or "" for e in self.entries
        ]
        self.timezones: List[Optional[str]] = [e.get("tz") for e in self.entries]

        self.clocks: List[SmallClock] = []
        self.cityLabels: List[QtWidgets.QLabel] = []
        self.timeLabels: List[QtWidgets.QLabel] = []
        cols, rows = self.bestGrid(len(self.cities))
        itemWidth, itemHeight = 100, 100
        width = max(120, cols * itemWidth + 16)
        height = max(100, rows * itemHeight + 16)
        self.setFixedSize(width, height)
        try:
            utils.moveToTopRight(self, margin=10)
        except Exception:
            pass
        self.bg = QtWidgets.QWidget(self)
        self.bg.setGeometry(0, 0, width, height)
        self.bg.setStyleSheet(
            "background: rgba(35, 39, 46, 0.85); border-radius: 16px;"
        )
        self.grid = QtWidgets.QGridLayout(self.bg)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setSpacing(4)
        self.rebuildGrid()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.sync)
        self.timer.setInterval(1000)
        self.timer.start()
        utils.emitter.sig.connect(self.onResult)
        for label in self.timeLabels:
            label.setText("--:--")
        self.sync()

    @staticmethod
    def bestGrid(n: int):
        if n <= 1:
            return 1, 1
        import math

        cols = max(1, math.ceil(math.sqrt(n)))
        rows = (n + cols - 1) // cols
        if n <= 3:
            return n, 1
        return cols, rows

    def clearGrid(self):
        if not hasattr(self, "grid") or self.grid is None:
            return
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                try:
                    widget.setParent(None)
                    widget.deleteLater()
                except Exception:
                    pass
                continue
            subLayout = item.layout()
            if subLayout is not None:
                while subLayout.count():
                    subItem = subLayout.takeAt(0)
                    if subItem is None:
                        continue
                    subWidget = subItem.widget()
                    if subWidget is not None:
                        try:
                            subWidget.setParent(None)
                            subWidget.deleteLater()
                        except Exception:
                            pass
                        continue
                    nestedLayout = subItem.layout()
                    if nestedLayout is not None:
                        while nestedLayout.count():
                            nestedItem = nestedLayout.takeAt(0)
                            if nestedItem is None:
                                continue
                            nestedWidget = nestedItem.widget()
                            if nestedWidget is not None:
                                try:
                                    nestedWidget.setParent(None)
                                    nestedWidget.deleteLater()
                                except Exception:
                                    pass

    def rebuildGrid(self):
        self.clocks = []
        self.cityLabels = []
        self.timeLabels = []

        try:
            self.clearGrid()
        except Exception:
            pass

        self.entries = utils.loadCityEntries()[:9]
        self.cities = [e.get("label") or e.get("city") or "" for e in self.entries]
        self.timezones = [e.get("tz") for e in self.entries]
        cols, rows = self.bestGrid(len(self.cities))
        itemWidth, itemHeight = 100, 100
        width = max(120, cols * itemWidth + 16)
        height = max(100, rows * itemHeight + 16)
        try:
            try:
                previousGeometry = self.geometry()
            except Exception:
                previousGeometry = None
            if previousGeometry is None:
                oldWidget = globals().get("_APP_MAIN_WIDGET")
                if oldWidget is not None and oldWidget is not self:
                    try:
                        previousGeometry = oldWidget.geometry()
                    except Exception:
                        previousGeometry = None
        except Exception:
            previousGeometry = None
        try:
            self.setFixedSize(width, height)
        except Exception:
            pass
        try:
            if previousGeometry is not None:
                try:
                    screen = QtWidgets.QApplication.primaryScreen()
                    availableGeometry = (
                        screen.availableGeometry()
                        if screen is not None
                        else QtCore.QRect(0, 0, 800, 600)
                    )
                    desiredX = previousGeometry.x() + previousGeometry.width() - width
                    minX = availableGeometry.x()
                    maxX = availableGeometry.x() + availableGeometry.width() - width
                    desiredX = max(minX, min(desiredX, maxX))
                    desiredY = max(
                        availableGeometry.y(),
                        min(
                            previousGeometry.y(),
                            availableGeometry.y() + availableGeometry.height() - height,
                        ),
                    )
                    self.setGeometry(desiredX, desiredY, width, height)
                    try:
                        self.bg.setGeometry(0, 0, width, height)
                    except Exception:
                        pass
                except Exception:
                    try:
                        self.bg.setGeometry(0, 0, width, height)
                        utils.moveToTopRight(self, margin=10)
                    except Exception:
                        pass
            else:
                try:
                    self.bg.setGeometry(0, 0, width, height)
                except Exception:
                    pass
                utils.moveToTopRight(self, margin=10)
        except Exception:
            try:
                self.bg.setGeometry(0, 0, width, height)
            except Exception:
                pass

        for i, city in enumerate(self.cities):
            row = i // cols
            col = i % cols
            columnLayout = QtWidgets.QVBoxLayout()
            columnLayout.setSpacing(0)
            clock = SmallClock(self.bg)
            columnLayout.addWidget(clock, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            labelsLayout = QtWidgets.QVBoxLayout()
            labelsLayout.setSpacing(2)
            cityLabel = QtWidgets.QLabel(city)
            cityLabel.setStyleSheet(
                "font-size: 14px; color: #eee; text-align: center; background: none;"
            )
            cityLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            labelsLayout.addWidget(cityLabel, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            timeLabel = QtWidgets.QLabel("--:--")
            timeLabel.setStyleSheet(
                "font-size: 14px; color: #eee; text-align: center; background: none;"
            )
            timeLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            labelsLayout.addWidget(timeLabel, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            columnLayout.addLayout(labelsLayout)
            self.grid.addLayout(columnLayout, row, col)
            self.clocks.append(clock)
            self.cityLabels.append(cityLabel)
            self.timeLabels.append(timeLabel)

        for label in self.timeLabels:
            label.setText("--:--")

        self.gen += 1

    def sync(self):
        start = datetime.now()
        self.updateWidget()
        elapsed = (datetime.now() - start).total_seconds()
        secondsUntilMinute = 60 - datetime.now().second
        if secondsUntilMinute <= elapsed:
            self.timer.setInterval(1000)
        else:
            self.timer.setInterval(max(100, int((secondsUntilMinute - elapsed) * 1000)))
        try:
            self.timer.timeout.disconnect()
        except Exception:
            pass
        self.timer.timeout.connect(self.onMinuteTick)

    def onMinuteTick(self):
        self.updateWidget()
        try:
            self.timer.setInterval(60000)
        except Exception:
            self.timer.setInterval(1000)

    def updateWidget(self):
        self.entries = utils.loadCityEntries()[:9]
        self.cities = [e.get("label") or e.get("city") or "" for e in self.entries]
        self.timezones = [e.get("tz") for e in self.entries]
        cityCount = len(self.cities)
        if cityCount != len(self.clocks):
            try:
                currentWidget = globals().get("_APP_MAIN_WIDGET")
                if currentWidget is not None and currentWidget is not self:
                    return
            except Exception:
                pass
            try:
                self.timer.stop()
            except Exception:
                pass
            try:
                self.rebuildGrid()
            except Exception:
                pass
            try:
                self.timer.start()
            except Exception:
                pass
            self.fetchAllTimes()
            return
        self.gen += 1
        currentGen = self.gen
        widgetId = self.id
        for i in range(cityCount):
            city = self.cities[i]
            timezone = self.timezones[i] if i < len(self.timezones) else None
            try:
                self.cityLabels[i].setText(city)
            except Exception:
                pass
            try:
                utils.executor.submit(self.worker, i, city, timezone, widgetId, currentGen)
            except Exception:
                pass

    def fetchAllTimes(self):
        self.gen += 1
        currentGen = self.gen
        widgetId = self.id
        cityCount = len(self.cities)
        for i in range(cityCount):
            city = self.cities[i]
            timezone = self.timezones[i] if i < len(self.timezones) else None
            try:
                utils.executor.submit(self.worker, i, city, timezone, widgetId, currentGen)
            except Exception:
                pass

    def worker(
        self, index: int, label: str, timezone: Optional[str], widgetId: str, generation: int
    ):
        display = (label or "").strip() or unknownCityDisplay

        if not timezone:
            utils.emitter.sig.emit(
                index,
                display,
                "--:--",
                None,
                widgetId,
                generation,
            )
            return

        timeString = utils.fetchTime(timezone)
        parsedTime = None
        try:
            dt = datetime.strptime(timeString, "%I:%M %p")
            parsedTime = dt.time()
        except Exception:
            parsedTime = None

        utils.emitter.sig.emit(index, display, timeString, parsedTime, widgetId, generation)

    def onResult(
        self, index: int, display: str, timeString: str, parsedTime, widgetId: str, generation: int
    ):
        if widgetId != self.id:
            return
        if generation != self.gen:
            return
        if index < 0 or index >= len(self.cityLabels):
            return
        try:
            self.cityLabels[index].setText(display)
        except Exception:
            pass
        try:
            self.timeLabels[index].setText(timeString)
        except Exception:
            pass
        try:
            if parsedTime is not None:
                self.clocks[index].setTime(parsedTime)
        except Exception:
            try:
                self.clocks[index].setTime(None)
            except Exception:
                pass


def main():
    # Initialize persistent user data directory on startup
    try:
        utils.initializeUserData()
    except Exception:
        pass
    
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    iconCandidates = utils.getTrayIconCandidates()
    for iconPath in iconCandidates:
        if os.path.exists(iconPath):
            app.setWindowIcon(QtGui.QIcon(iconPath))
            break

    mainWidget = MainWidget()
    try:
        mainWidget.setWindowOpacity(0.0)
    except Exception:
        pass
    utils.moveToTopRight(mainWidget, margin=10)
    mainWidget.show()
    utils.fadeIn(mainWidget, duration=300)
    settingsWindow = SettingsWindow()

    def onSaved(cities: List[str]):
        try:
            currentMainWidget = globals().get("_APP_MAIN_WIDGET")
            if currentMainWidget is not None:
                try:
                    currentMainWidget.updateWidget()
                except Exception:
                    newWidget = MainWidget()
                    utils.replaceMainWidget(newWidget)
            else:
                newWidget = MainWidget()
                utils.replaceMainWidget(newWidget)
            settingsWindow.statusLabel.setText("Saved")
        except Exception:
            pass

    try:
        settingsWindow.settingsSaved.connect(onSaved)
    except Exception:
        pass

    trayIcon = utils.pickTrayIcon()
    tray = QtWidgets.QSystemTrayIcon(trayIcon, parent=app)
    menu = QtWidgets.QMenu()
    actionSettings = QtGui.QAction("Settings", menu)
    actionQuit = QtGui.QAction("Quit", menu)
    menu.addAction(actionSettings)
    menu.addAction(actionQuit)
    actionSettings.triggered.connect(lambda: settingsWindow.show())

    def quitApp():
        try:
            utils.executor.shutdown(wait=False)
        except Exception:
            pass
        try:
            settingsWindow.close()
        except Exception:
            pass
        try:
            appMainWidget = globals().get("_APP_MAIN_WIDGET")
            if appMainWidget is not None:
                appMainWidget.close()
        except Exception:
            pass
        QtWidgets.QApplication.quit()

    actionQuit.triggered.connect(quitApp)
    tray.setContextMenu(menu)
    tray.setToolTip("TimeZones")
    tray.show()
    globals()["_APP_TRAY"] = tray
    globals()["_APP_SETTINGS_WINDOW"] = settingsWindow
    globals()["_APP_MAIN_WIDGET"] = mainWidget
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
