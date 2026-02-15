import sys
import json
import math
import requests
from datetime import datetime
from PyQt6 import QtWidgets, QtGui, QtCore
from rapidfuzz import process
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder


class SimpleClockWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.time = None
        self.setFixedSize(40, 40)

    def setTime(self, time):
        self.time = time
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.setPen(QtGui.QPen(QtGui.QColor('#bbb'), 1.2))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)
        if self.time:
            c = rect.center()
            center = QtCore.QPointF(float(c.x()), float(c.y()))
            r = rect.width() // 2
            hour = self.time.hour % 12 + self.time.minute / 60.0
            angle = math.radians((hour / 12.0) * 360.0 - 90)
            handWidth = 1.2
            painter.setPen(QtGui.QPen(QtGui.QColor('#fff'), handWidth, cap=QtCore.Qt.PenCapStyle.RoundCap))
            hourEnd = QtCore.QPointF(
                center.x() + 0.3 * r * math.cos(angle),
                center.y() + 0.3 * r * math.sin(angle)
            )
            painter.drawLine(center, hourEnd)
            minute = self.time.minute
            angle = math.radians((minute / 60.0) * 360.0 - 90)
            painter.setPen(QtGui.QPen(QtGui.QColor('#fff'), handWidth, cap=QtCore.Qt.PenCapStyle.RoundCap))
            minEnd = QtCore.QPointF(
                center.x() + 0.6 * r * math.cos(angle),
                center.y() + 0.6 * r * math.sin(angle)
            )
            painter.drawLine(center, minEnd)
        painter.end()


def loadCityTimezones():
    try:
        with open("timezonesDict.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "new york": "America/New_York",
            "london": "Europe/London",
            "tokyo": "Asia/Tokyo"
        }

def loadCities():
    try:
        with open("timezones.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return [entry["city"] for entry in data if "city" in entry]
    except Exception:
        return ["New York", "London", "Tokyo"]

cityTimezone = loadCityTimezones()

def loadCities():
    try:
        with open("timezones.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return [entry["city"] for entry in data if "city" in entry]
    except Exception:
        return ["New York", "London", "Tokyo"]


def makeWidget():
    widget = QtWidgets.QWidget()
    widget.setWindowFlags(
        QtCore.Qt.WindowType.FramelessWindowHint |
        QtCore.Qt.WindowType.Tool
    )
    widget.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
    widget.cities = loadCities()[:9]
    n = len(widget.cities)
    def bestGrid(n):
        if n < 4:
            return n, 1
        for rows in range(2, n+1):
            if n % rows == 0 and rows <= n // rows:
                return n // rows, rows
        cols = (n + 1) // 2
        rows = (n + cols - 1) // cols
        return cols, rows

    cols, rows = bestGrid(n)
    itemWidth = 100
    itemHeight = 100
    width = max(120, cols * itemWidth + 16)
    height = max(100, rows * itemHeight + 16)
    widget.setFixedSize(width, height)
    moveToTopRight(widget, height)
    widget.setWindowOpacity(1.0)

    bgWidget = QtWidgets.QWidget(widget)
    bgWidget.setGeometry(0, 0, width, height)
    bgWidget.setStyleSheet("background: rgba(35, 39, 46, 0.85); border-radius: 16px;")

    grid = QtWidgets.QGridLayout(bgWidget)
    grid.setContentsMargins(8, 8, 8, 8)
    grid.setSpacing(4)
    widget.clockWidgets = []
    widget.cityLabels = []
    widget.timeLabels = []
    for idx, city in enumerate(widget.cities):
        row = idx // cols
        col = idx % cols
        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(0)
        clock = SimpleClockWidget(bgWidget)
        vbox.addWidget(clock, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        labelUnit = QtWidgets.QVBoxLayout()
        labelUnit.setSpacing(2)
        cityLabel = QtWidgets.QLabel(city)
        cityLabel.setStyleSheet("font-size: 14px; color: #eee; text-align: center; background: none;")
        cityLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        labelUnit.addWidget(cityLabel, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        timeLabel = QtWidgets.QLabel("--:--")
        timeLabel.setStyleSheet("font-size: 14px; color: #eee; text-align: center; background: none;")
        timeLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        labelUnit.addWidget(timeLabel, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        vbox.addLayout(labelUnit)
        grid.addLayout(vbox, row, col)
        widget.clockWidgets.append(clock)
        widget.cityLabels.append(cityLabel)
        widget.timeLabels.append(timeLabel)
    widget.timer = QtCore.QTimer(widget)
    def syncUpdate():
        start = datetime.now()
        updateWidget(widget)
        elapsed = (datetime.now() - start).total_seconds()
        now = datetime.now()
        secondsToNextMinute = 60 - now.second
        if secondsToNextMinute <= elapsed:
            widget.timer.setInterval(1000)
        else:
            widget.timer.setInterval(int((secondsToNextMinute - elapsed) * 1000))
        widget.timer.timeout.disconnect()
        widget.timer.timeout.connect(minuteUpdate)
    def minuteUpdate():
        start = datetime.now()
        updateWidget(widget)
        elapsed = (datetime.now() - start).total_seconds()
        widget.timer.setInterval(max(1000, int((60 - elapsed) * 1000)))
    widget.timer.timeout.connect(syncUpdate)
    widget.timer.setInterval(100)
    widget.timer.start()
    syncUpdate()
    return widget


def fuzzyCityLookup(city):
    choices = list(cityTimezone.keys())
    result = process.extractOne(city.strip().lower(), choices, score_cutoff=60)
    if result:
        match, score, _ = result
        return match, cityTimezone[match]
    try:
        geolocator = Nominatim(user_agent="timezoneApp")
        location = geolocator.geocode(city, language="en", addressdetails=False, timeout=10)
        if location:
            tf = TimezoneFinder()
            tz = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            if tz:
                return location.address, tz
    except Exception:
        pass
    return None, None


def updateWidget(widget):
    widget.cities = loadCities()[:9]
    n = len(widget.cities)
    if n != len(widget.clockWidgets):
        parent = widget.clockWidgets[0].parentWidget().parentWidget() if widget.clockWidgets else None
        if parent:
            for i in reversed(range(parent.layout().count())):
                item = parent.layout().itemAt(i)
                if item:
                    parent.layout().removeItem(item)
        newWidget = makeWidget()
        widget.setParent(None)
        newWidget.show()
        return
    for i in range(n):
        city = widget.cities[i]
        match, tz = fuzzyCityLookup(city)
        if tz:
            if "," in match:
                displayName = match.split(",")[0].strip().title()
            else:
                displayName = match.title()
            timeStr = fetchTime(tz)
            try:
                t = datetime.strptime(timeStr, "%I:%M %p")
                widget.clockWidgets[i].setTime(t.time())
            except Exception:
                widget.clockWidgets[i].setTime(None)
        else:
            displayName = city
            timeStr = "--:--"
            widget.clockWidgets[i].setTime(None)
        widget.cityLabels[i].setText(displayName)
        widget.timeLabels[i].setText(timeStr)




def moveToTopRight(widget, height=None):
    screen = QtWidgets.QApplication.primaryScreen().geometry()
    h = height if height else widget.height()
    x = screen.width() - widget.width() - 10
    y = 10
    widget.move(x, y)


def fetchTime(tz):
    try:
        url = f"https://timeapi.io/api/Time/current/zone?timeZone={tz}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            time24 = data.get("time", "--:--")
            try:
                t = datetime.strptime(time24, "%H:%M")
                if sys.platform == "win32":
                    return t.strftime("%#I:%M %p")
                else:
                    return t.strftime("%-I:%M %p")
            except Exception:
                return time24
    except Exception:
        pass
    return "--:--"


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = makeWidget()
    widget.show()
    app.widget = widget
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
