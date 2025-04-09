# Misc Modules
import os
import shutil
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
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.DEBUG)  # Fuck it's annoying this doesn't work, something is reconfiguring the root logger and removing debug
# logger.addHandler(console_handler) # well debug statements show but so do duplicate logs.
LogLevel = "NONE"  # Shitty workaround but whatever


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

        # A single unknown folder with a pak or utoc file in is to be moved
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

        return check_return

    # Corrects the mod data structure for specfic file types
    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        filetree = super().fix(filetree)

        # Check if the filetree looks valid and contains at least one item
        if (
            self.dataLooksValid(filetree) is self.FIXABLE
            and len(filetree) > 0  # Ensure there's at least one entry in the filetree
            and is_directory(folder := filetree[0])  # Ensure folder is a directory
            and folder is not None  # Ensure folder is not None
            and len(folder) > 0  # Ensure the folder has files before proceeding
        ):
            # List of extensions to check, can be extended dynamically
            file_extensions = ["*.pak", "*.utoc", "*.ucas"]  # Add more as needed
            matched_files = []  # To track matched files for debugging
            files_to_move = []  # To store files that need to be moved

            # Debugging: Output all files in the folder to ensure everything is being found
            all_files = [
                entry.name() for entry in folder if entry is not None and entry.isFile()
            ]
            logger.info(
                f"Found files in folder: {', '.join(all_files)}"
            )  # Log all files in the folder

            # Collect files that need to be moved
            for entry in folder:
                if (
                    entry is not None and entry.isFile()
                ):  # Ensure entry is valid and is a file
                    file_name = entry.name()

                    # Debug: Check if we are even entering the loop for each file
                    if LogLevel == "Debug":
                        logger.info(f"Checking file: {file_name}")

                    # Check for matches with file extensions
                    for ext in file_extensions:
                        if fnmatch.fnmatch(file_name, ext):
                            logger.info(
                                f"File matches: {file_name} (Matches {ext})"
                            )  # Debug which file extension matches
                            files_to_move.append(
                                entry
                            )  # Add to the list of files to move
                            matched_files.append(file_name)  # Track matched files
                            break  # Break after the first match to prevent unnecessary checks

            # Move the files after the loop to ensure no file is skipped
            for file in files_to_move:
                filetree.move(file, "BlueClient/Content/Paks/~mods/")
                if LogLevel == "Debug":
                    logger.info(
                        f"Moved {file.name()} to BlueClient/Content/Paks/~mods/"
                    )

            # Log moved files
            if matched_files:
                logger.info(f"Moved files: {', '.join(matched_files)}")
            else:
                logger.warning("No matching files were moved.")

            # After moving the files, check if the folder is empty and delete it if so
            if not any(
                entry.isFile() for entry in folder
            ):  # Check if folder still contains files
                if LogLevel == "Debug":
                    logger.info(f"Removing empty folder: {folder}")
                filetree.remove(folder)

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
        # Not really doing anything with this right now.
        self._register_feature(BasicLocalSavegames(self.savesDirectory()))
        self._organizer = organizer
        modList = self._organizer.modList()
        modList.onModStateChanged(self.mod_state_changed)

        return True

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
                logger.warning(f"🧐Mod not found: {mod_name}")
                continue

            mod_path = Path(mod.absolutePath())
            source_dir = mod_path / "My3DPrinter"

            # Get the actual folder inside My3DPrinter (e.g., 0AE242564857369BAF5F84BC366FDB64)
            actual_mod_folder = next(source_dir.glob("*"), None)

            # Check if this is a 3DPrinter mod
            is_printer_mod = actual_mod_folder and actual_mod_folder.is_dir()

            # Handle enabling and disabling of the mod
            if state & mobase.ModState.ACTIVE:
                logger.info(f"✔️{mod_name} enabled.")
                if is_printer_mod:
                    logger.info(f"🖨️ {mod_name} is a 3DPrinter mod!")
                    target_dir = (
                        printer_base / actual_mod_folder.name
                    )  # Use the actual folder name for the symlink
                    if target_dir.exists():
                        logger.info(
                            f"Removing old 🔗symlink or directory at: {target_dir}"
                        )
                        if target_dir.is_symlink() or target_dir.is_file():
                            target_dir.unlink()
                        elif target_dir.is_dir():
                            shutil.rmtree(target_dir)
                    try:
                        logger.info(
                            f"Creating 🔗symlink: {target_dir} → {actual_mod_folder}"
                        )
                        os.symlink(
                            actual_mod_folder, target_dir, target_is_directory=True
                        )
                    except Exception as e:
                        logger.error(
                            f"❌Failed to create 🔗symlink for {mod_name}: {e}"
                        )
            else:
                logger.info(f"➖{mod_name} disabled.")
                if is_printer_mod:
                    logger.info(f"🖨️ {mod_name} is a 3DPrinter mod!")
                    target_dir = printer_base / actual_mod_folder.name
                    if target_dir.exists():
                        try:
                            if target_dir.is_symlink() or target_dir.is_file():
                                target_dir.unlink()
                            elif target_dir.is_dir():
                                shutil.rmtree(target_dir)
                            logger.info(
                                f"Removed 🖨️ printer 🔗symlink: {target_dir} for {mod_name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"❌Failed to remove 🖨️ printer 🔗symlink for {mod_name}: {e}"
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
                                logger.info(f"Removing existing 🔗symlink: {file_dst}")
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
        mods_parent_path = Path(self._organizer.modsPath())
        modlist = self._organizer.modList().allModsByProfilePriority()

        for mod in modlist:
            if self._organizer.modList().state(mod) & mobase.ModState.ACTIVE:
                mod_path = mods_parent_path / mod
                for file_name in ["bitfix", "dsound.dll"]:
                    file_dst = (
                        Path(self.gameDirectory().absolutePath())
                        / "BlueClient"
                        / "Binaries"
                        / "Win64"
                        / file_name
                    )
                    if file_dst.is_symlink():
                        logger.info(f"Removing 🔗symlink: {file_dst}")
                        file_dst.unlink()

    def _onAboutToRun(self, path: str):
        logger.info(f"🐸 Application about to run: {path}")
        self.AddSymlinksOnLaunch()
        return True

    def _onFinishedRun(self, path: str, exit_code: int):
        logger.info(f"🐸 Application finished running: {path}, exit code: {exit_code}")
        self.RemoveSymlinksOnExit()  # Clean up symlinks when game finishes
        return True


def createPlugin() -> IPlugin:
    return InzoiGame()
