import sys
import uuid
from datetime import datetime
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

import utils
from settings import SettingsWindow


class SmallClock(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.time = None
        self.setFixedSize(40, 40)

    def setTime(self, t):
        self.time = t
        self.update()

    def paintEvent(self, a0):
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
            angle_deg = (hour / 12.0) * 360.0 - 90
            import math

            hw = 1.2
            p.setPen(
                QtGui.QPen(QtGui.QColor("#fff"), hw, cap=QtCore.Qt.PenCapStyle.RoundCap)
            )
            rad = math.radians(angle_deg)
            p.drawLine(
                QtCore.QPointF(cx, cy),
                QtCore.QPointF(
                    cx + 0.3 * radius * math.cos(rad), cy + 0.3 * radius * math.sin(rad)
                ),
            )
            minute = self.time.minute
            m_deg = (minute / 60.0) * 360.0 - 90
            m_rad = math.radians(m_deg)
            p.setPen(
                QtGui.QPen(QtGui.QColor("#fff"), hw, cap=QtCore.Qt.PenCapStyle.RoundCap)
            )
            p.drawLine(
                QtCore.QPointF(cx, cy),
                QtCore.QPointF(
                    cx + 0.6 * radius * math.cos(m_rad),
                    cy + 0.6 * radius * math.sin(m_rad),
                ),
            )
        p.end()


class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._id = str(uuid.uuid4())
        self._gen = 0
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.cities = utils.load_cities()[:9]
        self.clocks: List[SmallClock] = []
        self.city_labels: List[QtWidgets.QLabel] = []
        self.time_labels: List[QtWidgets.QLabel] = []
        cols, rows = self._best_grid(len(self.cities))
        iw, ih = 100, 100
        w = max(120, cols * iw + 16)
        h = max(100, rows * ih + 16)
        self.setFixedSize(w, h)
        try:
            utils.move_to_top_right(self, margin=10)
        except Exception:
            pass
        self.bg = QtWidgets.QWidget(self)
        self.bg.setGeometry(0, 0, w, h)
        self.bg.setStyleSheet(
            "background: rgba(35, 39, 46, 0.85); border-radius: 16px;"
        )
        self.grid = QtWidgets.QGridLayout(self.bg)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setSpacing(4)
        self._rebuild_grid()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._sync)
        self.timer.setInterval(1000)
        self.timer.start()
        utils.EMITTER.sig.connect(self._on_result)
        for lbl in self.time_labels:
            lbl.setText("--:--")
        self._sync()

    @staticmethod
    def _best_grid(n: int):
        if n <= 1:
            return 1, 1
        import math

        cols = max(1, math.ceil(math.sqrt(n)))
        rows = (n + cols - 1) // cols
        if n <= 3:
            return n, 1
        return cols, rows

    def _clear_grid(self):
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
            sub_layout = item.layout()
            if sub_layout is not None:
                while sub_layout.count():
                    sub_item = sub_layout.takeAt(0)
                    if sub_item is None:
                        continue
                    sub_widget = sub_item.widget()
                    if sub_widget is not None:
                        try:
                            sub_widget.setParent(None)
                            sub_widget.deleteLater()
                        except Exception:
                            pass
                        continue
                    nested = sub_item.layout()
                    if nested is not None:
                        while nested.count():
                            ni = nested.takeAt(0)
                            if ni is None:
                                continue
                            nw = ni.widget()
                            if nw is not None:
                                try:
                                    nw.setParent(None)
                                    nw.deleteLater()
                                except Exception:
                                    pass

    def _rebuild_grid(self):
        self.clocks = []
        self.city_labels = []
        self.time_labels = []

        try:
            self._clear_grid()
        except Exception:
            pass

        self.cities = utils.load_cities()[:9]
        cols, rows = self._best_grid(len(self.cities))
        iw, ih = 100, 100
        w = max(120, cols * iw + 16)
        h = max(100, rows * ih + 16)
        try:
            try:
                prev = self.geometry()
            except Exception:
                prev = None
            if prev is None:
                old = globals().get("_APP_MAIN_WIDGET")
                if old is not None and old is not self:
                    try:
                        prev = old.geometry()
                    except Exception:
                        prev = None
        except Exception:
            prev = None
        try:
            self.setFixedSize(w, h)
        except Exception:
            pass
        try:
            if prev is not None:
                try:
                    scr = QtWidgets.QApplication.primaryScreen()
                    avail = (
                        scr.availableGeometry()
                        if scr is not None
                        else QtCore.QRect(0, 0, 800, 600)
                    )
                    desired_x = prev.x() + prev.width() - w
                    min_x = avail.x()
                    max_x = avail.x() + avail.width() - w
                    desired_x = max(min_x, min(desired_x, max_x))
                    desired_y = max(
                        avail.y(), min(prev.y(), avail.y() + avail.height() - h)
                    )
                    self.setGeometry(desired_x, desired_y, w, h)
                    try:
                        self.bg.setGeometry(0, 0, w, h)
                    except Exception:
                        pass
                except Exception:
                    try:
                        self.bg.setGeometry(0, 0, w, h)
                        utils.move_to_top_right(self, margin=10)
                    except Exception:
                        pass
            else:
                try:
                    self.bg.setGeometry(0, 0, w, h)
                except Exception:
                    pass
                utils.move_to_top_right(self, margin=10)
        except Exception:
            try:
                self.bg.setGeometry(0, 0, w, h)
            except Exception:
                pass

        for i, city in enumerate(self.cities):
            row = i // cols
            col = i % cols
            v = QtWidgets.QVBoxLayout()
            v.setSpacing(0)
            clock = SmallClock(self.bg)
            v.addWidget(clock, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            lu = QtWidgets.QVBoxLayout()
            lu.setSpacing(2)
            cl = QtWidgets.QLabel(city)
            cl.setStyleSheet(
                "font-size: 14px; color: #eee; text-align: center; background: none;"
            )
            cl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lu.addWidget(cl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            tl = QtWidgets.QLabel("--:--")
            tl.setStyleSheet(
                "font-size: 14px; color: #eee; text-align: center; background: none;"
            )
            tl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lu.addWidget(tl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            v.addLayout(lu)
            self.grid.addLayout(v, row, col)
            self.clocks.append(clock)
            self.city_labels.append(cl)
            self.time_labels.append(tl)

        for lbl in self.time_labels:
            lbl.setText("--:--")

        self._gen += 1

    def _sync(self):
        start = datetime.now()
        self.update_widget()
        elapsed = (datetime.now() - start).total_seconds()
        secs = 60 - datetime.now().second
        if secs <= elapsed:
            self.timer.setInterval(1000)
        else:
            self.timer.setInterval(max(100, int((secs - elapsed) * 1000)))
        try:
            self.timer.timeout.disconnect()
        except Exception:
            pass
        self.timer.timeout.connect(self._minute)

    def _minute(self):
        self.update_widget()
        try:
            self.timer.setInterval(60000)
        except Exception:
            self.timer.setInterval(1000)

    def update_widget(self):
        self.cities = utils.load_cities()[:9]
        n = len(self.cities)
        if n != len(self.clocks):
            try:
                current = globals().get("_APP_MAIN_WIDGET")
                if current is not None and current is not self:
                    return
            except Exception:
                pass
            try:
                self.timer.stop()
            except Exception:
                pass
            try:
                self._rebuild_grid()
            except Exception:
                pass
            try:
                self.timer.start()
            except Exception:
                pass
            return
        self._gen += 1
        gen = self._gen
        wid = self._id
        for i in range(n):
            c = self.cities[i]
            try:
                self.city_labels[i].setText(c)
            except Exception:
                pass
            try:
                self.time_labels[i].setText("--:--")
            except Exception:
                pass
            try:
                pass
            except Exception:
                pass
            try:
                utils.EXECUTOR.submit(self._worker, i, c, wid, gen)
            except Exception:
                pass

    def _worker(self, index: int, city: str, wid: str, gen: int):
        display, tz = utils.fuzzy_city_lookup(city, utils.load_city_timezones())
        tstr = "--:--"
        parsed = None
        if tz:
            tstr = utils.fetch_time(tz)
            try:
                dt = datetime.strptime(tstr, "%I:%M %p")
                parsed = dt.time()
            except Exception:
                parsed = None
        utils.EMITTER.sig.emit(index, display or city.title(), tstr, parsed, wid, gen)

    def _on_result(
        self, index: int, display: str, time_str: str, parsed, wid: str, gen: int
    ):
        if wid != self._id:
            return
        if gen != self._gen:
            return
        if index < 0 or index >= len(self.city_labels):
            return
        try:
            self.city_labels[index].setText(display)
        except Exception:
            pass
        try:
            self.time_labels[index].setText(time_str)
        except Exception:
            pass
        try:
            if parsed is not None:
                self.clocks[index].setTime(parsed)
        except Exception:
            try:
                self.clocks[index].setTime(None)
            except Exception:
                pass


replace_main_widget = utils.replace_main_widget


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    mw = MainWidget()
    try:
        mw.setWindowOpacity(0.0)
    except Exception:
        pass
    utils.move_to_top_right(mw, margin=10)
    mw.show()
    utils.fade_in(mw, duration=300)
    settings = SettingsWindow()

    def on_saved(cities: List[str]):
        try:
            mw = globals().get("_APP_MAIN_WIDGET")
            if mw is not None:
                try:
                    mw.update_widget()
                except Exception:
                    neww = MainWidget()
                    utils.replace_main_widget(neww)
            else:
                neww = MainWidget()
                utils.replace_main_widget(neww)
            settings.status_label.setText("Saved")
        except Exception:
            pass

    try:
        settings.settings_saved.connect(on_saved)
    except Exception:
        pass

    tray_icon = utils.pick_tray_icon()
    tray = QtWidgets.QSystemTrayIcon(tray_icon, parent=app)
    menu = QtWidgets.QMenu()
    act_settings = QtGui.QAction("Settings", menu)
    act_quit = QtGui.QAction("Quit", menu)
    menu.addAction(act_settings)
    menu.addAction(act_quit)
    act_settings.triggered.connect(lambda: settings.show())

    def _quit():
        try:
            utils.EXECUTOR.shutdown(wait=False)
        except Exception:
            pass
        try:
            settings.close()
        except Exception:
            pass
        try:
            g = globals().get("_APP_MAIN_WIDGET")
            if g is not None:
                g.close()
        except Exception:
            pass
        QtWidgets.QApplication.quit()

    act_quit.triggered.connect(_quit)
    tray.setContextMenu(menu)
    tray.setToolTip("TimeZones")
    tray.show()
    globals()["_APP_TRAY"] = tray
    globals()["_APP_SETTINGS_WINDOW"] = settings
    globals()["_APP_MAIN_WIDGET"] = mw
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
