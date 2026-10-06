# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

import mobase

from ..installer import SpaceRangersHDInstaller
from ..tool_bugreport import BugReportTool
from ..tool_migrate import MigrateTool


def createPlugins() -> list[mobase.IPlugin]:
    # The installer is a mobase.IPluginInstallerSimple; the tools are
    # mobase.IPluginTool. The basic_games loader registers every returned
    # mobase.IPlugin with MO2's plugincontainer, which picks installers out via
    # qobject_cast<IPluginInstaller*>.
    return [SpaceRangersHDInstaller(), MigrateTool(), BugReportTool()]
