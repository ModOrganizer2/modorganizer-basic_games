import functools
import json
import os
import shutil
import typing
from pathlib import Path

import mobase
import yaml
from PyQt6.QtCore import (
    QCoreApplication,
    QDir,
    QEventLoop,
    QRunnable,
    Qt,
    QThread,
    QThreadPool,
    qInfo,
    qWarning,
)
from PyQt6.QtWidgets import QApplication, QMainWindow, QProgressDialog

loose_file_folders = {
    "Public",
    "Mods",
    "Generated",
    "Localization",
    "ScriptExtender",
}


class BG3Utils:
    _mod_settings_xml_start = """<?xml version="1.0" encoding="UTF-8"?>
    <save>
        <version major="4" minor="8" revision="0" build="200"/>
        <region id="ModuleSettings">
            <node id="root">
                <children>
                    <node id="Mods">
                        <children>
                            <node id="ModuleShortDesc">
                                <attribute id="Folder" type="LSString" value="GustavX"/>
                                <attribute id="MD5" type="LSString" value=""/>
                                <attribute id="Name" type="LSString" value="GustavX"/>
                                <attribute id="PublishHandle" type="uint64" value="0"/>
                                <attribute id="UUID" type="guid" value="cb555efe-2d9e-131f-8195-a89329d218ea"/>
                                <attribute id="Version64" type="int64" value="36028797018963968"/>
                            </node>"""
    _mod_settings_xml_end = """
                        </children>
                    </node>
                </children>
            </node>
        </region>
    </save>"""

    def __init__(self, name: str):
        self.main_window = None
        self._name = name
        from . import lslib_retriever, pak_parser

        self._lslib_retriever = lslib_retriever.LSLibRetriever(self)
        self._pak_parser = pak_parser.BG3PakParser(self)

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer

    @functools.cached_property
    def autobuild_paks(self):
        return bool(self.get_setting("autobuild_paks"))

    @functools.cached_property
    def extract_full_package(self):
        return bool(self.get_setting("extract_full_package"))

    @functools.cached_property
    def remove_extracted_metadata(self):
        return bool(self.get_setting("remove_extracted_metadata"))

    @functools.cached_property
    def force_load_dlls(self):
        return bool(self.get_setting("force_load_dlls"))

    @functools.cached_property
    def log_diff(self):
        return bool(self.get_setting("log_diff"))

    @functools.cached_property
    def convert_yamls_to_json(self):
        return bool(self.get_setting("convert_yamls_to_json"))

    @functools.cached_property
    def log_dir(self):
        return Path(self._organizer.basePath()) / "logs/"

    @functools.cached_property
    def modsettings_backup(self):
        return self.plugin_data_path / "temp/modsettings.lsx"

    @functools.cached_property
    def modsettings_path(self):
        return self.overwrite_path / "PlayerProfiles/Public/modsettings.lsx"

    @functools.cached_property
    def plugin_data_path(self) -> Path:
        """Gets the path to the data folder for the current plugin."""
        return Path(self._organizer.pluginDataPath(), self._name).absolute()

    @functools.cached_property
    def tools_dir(self):
        return self.plugin_data_path / "tools"

    @functools.cached_property
    def overwrite_path(self):
        return Path(self._organizer.overwritePath())

    def active_mods(self) -> list[mobase.IModInterface]:
        modlist = self._organizer.modList()
        return [
            modlist.getMod(mod_name)
            for mod_name in filter(
                lambda mod: modlist.state(mod) & mobase.ModState.ACTIVE,
                modlist.allModsByProfilePriority(),
            )
        ]

    def _set_setting(self, key: str, value: mobase.MoVariant):
        self._organizer.setPluginSetting(self._name, key, value)

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

    def on_settings_changed(
        self,
        plugin_name: str,
        setting: str,
        old: mobase.MoVariant,
        new: mobase.MoVariant,
    ) -> None:
        if self._name != plugin_name:
            return
        if new and setting == "check_for_lslib_updates":
            try:
                self._lslib_retriever.download_lslib_if_missing()
            finally:
                self._set_setting(setting, False)
        elif new and setting == "force_reparse_metadata":
            try:
                self.construct_modsettings_xml(
                    exec_path="bin/bg3", force_reparse_metadata=True
                )
            finally:
                self._set_setting(setting, False)
        elif new and setting == "convert_jsons_to_yaml":
            try:
                self._convert_jsons_to_yaml()
            finally:
                self._set_setting(setting, False)
        elif setting in {
            "extract_full_package",
            "autobuild_paks",
            "remove_extracted_metadata",
            "force_load_dlls",
            "log_diff",
            "convert_yamls_to_json",
        } and hasattr(self, setting):
            delattr(self, setting)

    def construct_modsettings_xml(
        self,
        exec_path: str = "",
        working_dir: typing.Optional[QDir] = None,
        args: str = "",
        force_reparse_metadata: bool = False,
    ) -> bool:
        if (
            "bin/bg3" not in exec_path
            or not self._lslib_retriever.download_lslib_if_missing()
        ):
            return True
        active_mods = self.active_mods()
        progress = self.create_progress_window(
            "Generating modsettings.xml", len(active_mods)
        )
        threadpool = QThreadPool.globalInstance()
        if threadpool is None:
            return False
        metadata: dict[str, str] = {}

        def retrieve_mod_metadata_in_new_thread(mod: mobase.IModInterface):
            return lambda: metadata.update(
                self._pak_parser.get_metadata_for_files_in_mod(
                    mod, force_reparse_metadata
                )
            )

        for mod in active_mods:
            if progress.wasCanceled():
                qWarning("processing canceled by user")
                return False
            threadpool.start(QRunnable.create(retrieve_mod_metadata_in_new_thread(mod)))
        count = 0
        num_active_mods = len(active_mods)
        total_intervals_to_wait = (num_active_mods * 2) + 20
        while len(metadata.keys()) < num_active_mods:
            progress.setValue(len(metadata.keys()))
            QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
            count += 1
            if count == total_intervals_to_wait or progress.wasCanceled():
                remaining_mods = {mod.name() for mod in active_mods} - metadata.keys()
                qWarning(f"processing did not finish in time for: {remaining_mods}")
                progress.close()
                break
            QThread.msleep(100)
        progress.setValue(num_active_mods)
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
        progress.close()
        qInfo(f"writing mod load order to {self.modsettings_path}")
        self.modsettings_path.parent.mkdir(parents=True, exist_ok=True)
        self.modsettings_path.write_text(
            (
                self._mod_settings_xml_start
                + "".join(
                    metadata[mod.name()]
                    for mod in active_mods
                    if mod.name() in metadata
                )
                + self._mod_settings_xml_end
            )
        )
        qInfo(
            f"backing up generated file {self.modsettings_path} to {self.modsettings_backup}, "
            f"check the backup after the executable runs for differences with the file used by the game if you encounter issues"
        )
        shutil.copy(self.modsettings_path, self.modsettings_backup)
        return True

    def _convert_jsons_to_yaml(self):
        qInfo("converting all json files to yaml")
        active_mods = self.active_mods()
        progress = self.create_progress_window(
            "Converting all json files to yaml", len(active_mods) + 1
        )
        for mod in active_mods:
            _convert_jsons_in_dir_to_yaml(Path(mod.absolutePath()))
            progress.setValue(progress.value() + 1)
            QApplication.processEvents()
            if progress.wasCanceled():
                qWarning("conversion canceled by user")
                return
        _convert_jsons_in_dir_to_yaml(self.overwrite_path)
        progress.setValue(len(active_mods) + 1)
        QApplication.processEvents()
        progress.close()

    def on_mod_installed(self, mod: mobase.IModInterface) -> None:
        if self._lslib_retriever.download_lslib_if_missing():
            self._pak_parser.get_metadata_for_files_in_mod(mod, True)


def _convert_jsons_in_dir_to_yaml(path: Path):
    for file in list(path.rglob("*.json")):
        converted_path = file.parent / file.name.replace(".json", ".yaml")
        try:
            if not converted_path.exists() or os.path.getmtime(file) > os.path.getmtime(
                converted_path
            ):
                with open(file, "r") as json_file:
                    with open(converted_path, "w") as yaml_file:
                        yaml.dump(
                            json.load(json_file), yaml_file, indent=2, sort_keys=False
                        )
                qInfo(f"Converted {file} to YAML")
        except OSError as e:
            qWarning(f"Error accessing file {converted_path}: {e}")
