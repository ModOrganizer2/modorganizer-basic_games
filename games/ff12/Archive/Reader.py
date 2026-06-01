import io
import struct
import zlib
from pathlib import Path
from typing import BinaryIO, Dict, List

from PyQt6.QtCore import qWarning


class ArchiveEntry:
    def __init__(self, original_size: int, data_offset: int, block_sizes: List[int]):
        self.original_size = original_size
        self.data_offset = data_offset
        self.block_sizes = block_sizes


class ArchiveReader:
    _MAX_BLOCK_SIZE = 64 * 1024

    def __init__(self, path: Path):
        self._filename = path
        self._entries: Dict[str, ArchiveEntry] = {}
        self._file_handle: BinaryIO | None = None

        self._load_metadata()

    def open(self) -> bool:
        """
        Open the archive for reading and store the file handle.
        Returns True if the file was successfully opened or already open, False otherwise.
        """
        if self._file_handle is not None:
            return True

        try:
            self._file_handle = open(self._filename, "rb")
            return True
        except Exception as e:
            qWarning(f"Failed to open archive: {e}")
            return False

    def close(self):
        """Close the file handle."""
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self):
        """Enable 'with' statement to automatically open and close the file handle."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Enable 'with' statement to automatically open and close the file handle."""
        self.close()

    def _load_metadata(self):
        """Load the archive metadata"""
        with self as file:
            file = file._file_handle
            try:
                header_data = file.read(16)
                if len(header_data) < 16:
                    raise EOFError("File too short for header")

                magic, header_size, file_count = struct.unpack("<IIQ", header_data)
                if magic != 0x4B595253:
                    raise ValueError("Invalid archive format")

                # Skip MD5 checksums for file names
                file.seek(16 * file_count, io.SEEK_CUR)

                file_metadata = self._read_file_metadata(file, file_count)
                file_path_data = self._read_file_path_data(file)
                block_count = self._get_block_count(file_metadata)
                global_block_sizes = self._read_block_sizes(file, block_count)

                for (
                    block_sizes_start_index,
                    original_size,
                    data_offset,
                    filepath_offset,
                ) in file_metadata:
                    name = self._read_null_string_lower(file_path_data, filepath_offset)

                    blocks = original_size // self._MAX_BLOCK_SIZE
                    if original_size % self._MAX_BLOCK_SIZE != 0:
                        blocks += 1

                    file_block_sizes = global_block_sizes[
                        block_sizes_start_index : block_sizes_start_index + blocks
                    ]
                    self._entries[name] = ArchiveEntry(
                        original_size, data_offset, file_block_sizes
                    )

            except Exception as e:
                qWarning(f"Failed to load archive metadata: {e}")

    def _read_file_metadata(self, file: BinaryIO, count: int) -> List[tuple]:
        """Read metadata for file entries"""
        file_struct = struct.Struct("<IIQQQ")
        file_metadata = []

        for _ in range(count):
            data = file.read(file_struct.size)
            if len(data) < file_struct.size:
                raise EOFError("Unexpected EOF reading file metadata")

            block_sizes_start_index, _, original_size, data_offset, filepath_offset = (
                file_struct.unpack(data)
            )
            file_metadata.append(
                (block_sizes_start_index, original_size, data_offset, filepath_offset)
            )

        return file_metadata

    def _read_file_path_data(self, file: BinaryIO) -> bytes:
        """Read data for file paths"""
        size_data = file.read(4)
        if len(size_data) < 4:
            raise EOFError("Unexpected EOF reading file path data size")

        size = struct.unpack("<I", size_data)[0]
        path_data = file.read(size - 4)
        if len(path_data) < (size - 4):
            raise EOFError("Unexpected EOF reading file path data")

        return path_data

    def _get_block_count(self, file_metadata: List[tuple]) -> int:
        """Calculate total number of blocks across all files"""
        count = 0
        for _, original_size, _, _ in file_metadata:
            blocks = original_size // self._MAX_BLOCK_SIZE
            if original_size % self._MAX_BLOCK_SIZE != 0:
                blocks += 1
            count += blocks
        return count

    def _read_block_sizes(self, file: BinaryIO, count: int) -> List[int]:
        """Read block sizes for all files"""
        data = file.read(count * 2)
        if len(data) < count * 2:
            raise ValueError("Unexpected EOF reading block sizes")

        return list(struct.unpack(f"<{count}H", data))

    def unpack_file(self, file_path: str, out_path: str):
        """Unpack a file from the archive"""
        if self._file_handle is None:
            raise ValueError("Archive file handle is not open")

        entry = self._entries.get(file_path)
        if entry is None:
            raise FileNotFoundError(f"File '{file_path}' not found in archive entries")

        self._file_handle.seek(entry.data_offset, io.SEEK_SET)
        block_count = 0

        with open(out_path, "wb") as out_file:
            for block_size in entry.block_sizes:
                if block_size == 0:
                    block_size = self._MAX_BLOCK_SIZE

                block_data = self._file_handle.read(block_size)
                if len(block_data) < block_size:
                    raise EOFError("Unexpected EOF reading data block")

                is_last_block = block_count == len(entry.block_sizes) - 1
                remaining_size = entry.original_size % self._MAX_BLOCK_SIZE

                if block_size == self._MAX_BLOCK_SIZE or (
                    is_last_block and block_size == remaining_size
                ):
                    out_file.write(block_data)
                else:
                    decompressed_data = zlib.decompress(block_data)
                    out_file.write(decompressed_data)

                block_count += 1

    @staticmethod
    def _read_null_string_lower(data: bytes, offset: int) -> str:
        """Read a null-terminated string from byte data and convert to lowercase."""
        end = data.find(b"\0", offset)
        if end == -1:
            end = len(data)

        return data[offset:end].decode("utf-8", errors="replace").lower()


def get_archives(folder: Path) -> list[Path]:
    """Return a list of all archives in the given folder."""
    if not folder.exists() or not folder.is_dir():
        return []

    return list(folder.glob("*.vbf"))
