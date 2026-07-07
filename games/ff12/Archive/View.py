from pathlib import Path

from PyQt6.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QModelIndex,
    QPoint,
    QStandardPaths,
    Qt,
)
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QTreeView,
    QWidget,
)

from .Model import ArchiveColumn, ArchiveModel, TreeNode


class ArchiveView(QTreeView):
    def __init__(self, parent: QWidget | None):
        super().__init__(parent)

        self.setRootIndex(QModelIndex())
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(  # pyright: ignore[reportUnknownMemberType]
            self._show_context_menu
        )
        self._last_export_dir: str | None = None
        self._model: ArchiveModel | None = None

    def _setup_view(self) -> None:
        """Setup view appearance and default sorting."""
        if self._model is None:
            return

        self.setColumnWidth(ArchiveColumn.NAME, 290)
        self.setColumnWidth(ArchiveColumn.TYPE, 90)
        self.setColumnWidth(ArchiveColumn.SIZE, 90)
        self.sortByColumn(ArchiveColumn.NAME, Qt.SortOrder.AscendingOrder)

    def setModel(self, model: QAbstractItemModel | None) -> None:
        """Setup view after model is set."""
        super().setModel(model)
        self._model = model if isinstance(model, ArchiveModel) else None
        self._setup_view()

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu at the given position."""
        if self._model is None:
            return

        menu = QMenu(self)

        selected_indexes = self._get_selected_indexes()
        if selected_indexes:
            export_action = QAction("Export", self)
            export_action.triggered.connect(  # pyright: ignore[reportUnknownMemberType]
                lambda: self._export_selection(selected_indexes)
            )
            menu.addAction(export_action)  # pyright: ignore[reportUnknownMemberType]

        if menu.actions():
            menu.exec(self.mapToGlobal(position))

    def _export_selection(self, indexes: list[QModelIndex]) -> None:
        start_dir = self._last_export_dir or QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DesktopLocation
        )

        export_dir = QFileDialog.getExistingDirectory(
            self, "Choose Export Directory", start_dir
        )
        if not export_dir:
            return

        self._last_export_dir = export_dir
        export_path = Path(export_dir)

        files_to_export = self._get_selected_files(indexes)
        if not files_to_export:
            QMessageBox.information(self, "Export", "No files to export.")
            return

        progress = QProgressDialog(
            "Exporting files...", "Cancel", 0, len(files_to_export), self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        exported_count = 0
        failed_files: list[str] = []

        assert self._model is not None
        reader = self._model.get_reader()
        if reader is None:
            progress.close()
            return

        with reader:
            for i, file_node in enumerate(files_to_export):
                if progress.wasCanceled():
                    break

                progress.setLabelText(f"Exporting: {file_node.name}")
                progress.setValue(i)
                QCoreApplication.processEvents()

                relative_path = file_node.path()
                try:
                    output_file = export_path / Path(relative_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)

                    reader.unpack_file(relative_path, output_file)

                    exported_count += 1
                except Exception as e:
                    failed_files.append(f"{relative_path} ({str(e)})")

        progress.close()
        if failed_files:
            log_path = export_path / "export.log"
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write("\n".join(failed_files))

            total_count = len(files_to_export)
            fail_count = len(failed_files)
            QMessageBox.warning(
                self,
                "Export Complete",
                f"Only {total_count - fail_count} of {total_count} files were exported successfully.\n"
                f"See log for details: {log_path}",
            )
        else:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {exported_count} file(s) to:\n{export_path}",
            )

    def _get_selected_indexes(self) -> list[QModelIndex]:
        sm = self.selectionModel()
        assert sm is not None
        indexes = sm.selectedIndexes()

        rows: dict[int, QModelIndex] = {}
        for index in indexes:
            if index.column() == 0:
                rows[index.row()] = index

        return list(rows.values())

    def _get_selected_files(self, indexes: list[QModelIndex]) -> list[TreeNode]:
        files: list[TreeNode] = []

        def collect(node: TreeNode) -> None:
            if node.is_dir:
                for child in node.children:
                    collect(child)
            else:
                files.append(node)

        for index in indexes:
            node = self._model.get_node(index) if self._model else None
            if node:
                collect(node)
        return files
