# Misc Modules
import os
import logging
import fnmatch
from pathlib import Path

# PyQt6 Modules
from PyQt6.QtCore import QFileInfo, QDir  # type: ignore

# Mod Organizer 2 Modules
import mobase  # type: ignore
from mobase import IOrganizer, IPlugin  # type: ignore

from ..basic_features import BasicLocalSavegames, BasicModDataChecker, GlobPatterns
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
LogLevel = "Prod"  # Shitty workaround but whatever


class InzoiModDataChecker(BasicModDataChecker):
    def __init__(self):
        # Directly pass the GlobPatterns to BasicModDataChecker
        super().__init__(
            GlobPatterns(
                valid=[
                    # Validate a mod if the following files are in the root of the mod folder
                    "My3DPrinter",
                    "BlueClient",
                    "meta.ini",
                ],
                delete=[
                    # Delte useless crap that is included in the root of the mod folder
                    "*.txt",
                    "*.md",
                    "README",
                    "icon.png",
                    "license",
                    "LICENCE",
                    "manifest.json",
                    "*.dll.mdb",
                    "*.pdb",
                ],
                move={
                    # Correct DLLs at root of mod folder
                    "dwmapi.dll": "BlueClient/Binaries/Win64",
                    "dsound.dll": "BlueClient/Binaries/Win64",
                    # Correct PAK, UCAS or UTOC at root of mod folder
                    "*.pak": "BlueClient/Content/Paks/~mods/",
                    "*.utoc": "BlueClient/Content/Paks/~mods/",
                    "*.ucas": "BlueClient/Content/Paks/~mods/",
                },
            )
        )

    # Handles subfolder mod data validation
    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        # fix: single root folders get traversed by Simple Installer
        parent = filetree.parent()
        if parent is not None and self.dataLooksValid(parent) is self.FIXABLE:
            return self.FIXABLE

        # Call the parent class method to get the base check
        check_return = super().dataLooksValid(filetree)

        # Case: AFolder/BlueClient/... (needs flattening)
        if (
            check_return is self.INVALID
            and len(filetree) == 1
            and is_directory(wrapper := filetree[0])
            and any(
                is_directory(entry) and entry.name().lower() == "blueclient"
                for entry in wrapper
            )
        ):
            return self.FIXABLE

        # Case: A folder that only contains a single directory which has pak/utoc/ucas
        if (
            check_return is self.INVALID
            and len(filetree) == 1
            and is_directory(folder := filetree[0])
            and any(
                fnmatch.fnmatch(entry.name(), "*.pak")
                or fnmatch.fnmatch(entry.name(), "*.utoc")
                or fnmatch.fnmatch(entry.name(), "*.ucas")
                for entry in folder
            )
        ):
            return self.FIXABLE

        # Check for 3D printer mod folder with *.glb files
        for entry in filetree:
            if is_directory(entry) and entry.name():
                # Look for *.glb files in the directory
                glb_files = [
                    f
                    for f in entry
                    if f.isFile() and fnmatch.fnmatch(f.name(), "*.glb")
                ]
                if glb_files:
                    return self.FIXABLE

        return check_return

    # Fixes all incorecctly packaged mods
    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        filetree = super().fix(filetree)

        # Step 1: Flatten AFolder/BlueClient/... to just BlueClient/...
        if (
            len(filetree) == 1
            and is_directory(wrapper := filetree[0])
            and any(
                is_directory(entry) and entry.name().lower() == "blueclient"
                for entry in wrapper
            )
        ):
            for entry in wrapper:
                if is_directory(entry) and entry.name().lower() == "blueclient":
                    logger.info(
                        f"Flattening wrapper folder: {wrapper.name()} → {entry.name()}"
                    )
                    filetree.move(entry, entry.name())
                    filetree.remove(wrapper)
                    break

        # Step 2: Handle single-folder case with .pak/.utoc/.ucas
        if (
            self.dataLooksValid(filetree) is self.FIXABLE
            and len(filetree) > 0
            and is_directory(folder := filetree[0])
            and folder is not None
            and len(folder) > 0
        ):
            file_extensions = ["*.pak", "*.utoc", "*.ucas"]
            matched_files: list[str] = []
            files_to_move: list[mobase.IFileTreeEntry] = []

            all_files = [
                entry.name() for entry in folder if entry is not None and entry.isFile()
            ]
            logger.info(
                f"🧐 Checking for PAK,UTOC or UCAS files in folder: {folder.name()}"
            )
            logger.info(f"🗂️ Found files in folder: {', '.join(all_files)}")

            for entry in folder:
                if entry is not None and entry.isFile():
                    file_name = entry.name()

                    if LogLevel == "Debug":
                        logger.info(f"🧐 Checking file: {file_name}")

                    for ext in file_extensions:
                        if fnmatch.fnmatch(file_name, ext):
                            logger.info(f"🗂️ File matches: {file_name} (Matches {ext})")
                            files_to_move.append(entry)
                            matched_files.append(file_name)
                            break

            for file in files_to_move:
                filetree.move(file, "BlueClient/Content/Paks/~mods/")
                if LogLevel == "Debug":
                    logger.info(
                        f"✈️ Moved {file.name()} to BlueClient/Content/Paks/~mods/"
                    )

            if matched_files:
                logger.info(f"✈️ Moved files: {', '.join(matched_files)}")
            else:
                logger.info("👍 No matching files were moved.")

            if not any(entry.isFile() for entry in folder):
                logger.info(f"🧹 Removing empty folder: {folder.name()}")
                filetree.remove(folder)

        # Step 3: Handle 3D printer mod folder logic
        for entry in filetree:
            if entry is not None and is_directory(entry) and entry.name():
                all_files = [f for f in entry if f is not None and f.isFile()]

                if all_files:
                    folder_name = entry.name()
                    glb_files = [
                        f for f in all_files if f.name().lower().endswith(".glb")
                    ]

                    logger.info(
                        f"Found incorrectly formatted 🖨️ 3DPrinter mod folder: {folder_name}"
                    )  # ← log once per folder

                    # Rename folder to match .glb if applicable
                    if len(glb_files) == 1:
                        expected_name = Path(glb_files[0].name()).stem
                        if folder_name != expected_name:
                            logger.info(
                                f"Renaming 🖨️ 3DPrinter mod folder: {folder_name} → {expected_name}"
                            )
                            filetree.move(entry, expected_name)
                            folder_name = expected_name

                    logger.info(f"🛠️ Fixing 🖨️ 3DPrinter mod folder: {folder_name}")
                    target_dir = Path("My3DPrinter") / folder_name
                    target_dir.mkdir(parents=True, exist_ok=True)

                    for file in all_files:
                        if file is not None and file.isFile():
                            logger.info(f"✈️ Moving file: {file.name()} to {target_dir}")
                            filetree.move(file, str(target_dir / file.name()))

                    if not any(f is not None and f.isFile() for f in entry):
                        logger.info(f"🧹Removing empty folder: {folder_name}")
                        filetree.remove(entry)
                    break

        return filetree


class InzoiGame(BasicGame):
    Name = "inZOI Support Plugin"
    Author = "Frog"
    Version = "2.0.0"
    Description = "Adds inZOI support to Mod Organizer 2, includes handling for 3DPrinter Files, Includes handling for UE4SS dwmapi.dll injection."

    GameName = "inZOI"
    GameShortName = "inzoi"
    GameBinary = "inZOI.exe"
    GameNexusId = 7480
    GameSteamId = 2456740

    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = "%DOCUMENTS%/inZOI"
    GameSavesDirectory = "%GAME_DOCUMENTS%/SaveGames"

    def init(self, organizer: IOrganizer) -> bool:
        if not super().init(organizer):
            return False

        self._register_feature(InzoiModDataChecker())
        organizer.onAboutToRun(self._onAboutToRun)
        organizer.onFinishedRun(self._onFinishedRun)
        organizer.onPluginSettingChanged(self._settings_change_callback)
        # Not really doing anything with this right now.
        # self._register_feature(BasicLocalSavegames(self.savesDirectory()))
        self._organizer = organizer
        modList = self._organizer.modList()
        modList.onModStateChanged(self.mod_state_changed)

        return True

    @property
    def deploy_3dprinter(self) -> bool:
        return self._organizer.pluginSetting(
            self.name(), "Deploy 3DPrinter mods on launch"
        )

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "inZOI",
                QFileInfo(
                    self.gameDirectory(),
                    self.binaryName(),
                ),
            ),
            # This is probably wrong but ¯\_(ツ)_/¯ it works so fuck it.
            mobase.ExecutableInfo(
                "inZOI Shipping Exe",
                QFileInfo(
                    self.gameDirectory(),
                    "inZOI-Win64-Shipping.exe",
                ),
            ),
        ]

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        try:
            efls = super().executableForcedLoads()
        except AttributeError:
            efls = []

        libraries = ["BlueClient/Binaries/Win64/dwmapi.dll"]

        # Only apply the forced load settings to "inZOI-Win64-Shipping.exe"
        for exe in self.executables():
            if exe.binary().fileName() == "inZOI-Win64-Shipping.exe":
                efls.extend(
                    mobase.ExecutableForcedLoadSetting(
                        exe.binary().fileName(), lib
                    ).withEnabled(True)
                    for lib in libraries
                )

        return efls

    def mod_state_changed(self, mod_states: dict[str, mobase.ModState]):
        printer_base = (
            Path(self.documentsDirectory().absolutePath())
            / "AIGenerated"
            / "My3DPrinter"
        )
        printer_base.mkdir(parents=True, exist_ok=True)

        for mod_name, state in mod_states.items():
            mod = self._organizer.modList().getMod(mod_name)
            if not mod:
                logger.warning(f"🧐 Mod not found: {mod_name}")
                continue

            mod_path = Path(mod.absolutePath())
            source_dir = mod_path / "My3DPrinter"
            actual_mod_folder = next(source_dir.glob("*"), None)
            is_printer_mod = actual_mod_folder and actual_mod_folder.is_dir()

            if state & mobase.ModState.ACTIVE:
                logger.info(f"✔️ {mod_name} enabled.")
                if is_printer_mod:
                    logger.info(f"🖨️ {mod_name} is a 3DPrinter mod!")
                    if self.deploy_3dprinter:
                        continue  # just log, no symlink now
                    target_dir = printer_base / actual_mod_folder.name
                    if target_dir.exists():
                        logger.info(
                            f"Removing old 🔗 symlink or directory at: {target_dir}"
                        )
                        if target_dir.is_symlink():
                            target_dir.unlink()
                    try:
                        logger.info(
                            f"Creating 🔗 symlink: {target_dir} → {actual_mod_folder}"
                        )
                        os.symlink(
                            actual_mod_folder, target_dir, target_is_directory=True
                        )
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to create 🔗 symlink for {mod_name}: {e}"
                        )
            else:
                logger.info(f"➖ {mod_name} disabled.")
                if is_printer_mod:
                    logger.info(f"🖨️ {mod_name} is a 3DPrinter mod!")
                    if self.deploy_3dprinter:
                        continue  # just log, no unlink now
                    target_dir = printer_base / actual_mod_folder.name
                    if target_dir.exists():
                        try:
                            if target_dir.is_symlink():
                                target_dir.unlink()
                                logger.info(
                                    f"🧹 Removed 🖨️ printer 🔗 symlink: {target_dir} for {mod_name}"
                                )
                        except Exception as e:
                            logger.error(
                                f"❌ Failed to remove 🖨️ printer 🔗 symlink for {mod_name}: {e}"
                            )

    def AddSymlinksOnLaunch(self):
        mods_parent_path = Path(self._organizer.modsPath())
        modlist = self._organizer.modList().allModsByProfilePriority()

        for mod in modlist:
            if self._organizer.modList().state(mod) & mobase.ModState.ACTIVE:
                mod_path = mods_parent_path / mod
                for file_name in ["bitfix", "dsound.dll"]:
                    file_src = (
                        mod_path / "BlueClient" / "Binaries" / "Win64" / file_name
                    )
                    if file_src.exists():
                        file_dst = (
                            Path(self.gameDirectory().absolutePath())
                            / "BlueClient"
                            / "Binaries"
                            / "Win64"
                            / file_name
                        )
                        if file_dst.exists():
                            logger.info(
                                f"Checking existing 🔗symlink or file: {file_dst}"
                            )
                            # Only remove if it's a symlink
                            if file_dst.is_symlink():
                                logger.info(
                                    f"🧹 Removing existing 🔗symlink: {file_dst}"
                                )
                                file_dst.unlink()
                            else:
                                logger.info(
                                    f"Skipping removal of file or directory: {file_dst}"
                                )
                        try:
                            logger.info(f"Creating 🔗symlink: {file_dst} → {file_src}")
                            os.symlink(file_src, file_dst, target_is_directory=False)
                        except Exception as e:
                            logger.error(
                                f"❌Failed to create 🔗symlink for {file_src}: {e}"
                            )

    def RemoveSymlinksOnExit(self):
        modlist = self._organizer.modList().allModsByProfilePriority()

        for mod in modlist:
            if self._organizer.modList().state(mod) & mobase.ModState.ACTIVE:
                for file_name in ["bitfix", "dsound.dll"]:
                    file_dst = (
                        Path(self.gameDirectory().absolutePath())
                        / "BlueClient"
                        / "Binaries"
                        / "Win64"
                        / file_name
                    )
                    if file_dst.is_symlink():
                        logger.info(f"🧹 Removing 🔗symlink: {file_dst}")
                        file_dst.unlink()

    def Add3DPrinterSymlinksOnLaunch(self):
        printer_base = (
            Path(self.documentsDirectory().absolutePath())
            / "AIGenerated"
            / "My3DPrinter"
        )
        printer_base.mkdir(parents=True, exist_ok=True)

        modlist = self._organizer.modList().allModsByProfilePriority()
        for mod_name in modlist:
            if self._organizer.modList().state(mod_name) & mobase.ModState.ACTIVE:
                mod = self._organizer.modList().getMod(mod_name)
                if not mod:
                    continue

                mod_path = Path(mod.absolutePath())
                source_dir = mod_path / "My3DPrinter"
                actual_mod_folder = next(source_dir.glob("*"), None)

                if actual_mod_folder and actual_mod_folder.is_dir():
                    target_dir = printer_base / actual_mod_folder.name
                    if target_dir.exists() and target_dir.is_symlink():
                        target_dir.unlink()
                    try:
                        os.symlink(
                            actual_mod_folder, target_dir, target_is_directory=True
                        )
                        logger.info(
                            f"Created 3DPrinter 🔗symlink: {target_dir} → {actual_mod_folder}"
                        )
                    except Exception as e:
                        logger.error(f"❌ Failed to create 3DPrinter symlink: {e}")

    def Remove3DPrinterSymlinksOnExit(self):
        printer_base = (
            Path(self.documentsDirectory().absolutePath())
            / "AIGenerated"
            / "My3DPrinter"
        )

        if printer_base.exists():
            for child in printer_base.iterdir():
                if child.is_symlink():
                    try:
                        child.unlink()
                        logger.info(f"🧹 Removed 3DPrinter 🔗symlink: {child}")
                    except Exception as e:
                        logger.error(f"❌ Failed to remove 3DPrinter symlink: {e}")

    def _onAboutToRun(self, path: str):
        logger.info(f"🐸 Application about to run: {path}")
        self.AddSymlinksOnLaunch()
        if self.deploy_3dprinter:
            self.Add3DPrinterSymlinksOnLaunch()
        return True

    def _onFinishedRun(self, path: str, exit_code: int):
        logger.info(f"🐸 Application finished running: {path}, exit code: {exit_code}")
        self.RemoveSymlinksOnExit()  # Clean up symlinks when game finishes
        if self.deploy_3dprinter:
            self.Remove3DPrinterSymlinksOnExit()
        return True

    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting(
                "Deploy 3DPrinter mods on launch",
                (
                    "Deploys 3DPrinter mods on launch instead of when the mod is enabled."
                ),
                default_value=False,
            )
        ]

    def _settings_change_callback(
        self,
        plugin_name: str,
        setting: str,
        old: mobase.MoVariant,
        new: mobase.MoVariant,
    ):
        if plugin_name == self.name() and setting == "Deploy 3DPrinter mods on launch":
            # self.deploy_3dprinter = bool(new)
            if LogLevel == "Debug":
                logger.info(
                    f"🐸 Plugin setting changed: {setting} = {new}, old value: {old}"
                )


def createPlugin() -> IPlugin:
    return InzoiGame()
