from __future__ import annotations

import json
import os
import sys
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

try:
    from rapidfuzz import process as rf_process
except Exception:
    rf_process = None

try:
    from geopy.geocoders import Nominatim
except Exception:
    Nominatim = None

try:
    from timezonefinder import TimezoneFinder
except Exception:
    TimezoneFinder = None

from PyQt6 import QtCore, QtGui, QtWidgets

EXECUTOR = ThreadPoolExecutor(max_workers=4)

_CACHE_MAX = 128
_cache_lock = threading.Lock()
_cache: "OrderedDict[str, Tuple[Optional[str], Optional[str]]]" = OrderedDict()


def _root_dir() -> str:
    return os.path.dirname(__file__)


def cache_get(key: str) -> Optional[Tuple[Optional[str], Optional[str]]]:
    if not key:
        return None
    k = key.strip().lower()
    with _cache_lock:
        v = _cache.get(k)
        if v is not None:
            try:
                _cache.move_to_end(k)
            except Exception:
                pass
        return v


def cache_put(key: str, value: Tuple[Optional[str], Optional[str]]) -> None:
    if not key:
        return
    k = key.strip().lower()
    with _cache_lock:
        _cache[k] = value
        try:
            _cache.move_to_end(k)
        except Exception:
            pass
        while len(_cache) > _CACHE_MAX:
            try:
                _cache.popitem(last=False)
            except Exception:
                break


def load_city_timezones(filename: Optional[str] = None) -> Dict[str, str]:
    if filename is None:
        filename = os.path.join(_root_dir(), "timezonesDict.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k).lower(): str(v) for k, v in data.items()}
            if isinstance(data, list):
                out: Dict[str, str] = {}
                for it in data:
                    if isinstance(it, dict):
                        city = it.get("city") or it.get("name")
                        tz = it.get("timezone") or it.get("tz") or it.get("tzname")
                        if city and tz:
                            out[str(city).lower()] = str(tz)
                if out:
                    return out
    except Exception:
        pass
    return {
        "new york": "America/New_York",
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
    }


def load_cities(filename: Optional[str] = None) -> List[str]:
    if filename is None:
        filename = os.path.join(_root_dir(), "timezones.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                out: List[str] = []
                for e in data:
                    if isinstance(e, dict) and "city" in e:
                        out.append(str(e["city"]))
                if out:
                    return out
    except Exception:
        pass
    return ["New York", "London", "Tokyo"]


def fuzzy_city_lookup(city: str, city_tz: Dict[str, str]) -> Tuple[str, Optional[str]]:
    if not city:
        return city, None
    cached = cache_get(city)
    if cached is not None:
        return (cached[0] or city.title(), cached[1])

    q = city.strip()
    if rf_process is not None and city_tz:
        try:
            choices = list(city_tz.keys())
            res = rf_process.extractOne(q, choices, score_cutoff=60)
            if res:
                match = res[0]
                tz = city_tz.get(match)
                if tz:
                    val = (match.title(), tz)
                    cache_put(city, val)
                    return val
        except Exception:
            pass

    if Nominatim is not None and TimezoneFinder is not None:
        try:
            geo = Nominatim(user_agent="timezone_utils")
            loc = geo.geocode(q)
            if loc:
                lat = getattr(loc, "latitude", None)
                lng = getattr(loc, "longitude", None)
                if lat is not None and lng is not None:
                    tf = TimezoneFinder()
                    tz = tf.timezone_at(lat=lat, lng=lng)
                    if tz:
                        addr = getattr(loc, "address", None)
                        display = (
                            addr.split(",")[0].strip().title() if addr else q.title()
                        )
                        val = (display, tz)
                        cache_put(city, val)
                        return val
        except Exception:
            pass

    return q.title(), None


def fetch_time(tz: str, timeout: int = 5) -> str:
    if not tz:
        return "--:--"
    try:
        url = f"https://timeapi.io/api/Time/current/zone?timeZone={tz}"
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            j = r.json()
            t24 = j.get("time") or j.get("time24")
            if t24:
                try:
                    dt = datetime.strptime(t24, "%H:%M")
                    if sys.platform.startswith("win"):
                        return dt.strftime("%#I:%M %p")
                    else:
                        return dt.strftime("%-I:%M %p")
                except Exception:
                    return str(t24)
    except Exception:
        pass
    return "--:--"


def move_to_top_right(widget: QtWidgets.QWidget, margin: int = 10) -> None:
    scr = QtWidgets.QApplication.primaryScreen()
    geo = scr.availableGeometry() if scr is not None else QtCore.QRect(0, 0, 800, 600)
    x = geo.width() - widget.width() - margin
    y = margin
    try:
        widget.move(x, y)
    except Exception:
        try:
            g = widget.geometry()
            g.moveTo(x, y)
            widget.setGeometry(g)
        except Exception:
            pass


def fade_in(
    widget: QtWidgets.QWidget, duration: int = 300
) -> Optional[QtCore.QPropertyAnimation]:
    try:
        widget.setWindowOpacity(0.0)
    except Exception:
        pass
    anim = QtCore.QPropertyAnimation(widget, b"windowOpacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    try:
        anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
    except Exception:
        pass
    try:
        setattr(widget, "_fade_anim", anim)
    except Exception:
        pass
    anim.start()
    return anim


def get_tray_icon_candidates() -> List[str]:
    here = _root_dir()
    return [
        os.path.join(here, "assets", "timezones.ico"),
        os.path.join(here, "timezones.ico"),
    ]


def pick_tray_icon() -> QtGui.QIcon:
    for p in get_tray_icon_candidates():
        if os.path.exists(p):
            try:
                return QtGui.QIcon(p)
            except Exception:
                pass
    style = QtWidgets.QApplication.style()
    if style is not None:
        try:
            return style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        except Exception:
            pass
    return QtGui.QIcon()


class ResultEmitter(QtCore.QObject):
    sig = QtCore.pyqtSignal(int, str, str, object, str, int)


EMITTER = ResultEmitter()

_replace_lock = threading.Lock()
_replace_state_lock = threading.Lock()
_replace_scheduled = False
_pending_entry: Optional[Dict] = None


def _perform_replace():
    global _replace_scheduled
    global _pending_entry

    with _replace_state_lock:
        entry = _pending_entry
        _pending_entry = None
        _replace_scheduled = False

    if not entry:
        return

    new_widget = entry.get("new_widget")
    prev_geom = entry.get("prev_geom")
    if new_widget is None:
        return

    old = globals().get("_APP_MAIN_WIDGET")

    try:
        if old is not None:
            try:
                old.hide()
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass
    except Exception:
        pass

    globals()["_APP_MAIN_WIDGET"] = new_widget

    try:
        if prev_geom is not None:
            try:
                px = prev_geom.x()
                pw = prev_geom.width()
                py = prev_geom.y()
                nw = new_widget.width()
                nh = new_widget.height()
                desired_x = px + pw - nw
                scr = QtWidgets.QApplication.primaryScreen()
                if scr is not None:
                    avail = scr.availableGeometry()
                    min_x = avail.x()
                    max_x = avail.x() + avail.width() - nw
                    desired_x = max(min_x, min(desired_x, max_x))
                    desired_y = max(avail.y(), min(py, avail.y() + avail.height() - nh))
                else:
                    desired_y = py
                new_widget.setGeometry(desired_x, desired_y, nw, nh)
            except Exception:
                move_to_top_right(new_widget, margin=10)
        else:
            move_to_top_right(new_widget, margin=10)
    except Exception:
        try:
            move_to_top_right(new_widget, margin=10)
        except Exception:
            pass

    try:
        new_widget.setWindowOpacity(0.0)
    except Exception:
        pass

    try:
        new_widget.show()
        try:
            new_widget.raise_()
        except Exception:
            pass
        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass
        fade_in(new_widget, duration=250)
    except Exception:
        try:
            new_widget.show()
        except Exception:
            pass

    try:
        if old is not None and old is not new_widget:
            old.deleteLater()
    except Exception:
        pass


def replace_main_widget(new_widget: QtWidgets.QWidget) -> None:
    global _replace_scheduled
    global _pending_entry

    with _replace_state_lock:
        old = globals().get("_APP_MAIN_WIDGET")
        try:
            prev_geom = old.geometry() if old is not None else None
        except Exception:
            prev_geom = None

        _pending_entry = {"new_widget": new_widget, "prev_geom": prev_geom}

        if _replace_scheduled:
            return
        _replace_scheduled = True

    try:
        QtCore.QTimer.singleShot(0, _perform_replace)
    except Exception:
        _perform_replace()
