from PyQt6 import QtWidgets
import json

class SettingsWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setMinimumSize(300, 200)

    def open(self):
        self.show()

    def close(self):
        self.hide()

    def saveSettings(self, cityList):
        with open("timezones.json", "w", encoding="utf-8") as f:
            json.dump([{"city": city} for city in cityList], f, indent=4)
