from pathlib import Path
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QHideEvent, QShowEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .Loader import ArchiveLoader
from .Model import ArchiveModel
from .Reader import ArchiveReader, get_archives
from .View import ArchiveView


class ArchiveContainerWidget(QWidget):
    def __init__(self, content_path: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self._content_path = content_path
        self._current_content: ArchiveContentWidget | None = None
        self._loader: ArchiveLoader | None = None

        v_layout = QVBoxLayout(self)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        h_layout = QHBoxLayout()
        label = QLabel("File")
        h_layout.addWidget(label)

        self._combo_box = QComboBox(self)
        self._combo_box.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        h_layout.addWidget(self._combo_box)
        v_layout.addLayout(h_layout)

        self._content = QVBoxLayout()
        v_layout.addLayout(self._content)

        self._combo_box.currentIndexChanged.connect(  # pyright: ignore[reportUnknownMemberType]
            self._load_selected
        )

    def _reset_combo_box(self) -> None:
        self._combo_box.blockSignals(True)
        self._combo_box.clear()
        for p in sorted(get_archives(self._content_path)):
            self._combo_box.addItem(p.name, userData=p)
        self._combo_box.blockSignals(False)

    def _clear_current_content(self) -> None:
        if self._loader and self._loader.isRunning():
            self._loader.finished.disconnect()  # pyright: ignore[reportUnknownMemberType]
            self._loader.error.disconnect()  # pyright: ignore[reportUnknownMemberType]
            self._loader.quit()
            self._loader = None

        if self._current_content:
            self._current_content.setParent(None)
            self._current_content.deleteLater()
            self._current_content = None

    def _load_selected(self) -> None:
        archive_path = cast(Path | None, self._combo_box.currentData())
        if not archive_path:
            return

        self._clear_current_content()
        self._current_content = ArchiveContentWidget()
        self._content.addWidget(self._current_content)

        self._loader = ArchiveLoader(archive_path)
        self._loader.finished.connect(  # pyright: ignore[reportUnknownMemberType]
            self._on_load_finished_callback
        )
        self._loader.error.connect(  # pyright: ignore[reportUnknownMemberType]
            self._on_load_error_callback
        )
        self._loader.start()

    def _on_load_finished_callback(self, reader: ArchiveReader) -> None:
        """Called when archive loading is complete."""
        if self._current_content:
            self._current_content.load_data(reader)

        if self._loader:
            self._loader.deleteLater()
            self._loader = None

    def _on_load_error_callback(self, _error_msg: str) -> None:
        """Called when archive loading fails."""
        if self._loader:
            self._loader.deleteLater()
            self._loader = None

    def showEvent(self, a0: QShowEvent | None) -> None:
        super().showEvent(a0)
        self._reset_combo_box()
        if self._combo_box.count() > 0 and not self._current_content:
            self._load_selected()

    def hideEvent(self, a0: QHideEvent | None) -> None:
        super().hideEvent(a0)
        self._clear_current_content()


class ArchiveContentWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._model = ArchiveModel()
        self._view = ArchiveView(self)
        self._view.setModel(self._model)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self._view)
        self.setLayout(self._layout)

    def load_data(self, reader: ArchiveReader) -> None:
        self._model.set_data(reader)
