import hashlib
import json
import shutil
import traceback
import urllib.request
import zipfile
from functools import cached_property
from pathlib import Path

from PyQt6.QtCore import qDebug, qWarning
from PyQt6.QtWidgets import QApplication, QMessageBox

from . import bg3_utils

_TIMEOUT = 30


class LSLibRetriever:
    def __init__(self, utils: bg3_utils.BG3Utils):
        self._utils = utils

    @cached_property
    def _needed_lslib_files(self):
        return {
            self._utils.tools_dir / x
            for x in {
                "CommandLineArgumentsParser.dll",
                "Divine.dll",
                "Divine.dll.config",
                "Divine.exe",
                "Divine.runtimeconfig.json",
            }
        }

    def download_lslib_if_missing(self, force: bool = False) -> bool:
        if not force and all(x.exists() for x in self._needed_lslib_files):
            return True
        old_archives = sorted(self._utils.tools_dir.glob("*.zip"))
        try:
            self._utils.tools_dir.mkdir(exist_ok=True, parents=True)
            with urllib.request.urlopen(
                "https://api.github.com/repos/Norbyte/lslib/releases/latest",
                timeout=_TIMEOUT,
            ) as response:
                assets = json.loads(response.read().decode("utf-8"))["assets"]
            asset = next(a for a in assets if a["name"].endswith(".zip"))
            zip_path = self._utils.tools_dir / asset["name"]
            if zip_path.exists():
                new_msg = QMessageBox(self._utils.main_window)
                new_msg.setIcon(QMessageBox.Icon.Information)
                new_msg.setText(
                    self._utils.tr("Latest version of LSLib already downloaded!")
                )
                new_msg.exec()
                return self._extract(zip_path)
            msg_box = QMessageBox(self._utils.main_window)
            msg_box.setWindowTitle(
                self._utils.tr("Baldur's Gate 3 Plugin - Missing dependencies")
            )
            if old_archives:
                msg_box.setText(self._utils.tr("LSLib update available."))
            else:
                msg_box.setText(
                    self._utils.tr(
                        "LSLib tools are missing.\nThese are necessary for the plugin to create the load order file for BG3."
                    )
                )
            msg_box.addButton(
                self._utils.tr("Download"), QMessageBox.ButtonRole.DestructiveRole
            )
            exit_btn = msg_box.addButton(
                self._utils.tr("Exit"), QMessageBox.ButtonRole.ActionRole
            )
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.exec()
            if msg_box.clickedButton() == exit_btn:
                if old_archives:
                    return self._extract(old_archives[-1])
                err = QMessageBox(self._utils.main_window)
                err.setIcon(QMessageBox.Icon.Critical)
                err.setText(
                    "LSLib tools are required for the proper generation of the modsettings.xml file, file will not be generated"
                )
                err.exec()
                return False
            progress = self._utils.create_progress_window(
                "Downloading LSLib", asset["size"], cancelable=False
            )
            digest = hashlib.sha256()
            part_path = zip_path.with_suffix(".part")
            try:
                with (
                    urllib.request.urlopen(
                        asset["browser_download_url"], timeout=_TIMEOUT
                    ) as src,
                    part_path.open("wb") as dst,
                ):
                    while chunk := src.read(1 << 16):
                        dst.write(chunk)
                        digest.update(chunk)
                        progress.setValue(progress.value() + len(chunk))
                        QApplication.processEvents()
            finally:
                progress.close()
            expected = asset.get("digest") or ""
            if expected and expected != f"sha256:{digest.hexdigest()}":
                part_path.unlink()
                raise ValueError(
                    f"{asset['name']} digest mismatch, expected {expected}"
                )
            part_path.replace(zip_path)
            for archive in old_archives:
                archive.unlink()
        except Exception:
            qDebug(f"Download failed: {traceback.format_exc()}")
            err = QMessageBox(self._utils.main_window)
            err.setIcon(QMessageBox.Icon.Critical)
            err.setText(
                self._utils.tr(
                    f"Failed to download LSLib tools:\n{traceback.format_exc()}"
                )
            )
            err.exec()
            return False
        return self._extract(zip_path)

    def _extract(self, zip_path: Path) -> bool:
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                names = [
                    n
                    for n in zip_ref.namelist()
                    if n.startswith("Packed/Tools/") and not n.endswith("/")
                ]
                qDebug(f"found files: {','.join(names)}")
                progress = self._utils.create_progress_window(
                    "Extracting LSLib", len(names), msg="Extracting LSLib files..."
                )
                try:
                    for name in names:
                        target = self._utils.tools_dir / Path(name).relative_to(
                            "Packed/Tools"
                        )
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zip_ref.open(name) as src, target.open("wb") as dst:
                            shutil.copyfileobj(src, dst)
                        progress.setValue(progress.value() + 1)
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            qWarning("processing canceled by user")
                            return False
                finally:
                    progress.close()
        except Exception:
            qDebug(f"Extraction failed: {traceback.format_exc()}")
            err = QMessageBox(self._utils.main_window)
            err.setIcon(QMessageBox.Icon.Critical)
            err.setText(
                self._utils.tr(
                    f"Failed to extract LSLib tools:\n{traceback.format_exc()}"
                )
            )
            err.exec()
            return False
        return True
