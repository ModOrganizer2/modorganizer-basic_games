from ..basic_game import BasicGame

import mobase
import sys
import psutil
import threading
import time


class MassEffectLegendaryGame(BasicGame):

    Name = "Mass Effect Legendary Edition Support Plugin"
    Author = "LostDragonist"
    Version = "1.0.0"

    GameName = "Mass Effect: Legendary Edition"
    GameShortName = "masseffectlegendaryedition"
    GameBinary = "Game/Launcher/MassEffectLauncher.exe"
    GameLauncher = "MassEffectLauncher.exe"
    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = (
        "%USERPROFILE%/Documents/BioWare/Mass Effect Legendary Edition/Save"
    )
    GameSaveExtension = "pcsav"
    GameSteamId = 1328670

    def init(self, organizer: mobase.IOrganizer) -> bool:
        if not super().init(organizer):
            return False
        if not self._organizer.onAboutToRun(lambda appName: self._spawnOriginWatcher()):
            print("Failed to register onAboutToRun callback!", file=sys.stderr)
            return False
        if not self._organizer.onFinishedRun(
            lambda appName, result: self._stopOriginWatcher()
        ):
            print("Failed to register onFinishedRun callback!", file=sys.stderr)
            return False
        return True

    def _spawnOriginWatcher(self) -> bool:
        _killOrigin()
        self.worker = threading.Thread(target=_workerFunc)
        self.worker.start()
        return True

    def _stopOriginWatcher(self) -> None:
        self.worker.join(10.0)


def _killOrigin():
    # Kill Origin if it's alive
    for proc in psutil.process_iter():
        if proc.name().lower() == "origin.exe":
            proc.kill()


def _workerFunc():
    gameAliveCount = 300  # Large number to allow Origin and the game to launch
    keepGoing = True
    while keepGoing:
        gameAlive = False
        # See if the game is alive
        for proc in psutil.process_iter():
            if proc.name().lower() in [
                "masseffectlauncher.exe",
                "masseffect1.exe",
                "masseffect2.exe",
                "masseffect3.exe",
            ]:
                gameAlive = True
                break
        if gameAlive:
            # Game is alive, sleep and keep monitoring
            time.sleep(1)
            gameAliveCount = 10
        else:
            gameAliveCount -= 1
            if gameAliveCount <= 0:
                _killOrigin()
                # Exit the thread
                keepGoing = False
