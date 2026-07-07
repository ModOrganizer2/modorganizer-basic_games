from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .Reader import ArchiveReader


class ArchiveLoader(QThread):
    """Background thread for loading archive."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, archive_path: Path):
        super().__init__()
        self._archive_path = archive_path

    def run(self):
        """Load archive in background thread."""
        try:
            reader = ArchiveReader(self._archive_path)
            self.finished.emit(reader)
        except Exception as e:
            self.error.emit(str(e))
