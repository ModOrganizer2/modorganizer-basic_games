import json
import os
from pathlib import Path

from PyQt6.QtCore import qInfo, qWarning
from PyQt6.QtWidgets import QApplication

from .bg3_tool_plugin import BG3ToolPlugin
from .icons import exchange


class BG3ToolConvertJsonsToYaml(BG3ToolPlugin):
    icon_bytes = exchange
    sub_name = "Convert JSONS to YAML"
    desc = "Convert all jsons in active mods to yaml immediately."

    def display(self):
        from ...game_baldursgate3 import BG3Game

        game_plugin = self._organizer.managedGame()
        if not isinstance(game_plugin, BG3Game):
            return
        utils = game_plugin.utils
        qInfo("converting all json files to yaml")
        active_mods = utils.active_mods()
        progress = utils.create_progress_window(
            "Converting all json files to yaml", len(active_mods) + 1
        )
        for mod in active_mods:
            _convert_jsons_in_dir_to_yaml(Path(mod.absolutePath()))
            progress.setValue(progress.value() + 1)
            QApplication.processEvents()
            if progress.wasCanceled():
                qWarning("conversion canceled by user")
                return
        _convert_jsons_in_dir_to_yaml(utils.overwrite_path)
        progress.setValue(len(active_mods) + 1)
        QApplication.processEvents()
        progress.close()


def _convert_jsons_in_dir_to_yaml(path: Path):
    import yaml

    for file in list(path.rglob("*.json")):
        converted_path = file.with_suffix(".yaml")
        try:
            if not converted_path.exists() or os.path.getmtime(file) > os.path.getmtime(
                converted_path
            ):
                data = json.loads(file.read_text(encoding="utf-8"))
                converted_path.write_text(
                    yaml.dump(data, indent=2, sort_keys=False, allow_unicode=True),
                    encoding="utf-8",
                )
                qInfo(f"Converted {file} to YAML")
        except (OSError, ValueError, yaml.YAMLError) as e:
            qWarning(f"Skipping {file}, conversion to YAML failed: {e}")
