from .bg3_tool_plugin import BG3ToolPlugin


class BG3ToolReparsePakMetadata(BG3ToolPlugin):
    icon_file = "ui-refresh.ico"
    sub_name = "Reparse Pak Metadata"
    desc = "Force reparsing mod metadata immediately."

    def display(self):
        from ...game_baldursgate3 import BG3Game

        game_plugin = self._organizer.managedGame()
        if isinstance(game_plugin, BG3Game):
            game_plugin.utils.construct_modsettings_xml(
                exec_path="bin/bg3", force_reparse_metadata=True
            )
