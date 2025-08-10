import pathlib

import mobase


class BG3ScriptExtender(mobase.ScriptExtender):
    def __init__(self, game: mobase.IPluginGame):
        super().__init__()
        self._game = game

    def loaderName(self) -> str:
        return "DWrite.dll"

    def loaderPath(self) -> str:
        return str(
            pathlib.Path(self._game.gameDirectory().absolutePath())
            / "bin"
            / self.loaderName()
        )

    def isInstalled(self) -> bool:
        return pathlib.Path(self.loaderPath()).exists()

    def getExtenderVersion(self) -> str:
        return mobase.getFileVersion(self.loaderPath())

    def getArch(self) -> int:
        return 0x8664 if self.isInstalled() else 0x0

    def binaryName(self):
        return ""

    def pluginPath(self):
        return ""

    def savegameExtension(self):
        return ""
