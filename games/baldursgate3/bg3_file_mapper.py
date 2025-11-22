import functools
import os
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QDir, qDebug, qInfo, qWarning, QLoggingCategory
from PyQt6.QtWidgets import QApplication

import mobase

from . import bg3_utils


class BG3FileMapper(mobase.IPluginFileMapper):
    current_mappings: list[mobase.Mapping] = []

    def __init__(self, utils: bg3_utils.BG3Utils, doc_dir: Callable[[], QDir]):
        super().__init__()
        self._utils = utils
        self.doc_dir = doc_dir

    @functools.cached_property
    def doc_path(self):
        return Path(self.doc_dir().path())

    def mappings(self) -> list[mobase.Mapping]:
        qInfo("creating custom bg3 mappings")
        self.current_mappings.clear()
        active_mods = self._utils.active_mods()
        doc_dir = Path(self.doc_dir().path())
        progress = self._utils.create_progress_window(
            "Mapping files to documents folder", len(active_mods) + 1
        )
        docs_path_mods = doc_dir / "Mods"
        docs_path_se = doc_dir / "Script Extender"
        for mod in active_mods:
            modpath = Path(mod.absolutePath())
            self.map_files(modpath, dest=docs_path_mods, pattern="*.pak", rel=False)
            self.map_files(modpath / "Script Extender", dest=docs_path_se)
            progress.setValue(progress.value() + 1)
            QApplication.processEvents()
            if progress.wasCanceled():
                qWarning("mapping canceled by user")
                return self.current_mappings
        self.map_files(self._utils.overwrite_path)
        self.create_mapping(
            self._utils.modsettings_path,
            doc_dir / "PlayerProfiles" / "Public" / self._utils.modsettings_path.name,
        )
        progress.setValue(len(active_mods) + 1)
        QApplication.processEvents()
        progress.close()
        return self.current_mappings

    def map_files(
        self,
        path: Path,
        dest: Optional[Path] = None,
        pattern: str = "*",
        rel: bool = True,
    ):
        dest = dest if dest else self.doc_path
        dest_func: Callable[[Path], str] = (
            (lambda f: os.path.relpath(f, path)) if rel else lambda f: f.name
        )
        found_jsons: set[Path] = set()
        for file in list(path.rglob(pattern)):
            if self._utils.convert_yamls_to_json and (
                file.name.endswith(".yaml") or file.name.endswith(".yml")
            ):
                converted_path = file.parent / file.name.replace(
                    ".yaml", ".json"
                ).replace(".yml", ".json")
                try:
                    if not converted_path.exists() or os.path.getmtime(
                        file
                    ) > os.path.getmtime(converted_path):
                        import json
                        import yaml
                        with open(file, "r") as yaml_file:
                            with open(converted_path, "w") as json_file:
                                json.dump(
                                    yaml.safe_load(yaml_file), json_file, indent=2
                                )
                        qDebug(f"Converted {file} to JSON")
                    found_jsons.add(converted_path)
                except OSError as e:
                    qWarning(f"Error accessing file {converted_path}: {e}")
            elif file.name.endswith(".json"):
                found_jsons.add(file)
            else:
                self.create_mapping(file, dest / dest_func(file))
        for file in found_jsons:
            self.create_mapping(file, dest / dest_func(file))

    def create_mapping(self, file: Path, dest: Path):
        self.current_mappings.append(
            mobase.Mapping(
                source=str(file),
                destination=str(dest),
                is_directory=file.is_dir(),
                create_target=True,
            )
        )
