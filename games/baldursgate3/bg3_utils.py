from functools import cached_property
from pathlib import Path

import mobase
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QProgressDialog, QMainWindow

from games.baldursgate3.lslib_retriever import LSLibRetriever


class BG3Utils:
    loose_file_folders = {
        "Public",
        "Mods",
        "Generated",
        "Localization",
        "ScriptExtender",
    }
    def __init__(self, organizer: mobase.IOrganizer, name: str):
        self.main_window = None
        self._organizer = organizer
        self._name = name
        self.lslib_retriever = LSLibRetriever(self)
    @cached_property
    def plugin_data_path(self) -> Path:
        """Gets the path to the data folder for the current plugin."""
        return Path(self._organizer.pluginDataPath(), self._name).absolute()
    @cached_property
    def tools_dir(self):
        return self.plugin_data_path / "tools"
    def get_setting(self, key: str) -> mobase.MoVariant:
        return self._organizer.pluginSetting(self._name, key)
    def tr(self, trstr: str) -> str:
        return QCoreApplication.translate(self._name, trstr)
    def create_progress_window(
        self, title: str, max_progress: int, msg: str = "", cancelable: bool = True
    ) -> QProgressDialog:
        progress = QProgressDialog(
            self.tr(msg if msg else title),
            self.tr("Cancel") if cancelable else None,
            0,
            max_progress,
            self.main_window,
        )
        progress.setWindowTitle(self.tr(f"BG3 Plugin: {title}"))
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.show()
        return progress
    def on_user_interface_initialized(self, window: QMainWindow) -> None:
        self.main_window = window
        pass
