import json
from pathlib import Path

import mobase
from PyQt6.QtCore import QDateTime, QDir, QLocale, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFormLayout,
    QLabel,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
)
from ..basic_game import BasicGame


class BaSSaveGame(BasicGameSaveGame):
    def __init__(self, filepath: Path):
        super().__init__(filepath)
        with open(self._filepath, "rb") as save:
            save_data = json.load(save)
        self._gameMode: str = save_data["gameModeId"]
        self._gender = (
            "Male" if save_data["creatureId"] == "PlayerDefaultMale" else "Female"
        )
        self._ethnicity: str = save_data["ethnicGroupId"]
        h, m, s = save_data["playTime"].split(":")
        self._elapsed = (int(h), int(m), float(s))
        f_stat = self._filepath.stat()
        self._created = f_stat.st_ctime
        self._modified = f_stat.st_mtime

    def getName(self) -> str:
        return f"{self.getPlayerSlug()} - {self._gameMode}"

    def getCreationTime(self) -> QDateTime:
        return QDateTime.fromSecsSinceEpoch(int(self._created))

    def getModifiedTime(self) -> QDateTime:
        return QDateTime.fromSecsSinceEpoch(int(self._modified))

    def getPlayerSlug(self) -> str:
        return f"{self._gender} {self._ethnicity}"

    def getElapsed(self) -> str:
        return (
            f"{self._elapsed[0]} hours, "
            f"{self._elapsed[1]} minutes, "
            f"{int(self._elapsed[2])} seconds"
        )

    def getGameMode(self) -> str:
        return self._gameMode


class BaSSaveGameInfoWidget(mobase.ISaveGameInfoWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.resize(400, 125)
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self._verticalLayout = QVBoxLayout()
        self._verticalLayout.setObjectName("verticalLayout")
        self._formLayout = QFormLayout()
        self._formLayout.setObjectName("formLayout")
        self._formLayout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        self._label = QLabel()
        self._label.setObjectName("label")
        font = QFont()
        font.setItalic(True)
        self._label.setFont(font)
        self._label.setText("Character")

        self._formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self._label)

        self._label_2 = QLabel()
        self._label_2.setObjectName("label_2")
        self._label_2.setFont(font)
        self._label_2.setText("Game Mode")

        self._formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self._label_2)

        self._label_3 = QLabel()
        self._label_3.setObjectName("label_4")
        self._label_3.setFont(font)
        self._label_3.setText("Created At")

        self._formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self._label_3)

        self._label_4 = QLabel()
        self._label_4.setObjectName("label_4")
        self._label_4.setFont(font)
        self._label_4.setText("Last Saved")

        self._formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self._label_4)

        self._label_5 = QLabel()
        self._label_5.setObjectName("label_3")
        self._label_5.setFont(font)
        self._label_5.setText("Session Duration")

        self._formLayout.setWidget(4, QFormLayout.ItemRole.LabelRole, self._label_5)

        font1 = QFont()
        font1.setBold(True)

        self._characterLabel = QLabel()
        self._characterLabel.setObjectName("characterLabel")
        self._characterLabel.setFont(font1)
        self._characterLabel.setText("")

        self._formLayout.setWidget(
            0, QFormLayout.ItemRole.FieldRole, self._characterLabel
        )

        self._gameModeLabel = QLabel()
        self._gameModeLabel.setObjectName("gameModeLabel")
        self._gameModeLabel.setFont(font1)
        self._gameModeLabel.setText("")

        self._formLayout.setWidget(
            1, QFormLayout.ItemRole.FieldRole, self._gameModeLabel
        )

        self._dateLabel = QLabel()
        self._dateLabel.setObjectName("dateLabel")
        self._dateLabel.setFont(font1)
        self._dateLabel.setText("")

        self._formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self._dateLabel)

        self._sessionLabel = QLabel()
        self._sessionLabel.setObjectName("sessionLabel")
        self._sessionLabel.setFont(font1)
        self._sessionLabel.setText("")

        self._formLayout.setWidget(
            3, QFormLayout.ItemRole.FieldRole, self._sessionLabel
        )

        self._elapsedTimeLabel = QLabel()
        self._elapsedTimeLabel.setObjectName("elapsedTimeLabel")
        self._elapsedTimeLabel.setFont(font1)
        self._elapsedTimeLabel.setText("")

        self._formLayout.setWidget(
            4, QFormLayout.ItemRole.FieldRole, self._elapsedTimeLabel
        )

        self._verticalLayout.addLayout(self._formLayout)

        self.setLayout(self._verticalLayout)
        self.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.BypassGraphicsProxyWidget
        )
        style = self.style()
        if style is not None:
            self.setWindowOpacity(
                style.styleHint(QStyle.StyleHint.SH_ToolTipLabel_Opacity) / 255.0
            )

    def setSave(self, save: mobase.ISaveGame):
        assert isinstance(save, BaSSaveGame)
        self._characterLabel.setText(save.getPlayerSlug())
        self._gameModeLabel.setText(save.getGameMode())
        t = save.getCreationTime().toLocalTime()
        self._dateLabel.setText(
            QLocale.system().toString(t.date(), QLocale.FormatType.ShortFormat)
            + " "
            + QLocale.system().toString(t.time())
        )
        s = save.getModifiedTime().toLocalTime()
        self._sessionLabel.setText(
            QLocale.system().toString(s.date(), QLocale.FormatType.ShortFormat)
            + " "
            + QLocale.system().toString(s.time())
        )
        self._elapsedTimeLabel.setText(save.getElapsed())
        self.resize(0, 125)


class BaSSaveGameInfo(BasicGameSaveGameInfo):
    def getSaveGameWidget(self, parent: QWidget | None = None):
        return BaSSaveGameInfoWidget(parent)


class BaSGame(BasicGame):
    Name = "Blade & Sorcery Plugin"
    Author = "R3z Shark & Silarn"
    Version = "0.5.0"

    GameName = "Blade & Sorcery"
    GameShortName = "bladeandsorcery"
    GameBinary = "BladeAndSorcery.exe"
    GameDataPath = r"BladeAndSorcery_Data\\StreamingAssets\\Mods"
    GameDocumentsDirectory = "%DOCUMENTS%/My Games/BladeAndSorcery"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Saves/Default"
    GameSaveExtension = "chr"
    GameSteamId = 629730
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Blade-&-Sorcery"
    )

    def init(self, organizer: mobase.IOrganizer) -> bool:
        BasicGame.init(self, organizer)
        self._featureMap[mobase.SaveGameInfo] = BaSSaveGameInfo()
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            BaSSaveGame(path) for path in Path(folder.absolutePath()).glob(f"*.{ext}")
        ]
