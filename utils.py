from __future__ import annotations

import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import requests
from PyQt6 import QtCore, QtGui, QtWidgets


class CityEntry(TypedDict, total=False):
    label: str
    tz: str
    city: str


def normalizeCityQuery(text: str) -> str:
    query = (text or "").strip()
    if not query:
        return ""
    query = re.sub(r"[^\w\s'-]", " ", query)
    query = re.sub(r"\s+", " ", query).strip().lower()
    return query


def looksLikePlaceQuery(normalizedQuery: str) -> bool:
    if not normalizedQuery or len(normalizedQuery) < 3:
        return False
    if not re.fullmatch(r"[a-z][a-z\s'’-]{2,}$", normalizedQuery):
        return False

    bannedWords = {
        "test",
        "testing",
        "asdf",
        "qwerty",
        "hello",
        "world",
        "random",
        "city",
        "timezone",
        "time",
        "none",
        "null",
        "aaaa",
        "aaaaa",
    }
    if normalizedQuery.replace(" ", "") in bannedWords or normalizedQuery in bannedWords:
        return False

    return True


try:
    from rapidfuzz import process as rfProcess
except Exception:
    rfProcess = None

try:
    from rapidfuzz import fuzz as rfFuzz
except Exception:
    rfFuzz = None

try:
    from geopy.geocoders import Nominatim
except Exception:
    Nominatim = None

try:
    from timezonefinder import TimezoneFinder
except Exception:
    TimezoneFinder = None

executor = ThreadPoolExecutor(max_workers=4)

defaultSuggestionLimit = 5
defaultSuggestionCutoff = 70
defaultGeocodeSuggestionLimit = 5


def rootDir() -> str:
    return os.path.dirname(__file__)


def loadCityTimezones(filename: Optional[str] = None) -> Dict[str, str]:
    if filename is None:
        filename = os.path.join(rootDir(), "timezonesDict.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k).lower(): str(v) for k, v in data.items()}
            if isinstance(data, list):
                output: Dict[str, str] = {}
                for item in data:
                    if isinstance(item, dict):
                        city = item.get("city") or item.get("name")
                        timezone = item.get("timezone") or item.get("tz") or item.get("tzname")
                        if city and timezone:
                            output[str(city).lower()] = str(timezone)
                if output:
                    return output
    except Exception:
        pass
    return {
        "new york": "America/New_York",
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
    }


def loadCityEntries(filename: Optional[str] = None) -> List[CityEntry]:
    if filename is None:
        filename = os.path.join(rootDir(), "timezones.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                output: List[CityEntry] = []
                for entry in data:
                    if not isinstance(entry, dict):
                        continue

                    label = entry.get("label")
                    timezone = entry.get("tz")
                    city = entry.get("city")

                    current: CityEntry = {}
                    if isinstance(label, str) and label.strip():
                        current["label"] = label.strip()
                    if isinstance(timezone, str) and timezone.strip():
                        current["tz"] = timezone.strip()
                    if isinstance(city, str) and city.strip():
                        current["city"] = city.strip()

                    if current:
                        output.append(current)

                if output:
                    return output
    except Exception:
        pass

    return [
        {"label": "New York", "tz": "America/New_York"},
        {"label": "London", "tz": "Europe/London"},
        {"label": "Tokyo", "tz": "Asia/Tokyo"},
    ]


def saveCityEntries(entries: List[CityEntry], filename: Optional[str] = None) -> None:
    if filename is None:
        filename = os.path.join(rootDir(), "timezones.json")

    payload: List[Dict[str, str]] = []
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
            payload.append({"label": label.strip(), "tz": timezone.strip()})

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)


def loadCities(filename: Optional[str] = None) -> List[str]:
    entries = loadCityEntries(filename)
    output: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        label = entry.get("label")
        city = entry.get("city")
        if isinstance(label, str) and label.strip():
            output.append(label.strip())
        elif isinstance(city, str) and city.strip():
            output.append(city.strip())
    if output:
        return output
    return ["New York", "London", "Tokyo"]


def suggestCities(
    query: str,
    cityTz: Dict[str, str],
    *,
    limit: int = defaultSuggestionLimit,
    scoreCutoff: int = defaultSuggestionCutoff,
) -> List[Tuple[str, str, int]]:
    if not cityTz:
        return []
    normalizedQuery = normalizeCityQuery(query)
    if len(normalizedQuery) < 2:
        return []
    if rfProcess is None:
        return []

    choices = list(cityTz.keys())

    scorer: Any = None
    if rfFuzz is not None:
        scorer = rfFuzz.token_sort_ratio

    try:
        matches = rfProcess.extract(
            normalizedQuery,
            choices,
            scorer=scorer,
            score_cutoff=scoreCutoff,
            limit=max(1, int(limit)),
        )
    except Exception:
        return []

    output: List[Tuple[str, str, int]] = []
    for match in matches:
        key = match[0]
        score = int(match[1])
        timezone = cityTz.get(key)
        if not timezone:
            continue
        output.append((key.title(), timezone, score))
    return output


def suggestPlacesGeocode(
    query: str,
    *,
    limit: int = defaultGeocodeSuggestionLimit,
) -> List[Tuple[str, str, int]]:
    normalizedQuery = normalizeCityQuery(query)
    if not looksLikePlaceQuery(normalizedQuery):
        return []
    if Nominatim is None or TimezoneFinder is None:
        return []

    try:
        geocoder = Nominatim(user_agent="TimeZonesWidget/1.0 (geopy; timezone suggestions)")
    except Exception:
        return []

    try:
        results = geocoder.geocode(
            query,
            exactly_one=False,
            limit=max(1, int(limit)),
            addressdetails=True,
        )
    except TypeError:
        try:
            results = geocoder.geocode(query, exactly_one=False, limit=max(1, int(limit)))
        except Exception:
            return []
    except Exception:
        return []

    if not results:
        return []

    if not isinstance(results, list):
        results = [results]

    timezoneFinder = TimezoneFinder()
    output: List[Tuple[str, str, int]] = []
    seenPlaceNames: set[str] = set()

    for location in results:
        try:
            latitude = getattr(location, "latitude", None)
            longitude = getattr(location, "longitude", None)
            if latitude is None or longitude is None:
                continue

            timezone = timezoneFinder.timezone_at(lat=latitude, lng=longitude)
            if not timezone:
                continue

            address = getattr(location, "address", None)
            label = str(address).strip() if address else query.strip()
            if not label:
                continue

            placeName = label.split(",")[0].strip() if "," in label else label.strip()
            if not placeName:
                continue

            placeNormalized = normalizeCityQuery(placeName)
            score = 0
            if rfFuzz is not None:
                score = int(rfFuzz.token_sort_ratio(normalizedQuery, placeNormalized))
                if score < 70:
                    continue
            else:
                if normalizedQuery not in placeNormalized:
                    continue
                score = 75

            if placeNormalized in seenPlaceNames:
                continue
            seenPlaceNames.add(placeNormalized)

            output.append((label, timezone, score))
        except Exception:
            continue

    output.sort(key=lambda item: item[2], reverse=True)
    return output[: max(1, int(limit))]


def fetchTime(timezone: str, timeout: int = 5) -> str:
    if not timezone:
        return "--:--"
    try:
        url = f"https://timeapi.io/api/Time/current/zone?timeZone={timezone}"
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            payload = response.json()
            time24 = payload.get("time") or payload.get("time24")
            if time24:
                try:
                    dt = datetime.strptime(time24, "%H:%M")
                    if sys.platform.startswith("win"):
                        return dt.strftime("%#I:%M %p")
                    return dt.strftime("%-I:%M %p")
                except Exception:
                    return str(time24)
    except Exception:
        pass
    return "--:--"


def moveToTopRight(widget: QtWidgets.QWidget, margin: int = 10) -> None:
    screen = QtWidgets.QApplication.primaryScreen()
    geometry = screen.availableGeometry() if screen is not None else QtCore.QRect(0, 0, 800, 600)
    x = geometry.width() - widget.width() - margin
    y = margin
    try:
        widget.move(x, y)
    except Exception:
        try:
            widgetGeometry = widget.geometry()
            widgetGeometry.moveTo(x, y)
            widget.setGeometry(widgetGeometry)
        except Exception:
            pass


def fadeIn(
    widget: QtWidgets.QWidget, duration: int = 300
) -> Optional[QtCore.QPropertyAnimation]:
    try:
        widget.setWindowOpacity(0.0)
    except Exception:
        pass
    animation = QtCore.QPropertyAnimation(widget, b"windowOpacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    try:
        animation.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
    except Exception:
        pass
    try:
        setattr(widget, "_fadeAnim", animation)
    except Exception:
        pass
    animation.start()
    return animation


def getTrayIconCandidates() -> List[str]:
    here = rootDir()
    return [
        os.path.join(here, "assets", "timezones.ico"),
        os.path.join(here, "timezones.ico"),
    ]


def pickTrayIcon() -> QtGui.QIcon:
    for iconPath in getTrayIconCandidates():
        if os.path.exists(iconPath):
            try:
                return QtGui.QIcon(iconPath)
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


emitter = ResultEmitter()

replaceStateLock = threading.Lock()
replaceScheduled = False
pendingEntry: Optional[Dict] = None


def performReplace():
    global replaceScheduled
    global pendingEntry

    with replaceStateLock:
        entry = pendingEntry
        pendingEntry = None
        replaceScheduled = False

    if not entry:
        return

    newWidget = entry.get("newWidget")
    previousGeometry = entry.get("previousGeometry")
    if newWidget is None:
        return

    oldWidget = globals().get("_APP_MAIN_WIDGET")

    try:
        if oldWidget is not None:
            try:
                oldWidget.hide()
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass
    except Exception:
        pass

    globals()["_APP_MAIN_WIDGET"] = newWidget

    try:
        if previousGeometry is not None:
            try:
                previousX = previousGeometry.x()
                previousWidth = previousGeometry.width()
                previousY = previousGeometry.y()
                newWidth = newWidget.width()
                newHeight = newWidget.height()
                desiredX = previousX + previousWidth - newWidth
                screen = QtWidgets.QApplication.primaryScreen()
                if screen is not None:
                    availableGeometry = screen.availableGeometry()
                    minX = availableGeometry.x()
                    maxX = availableGeometry.x() + availableGeometry.width() - newWidth
                    desiredX = max(minX, min(desiredX, maxX))
                    desiredY = max(
                        availableGeometry.y(),
                        min(previousY, availableGeometry.y() + availableGeometry.height() - newHeight),
                    )
                else:
                    desiredY = previousY
                newWidget.setGeometry(desiredX, desiredY, newWidth, newHeight)
            except Exception:
                moveToTopRight(newWidget, margin=10)
        else:
            moveToTopRight(newWidget, margin=10)
    except Exception:
        try:
            moveToTopRight(newWidget, margin=10)
        except Exception:
            pass

    try:
        newWidget.setWindowOpacity(0.0)
    except Exception:
        pass

    try:
        newWidget.show()
        try:
            newWidget.raise_()
        except Exception:
            pass
        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass
        fadeIn(newWidget, duration=250)
    except Exception:
        try:
            newWidget.show()
        except Exception:
            pass

    try:
        if oldWidget is not None and oldWidget is not newWidget:
            oldWidget.deleteLater()
    except Exception:
        pass


def replaceMainWidget(newWidget: QtWidgets.QWidget) -> None:
    global replaceScheduled
    global pendingEntry

    with replaceStateLock:
        oldWidget = globals().get("_APP_MAIN_WIDGET")
        try:
            previousGeometry = oldWidget.geometry() if oldWidget is not None else None
        except Exception:
            previousGeometry = None

        pendingEntry = {"newWidget": newWidget, "previousGeometry": previousGeometry}

        if replaceScheduled:
            return
        replaceScheduled = True

    try:
        QtCore.QTimer.singleShot(0, performReplace)
    except Exception:
        performReplace()
