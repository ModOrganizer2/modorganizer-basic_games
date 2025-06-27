# Mod Organizer 2 - Simple Games Plugin

Mod Organizer 2 meta-plugin to make creating game plugins easier and faster.

## Why?

In order to create a MO2 game plugin, one must implement the `IPluginGame` interface.
This interface was initially designed for Bethesda games such as the Elder Scrolls or
Fallout series and thus contains a lot of things that are irrelevant for most games.

The goal of this meta-plugin is to allow creating game plugins for "basic" games by
providing a very simple python class.

## How to install?

Basic games is included in Mod Organizer 2.4, if you want to use new game plugins that
have not been included in the release,
[download the latest archive](https://github.com/ModOrganizer2/modorganizer-basic_games/archive/master.zip)
and extract the files in the existing `basic_games` folder, overwriting existing files.

**Important:** Extract the *folder* in your `plugins` folder, not the individual files. Your
`plugins` folder should look like this:

```text
dlls/
plugins/
  data/
  basic_games/
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

You can rename `modorganizer-basic_games-xxx` to whatever you want (e.g., `basic_games`).

## Supported games

<!-- START: GAMES -->

| Game | Author | File | Extras |
|------|--------|------|--------|
| The Binding of Isaac: Rebirth — [STEAM](https://store.steampowered.com/app/250900/The_Binding_of_Isaac_Rebirth/) |[EzioTheDeadPoet](https://github.com/EzioTheDeadPoet)|[game_thebindingofisaacrebirth.py](games/game_thebindingofisaacrebirth.py)|<ul><li>profile specific ini file</li></ul>|
| Control — [STEAM](https://store.steampowered.com/app/870780/Control_Ultimate_Edition/) / [GOG](https://www.gog.com/game/control_ultimate_edition) / [EGS](https://www.epicgames.com/store/p/control) | [Zash](https://github.com/ZashIn) | [game_control.py](games/game_control.py) | |
| Darkest Dungeon — [GOG](https://www.gog.com/game/darkest_dungeon) / [STEAM](https://store.steampowered.com/app/262060/Darkest_Dungeon/) | [erri120](https://github.com/erri120) | [game_darkestdungeon.py](games/game_darkestdungeon.py) | <ul><li>save slot parsing</li><li>mod data checker</li></ul> |
| Dark Messiah of Might & Magic — [STEAM](https://store.steampowered.com/app/2100/Dark_Messiah_of_Might__Magic/) | [Holt59](https://github.com/holt59/) | [game_darkmessiahofmightandmagic.py](games/game_darkmessiahofmightandmagic.py) | <ul><li>save game preview</li></ul> |
| Dark Souls — [STEAM](https://store.steampowered.com/app/211420/DARK_SOULS_Prepare_To_Die_Edition/) | [Holt59](https://github.com/holt59/) | [game_darksouls.py](games/game_darkestdungeon.py) |  |
| Divinity: Original Sin (Classic) — [STEAM](https://store.steampowered.com/app/230230/Divinity_Original_Sin_Classic/) | [LostDragonist](https://github.com/LostDragonist/) | [game_divinityoriginalsin.py](games/game_divinityoriginalsin.py) | <ul><li>save game preview</li></ul> |
| Divinity: Original Sin (Enhanced Edition) — [STEAM](https://store.steampowered.com/app/373420/Divinity_Original_Sin__Enhanced_Edition/) | [LostDragonist](https://github.com/LostDragonist/) | [game_divinityoriginalsinee.py](games/game_divinityoriginalsinee.py) | <ul><li>save game preview</li><li>mod data checker</li></ul> |
| Dragon's Dogma: Dark Arisen — [GOG](https://www.gog.com/game/dragons_dogma_dark_arisen) / [STEAM](https://store.steampowered.com/app/367500/Dragons_Dogma_Dark_Arisen/) | [EzioTheDeadPoet](https://github.com/EzioTheDeadPoet) | [game_dragonsdogmadarkarisen.py](games/game_dragonsdogmadarkarisen.py) | |
| Dungeon Siege II — [GOG](https://www.gog.com/game/dungeon_siege_collection) / [STEAM](https://store.steampowered.com/app/39200/Dungeon_Siege_II/) | [Holt59](https://github.com/holt59/) | [game_dungeonsiege2.py](games/game_dungeonsiege2.py) | <ul><li>mod data checker</li></ul> |
| Kingdom Come: Deliverance — [GOG](https://www.gog.com/game/kingdom_come_deliverance) / [STEAM](https://store.steampowered.com/app/379430/Kingdom_Come_Deliverance/) / [Epic](https://store.epicgames.com/p/kingdom-come-deliverance) | [Silencer711](https://github.com/Silencer711) | [game_kingdomcomedeliverance.py](games/game_kingdomcomedeliverance.py) | <ul><li>profile specific cfg files</li></ul>|
| METAL GEAR SOLID 2: Sons of Liberty — [STEAM](https://store.steampowered.com/app/2131640/METAL_GEAR_SOLID_2_Sons_of_Liberty__Master_Collection_Version/)|[AkiraJkr](https://github.com/AkiraJkr)|[game_metalgearsolid2mc.py](games/game_metalgearsolid2mc.py)| |
| METAL GEAR SOLID 3: Snake Eater — [STEAM](https://store.steampowered.com/app/2131650/METAL_GEAR_SOLID_3_Snake_Eater__Master_Collection_Version/)|[AkiraJkr](https://github.com/AkiraJkr)|[game_metalgearsolid3mc.py](games/game_metalgearsolid3mc.py)| |
| Mirror's Edge — [GOG](https://www.gog.com/game/mirrors_edge) / [STEAM](https://store.steampowered.com/app/17410/Mirrors_Edge)|[EzioTheDeadPoet](https://eziothedeadpoet.github.io/AboutMe/)|[game_mirrorsedge.py](games/game_mirrorsedge.py)| |
| Mount & Blade II: Bannerlord — [GOG](https://www.gog.com/game/mount_blade_ii_bannerlord) / [STEAM](https://store.steampowered.com/app/261550/Mount__Blade_II_Bannerlord/) | [Holt59](https://github.com/holt59/) | [game_mountandblade2.py](games/game_mountandblade2.py) | <ul><li>mod data checker</li></ul> |
| Need for Speed: High Stakes | [uwx](https://github.com/uwx) | [game_nfshs.py](games/game_nfshs.py) | |
| No Man's Sky - [GOG](https://www.gog.com/game/no_mans_sky) / [Steam](https://store.steampowered.com/app/275850/No_Mans_Sky/)|[EzioTheDeadPoet](https://eziothedeadpoet.github.io/AboutMe/)|[game_nomanssky.py](games/game_nomanssky.py)| |
| S.T.A.L.K.E.R. Anomaly — [MOD](https://www.stalker-anomaly.com/) | [Qudix](https://github.com/Qudix) | [game_stalkeranomaly.py](games/game_stalkeranomaly.py) | <ul><li>mod data checker</li></ul> |
| Stardew Valley — [GOG](https://www.gog.com/game/stardew_valley) / [STEAM](https://store.steampowered.com/app/413150/Stardew_Valley/) | [Syer10](https://github.com/Syer10), [Holt59](https://github.com/holt59/) | [game_stardewvalley.py](games/game_stardewvalley.py) | <ul><li>mod data checker</li></ul> |
| STAR WARS™ Empire at War: Gold Pack - [GOG](https://www.gog.com/game/star_wars_empire_at_war_gold_pack) / [STEAM](https://store.steampowered.com/app/32470/) | [erri120](https://github.com/erri120) | <ul><li>Empire at War: [game_starwars-empire-at-war.py](games/game_starwars-empire-at-war.py)</li><li>Force of Corruption: [game_starwars-empire-at-war-foc.py](games/game_starwars-empire-at-war-foc.py)</li></ul> | |
| Subnautica — [STEAM](https://store.steampowered.com/app/264710/) / [Epic](https://store.epicgames.com/p/subnautica) | [dekart811](https://github.com/dekart811), [Zash](https://github.com/ZashIn) | [game_subnautica.py](games/game_subnautica.py) | <ul><li>mod data checker</li><li>save game preview</li></ul> |
| Subnautica: Below Zero — [STEAM](https://store.steampowered.com/app/848450/) | [dekart811](https://github.com/dekart811), [Zash](https://github.com/ZashIn) | [game_subnautica-below-zero.py](games/game_subnautica-below-zero.py) | <ul><li>mod data checker</li><li>save game preview</li></ul> |
| Train Simulator Classic — [STEAM](https://store.steampowered.com/app/24010/) | [Ryan Young](https://github.com/YoRyan) | [game_trainsimulator.py](games/game_trainsimulator.py) | |
| Valheim — [STEAM](https://store.steampowered.com/app/892970/Valheim/) | [Zash](https://github.com/ZashIn) | [game_valheim.py](games/game_valheim.py) | <ul><li>mod data checker</li><li>overwrite config sync</li><li>save game support (no preview)</li></ul> |
| Test Drive Unlimited | [uwx](https://github.com/uwx) | [game_tdu.py](games/game_tdu.py) | |
| Test Drive Unlimited 2 — [STEAM](https://steamcommunity.com/app/9930/) | [uwx](https://github.com/uwx) | [game_tdu2.py](games/game_tdu2.py) | |
| The Witcher: Enhanced Edition - [GOG](https://www.gog.com/game/the_witcher) / [STEAM](https://store.steampowered.com/app/20900/The_Witcher_Enhanced_Edition_Directors_Cut/) | [erri120](https://github.com/erri120) | [game_witcher1.py](games/game_witcher1.py) | <ul><li>save game parsing (no preview)</li></ul> |
| The Witcher 3: Wild Hunt — [GOG](https://www.gog.com/game/the_witcher_3_wild_hunt) / [STEAM](https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/) | [Holt59](https://github.com/holt59/) | [game_witcher3.py](games/game_witcher3.py) | <ul><li>save game preview</li></ul> |
| Tony Hawk's Pro Skater 3 | [uwx](https://github.com/uwx) | [game_thps3.py](games/game_thps3.py) | |
| Tony Hawk's Pro Skater 4 | [uwx](https://github.com/uwx) | [game_thps4.py](games/game_thps4.py) | |
| Tony Hawk's Underground | [uwx](https://github.com/uwx) | [game_thug.py](games/game_thug.py) | |
| Tony Hawk's Underground 2 | [uwx](https://github.com/uwx) | [game_thug2.py](games/game_thug2.py) | |
| Trackmania United Forever — [STEAM](https://store.steampowered.com/app/7200/Trackmania_United_Forever/) | [uwx](https://github.com/uwx) | [game_tmuf.py](games/game_tmuf.py) | |
| Yu-Gi-Oh! Master Duel — [STEAM](https://store.steampowered.com/app/1449850/) | [The Conceptionist](https://github.com/the-conceptionist) & [uwx](https://github.com/uwx) | [game_masterduel.py](games/game_masterduel.py) | |
| Zeus and Poseidon — [GOG](https://www.gog.com/game/zeus_poseidon) / [STEAM](https://store.steampowered.com/app/566050/Zeus__Poseidon/) | [Holt59](https://github.com/holt59/) | [game_zeusandpoiseidon.py](games/game_zeusandpoiseidon.py) | <ul><li>mod data checker</li></ul> |

<!-- END: GAMES -->

## How to add a new game?

See [CONTRIBUTING](./CONTRIBUTING.md).
