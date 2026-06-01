from enum import IntEnum, auto

from PyQt6.QtCore import QAbstractItemModel, QFileInfo, QModelIndex, Qt
from PyQt6.QtWidgets import QFileIconProvider

from .Reader import ArchiveReader


class TreeNode:
    def __init__(self, name: str, parent=None, is_dir=False, size=0, entry=None):
        self.name = name
        self.parent = parent
        self.is_dir = is_dir
        self.size = size
        self.children = []
        self.entry = entry

        if parent:
            parent.children.append(self)

    def child_count(self) -> int:
        return len(self.children)

    def child(self, row: int) -> "TreeNode | None":
        if 0 <= row < len(self.children):
            return self.children[row]
        return None

    def row(self) -> int:
        if self.parent:
            return self.parent.children.index(self)
        return 0

    def path(self) -> str:
        """Get the full path to this node."""
        if self.parent and self.parent.parent:
            return self.parent.path() + "/" + self.name
        return self.name

    def sort_children(self, column: int, order: Qt.SortOrder):
        """Sort children by the specified column and order.
        Directories always come before files.
        Directories only reorder when column == NAME.
        """
        dirs = [i for i in self.children if i.is_dir]
        if column == ArchiveColumn.NAME:
            dirs.sort(
                key=lambda node: node.name.lower(),
                reverse=(order == Qt.SortOrder.DescendingOrder),
            )

        files = [i for i in self.children if not i.is_dir]
        if column == ArchiveColumn.NAME:
            files.sort(
                key=lambda node: node.name.lower(),
                reverse=(order == Qt.SortOrder.DescendingOrder),
            )
        elif column == ArchiveColumn.TYPE:
            files.sort(
                key=lambda node: QFileInfo(node.name).suffix().lower(),
                reverse=(order == Qt.SortOrder.DescendingOrder),
            )
        elif column == ArchiveColumn.SIZE:
            files.sort(
                key=lambda node: node.size,
                reverse=(order == Qt.SortOrder.DescendingOrder),
            )

        self.children = dirs + files
        for i in dirs:
            i.sort_children(column, order)


class ArchiveColumn(IntEnum):
    NAME = 0
    TYPE = auto()
    SIZE = auto()


class ArchiveModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._reader = None
        self._icon_provider = QFileIconProvider()
        self._root_node = TreeNode("", None, True)
        self._sort_column = ArchiveColumn.NAME
        self._sort_order = Qt.SortOrder.AscendingOrder

    def set_data(self, reader: ArchiveReader):
        self.beginResetModel()
        self._reader = reader
        self._build_tree()
        self._sort_tree()
        self.endResetModel()

    def _build_tree(self):
        """Build the tree structure from archive entries."""
        dir_nodes: dict[str, TreeNode] = {"": self._root_node}
        sorted_entries = sorted(self._reader._entries.items(), key=lambda x: x[0])

        for name, entry in sorted_entries:
            path_parts = name.split("/")
            current_path = ""
            current_node = self._root_node

            for i, part in enumerate(path_parts[:-1]):
                if current_path:
                    current_path += "/" + part
                else:
                    current_path = part

                if current_path not in dir_nodes:
                    dir_node = TreeNode(part, current_node, True)
                    dir_nodes[current_path] = dir_node
                    current_node = dir_node
                else:
                    current_node = dir_nodes[current_path]

            filename = path_parts[-1]
            TreeNode(filename, current_node, False, entry.original_size, entry)

    def _sort_tree(self):
        """Sort the entire tree."""
        self._root_node.sort_children(self._sort_column, self._sort_order)

    def sort(self, column: int, order: Qt.SortOrder):
        """Implement sorting with proper persistent index handling"""
        persistent_indexes = self.persistentIndexList()

        old_nodes = []
        for index in persistent_indexes:
            if index.isValid():
                old_nodes.append(index.internalPointer())
            else:
                old_nodes.append(None)

        self.layoutAboutToBeChanged.emit(
            [], QAbstractItemModel.LayoutChangeHint.VerticalSortHint
        )

        self._sort_column = column
        self._sort_order = order
        self._sort_tree()

        new_indexes = []
        for node in old_nodes:
            if node is not None:
                new_index = self._find_index_for_node(node)
                new_indexes.append(new_index)
            else:
                new_indexes.append(QModelIndex())

        for old_index, new_index in zip(persistent_indexes, new_indexes):
            self.changePersistentIndex(old_index, new_index)

        self.layoutChanged.emit(
            [], QAbstractItemModel.LayoutChangeHint.VerticalSortHint
        )

    def _find_index_for_node(self, target_node: TreeNode) -> QModelIndex:
        """Find the QModelIndex for a specific TreeNode after sorting"""
        if target_node == self._root_node:
            return QModelIndex()

        path = []
        current = target_node
        while current and current != self._root_node:
            path.append(current)
            current = current.parent

        current_index = QModelIndex()
        for node in reversed(path):
            parent_node = node.parent if node.parent else self._root_node
            row = parent_node.children.index(node)
            current_index = self.index(row, 0, current_index)

        return current_index

    def rowCount(self, parent: QModelIndex) -> int:
        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()

        return parent_node.child_count()

    def columnCount(self, parent: QModelIndex) -> int:
        return len(ArchiveColumn)

    def index(self, row: int, column: int, parent: QModelIndex) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()

        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)

        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_node = index.internalPointer()
        parent_node = child_node.parent

        if parent_node == self._root_node or parent_node is None:
            return QModelIndex()

        return self.createIndex(parent_node.row(), 0, parent_node)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == ArchiveColumn.NAME:
                return node.name
            elif column == ArchiveColumn.TYPE:
                if node.is_dir:
                    return "Folder"
                else:
                    file_info = QFileInfo(node.name)
                    return file_info.suffix()
            elif column == ArchiveColumn.SIZE:
                if node.is_dir:
                    return ""
                else:
                    return self._format_file_size(node.size)

        elif role == Qt.ItemDataRole.DecorationRole and column == ArchiveColumn.NAME:
            if node.is_dir:
                return self._icon_provider.icon(QFileIconProvider.IconType.Folder)
            else:
                file_info = QFileInfo(node.name)
                return self._icon_provider.icon(file_info)

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if (
            orientation != Qt.Orientation.Horizontal
            or role != Qt.ItemDataRole.DisplayRole
        ):
            return None

        match ArchiveColumn(section):
            case ArchiveColumn.NAME:
                return "Name"
            case ArchiveColumn.TYPE:
                return "Type"
            case ArchiveColumn.SIZE:
                return "Size"

        return None

    def get_node(self, index: QModelIndex) -> TreeNode | None:
        """Get the TreeNode for a given index."""
        if index.isValid():
            return index.internalPointer()
        return None

    @staticmethod
    def _format_file_size(size: int) -> str:
        """Format file size (B, KB, MB, GB) with proper fallback."""
        if size < 1024:
            return f"{size} B"

        size_f = float(size)
        for unit in ["KB", "MB", "GB"]:
            size_f /= 1024.0
            if size_f < 1024.0:
                if size_f < 10:
                    return f"{size_f:.2f} {unit}"
                elif size_f < 100:
                    return f"{size_f:.1f} {unit}"
                else:
                    return f"{size_f:.0f} {unit}"

        return f"{size_f:.2f} GB"
