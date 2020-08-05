# Mod Organizer 2 - Simple Games Plugin (Modified for The Witcher 3)
**!!!DISCLAIMER THIS IS NOT THE OFFICIAL META PLUGIN I JUST USED IT TO AND TWEAKED THE WITCHER 3 GAME PLUGIN OF IT TO BETTER FIT THE NEEDS OF A WABBAJACK INSTALLER!!!**

## How to install?

Download [the archive](https://github.com/ModOrganizer2/modorganizer-basic_games/archive/master.zip)
and extract it directly into your MO2 `plugins` folder.

**Important:** Extract the *folder* in your `plugins` folder, not the individual files. Your
`plugins` folder should look like this:

```
dlls/
plugins/
  data/
  modorganizer-basic_games-master/
    games/
      __init__.py
      ...
    __init__.py
    basic_game.py
    ...
  bsa_extractor.dll
  ...
ModOrganizer.exe
```

You can rename `modorganizer-basic_games-master` to whatever you want (e.g., `basic_games`).

**Note:** You can also clone this repository in your `plugins/` folder:
```
cd $MO2_PATH/plugins
git clone https://github.com/ModOrganizer2/modorganizer-basic_games basic_games
```

## Supported games

**Note this download only contains my version of the Witcher 3 Plugin.
If you want to use the other Witcher 3 plugin, you will have to download [this](https://github.com/ModOrganizer2/modorganizer-basic_games) version of the plugin.**

| Game | Author | File | Extras |
|------|--------|------|--------|
| [Dark Messiah of Might & Magic](https://store.steampowered.com/app/2100/Dark_Messiah_of_Might__Magic/) | Holt59 | [game_darkmessiah[...].py](games/game_darkmessiahofmightandmagic.py) | <ul><li>steam detection</li><li>save game preview</li></ul> |
| [Darkest Dungeon](https://store.steampowered.com/app/262060/Darkest_Dungeon/) | [erri120](https://github.com/erri120) | [game_darkestdungeon.py](games/game_darkestdungeon.py) | <ul><li>steam detection</li></ul> |
| [Dungeon Siege II](https://store.steampowered.com/app/39200/Dungeon_Siege_II/) | Holt59 | [game_dungeonsiege2.py](games/game_dungeonsiege2.py) | <ul><li>steam detection</li><li>mod data checker</li></ul> |
| [Mount & Blade II: Bannerlord](https://store.steampowered.com/app/261550/Mount__Blade_II_Bannerlord/) | Holt59 | | <ul><li>steam detection</li><li>mod data checker</li></ul> |
| [S.T.A.L.K.E.R. Anomaly](https://www.stalker-anomaly.com/) | [Qudix](https://github.com/Qudix) | [game_stalkeranomaly.py](games/game_stalkeranomaly.py) | |
| [Stardew Valley](https://store.steampowered.com/app/413150/Stardew_Valley/) | [Syer10](https://github.com/Syer10), Holt59 | [game_stardewvalley.py](games/game_stardewvalley.py) | <ul><li>steam detection</li><li>mod data checker</li></ul> |
| [The Witcher 3: Wild Hunt](https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/) | Holt59 | [game_witcher3.py](https://github.com/ModOrganizer2/modorganizer-basic_games/blob/master/games/game_witcher3.py) | <ul><li>steam detection</li><li>save game preview</li></ul> |
| [The Witcher 3: Wild Hunt](https://www.gog.com/game/the_witcher_3_wild_hunt_game_of_the_year_edition)| [Holt59](https://github.com/Holt59), [Luca/EzioTheDeadPoet](https://github.com/EzioTheDeadPoet) |[game_witcher3alt.py](games/game_witcher3alt.py)|<ul><li>steam\|GOG detection</li><li>profile specific config files support</li></ul>|

## How to add a new game?

I would recommend that you go to the orginal [main plugins github](https://github.com/ModOrganizer2/modorganizer-basic_games#how-to-add-a-new-game) and look it up and create a fork there, instead of using my fork, since mine is dedicated to my alternative Witcher 3 game plugin.
